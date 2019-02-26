from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import F, Sum, Count
from django.views.generic import View, ListView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q
from django.shortcuts import get_object_or_404, get_list_or_404

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from wkhtmltopdf.views import PDFTemplateResponse
from dal import autocomplete

from products.models import Product
from gram_to_brand.models import (
    Order, CartProductMapping, Cart,
    GRNOrder, GRNOrderProductMapping
)
from addresses.models import Address, State
from brand.models import Brand
from .serializers import CartProductMappingSerializer
from gram_to_brand.models import Order, CartProductMapping
from brand.models import Vendor
from products.models import ProductVendorMapping


class SupplierAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Vendor.objects.all()
        state = self.forwarded.get('supplier_state', None)
        brand = self.forwarded.get('brand', None)
        if state and brand:
            vendos_id = ProductVendorMapping.objects.filter(
                product__product_brand__id=brand).values('vendor')
            qs = qs.filter(state__id=state,id__in=[vendos_id])

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)
        return qs


class ShippingAddressAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Address.objects.filter(
            Q(shop_name__shop_owner=self.request.user) |
            Q(shop_name__related_users=self.request.user),
            shop_name__shop_type__shop_type='gf',
            address_type='shipping',
            status=True
            )
        return qs


class BillingAddressAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Address.objects.filter(
            Q(shop_name__shop_owner=self.request.user) |
            Q(shop_name__related_users=self.request.user),
            shop_name__shop_type__shop_type='gf',
            address_type='billing',
            status=True
        )
        return qs


class BrandAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Brand.objects.all()
        if self.q:
            qs = qs.filter(brand_name__icontains=self.q)
        return qs


class StateAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = State.objects.all()
        if self.q:
            qs = qs.filter(state_name__icontains=self.q)
        return qs


class OrderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Order.objects.all()
        qs = qs.filter(
            Q(ordered_cart__gf_shipping_address__shop_name__shop_owner=
              self.request.user) |
            Q(ordered_cart__gf_shipping_address__shop_name__related_users=
              self.request.user),
            ordered_cart__po_status=Cart.FINANCE_APPROVED
        )
        if self.q:
            qs = qs.filter(order_no__icontains=self.q)
        return qs


class ProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Product.objects.all()
        order_id = self.forwarded.get('order', None)
        if order_id:
            order = Order.objects.get(id=order_id)
            cp_products = CartProductMapping.objects.filter(
                cart=order.ordered_cart).values('cart_product')
            qs = qs.filter(id__in=[cp_products]).order_by('product_name')

        if self.q:
            qs = qs.filter(product_name__istartswith=self.q)
        return qs


class DownloadPurchaseOrder(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'purchase_order.pdf'
    template_name = 'admin/purchase_order/purchase_order.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(Cart, pk=self.kwargs.get('pk'))
        pk = self.kwargs.get('pk')
        a = Cart.objects.get(pk=pk)
        shop = a
        products = a.cart_list.all()
        order = shop.order_cart_mapping
        order_id = order.order_no
        gram_factory_billing_gstin = shop.gf_billing_address.shop_name.\
            shop_name_documents.filter(shop_document_type='gstin').last()
        gram_factory_shipping_gstin= shop.gf_shipping_address.shop_name.\
            shop_name_documents.filter(shop_document_type='gstin').last()

        tax_inline, sum_amount, sum_qty = 0, 0, 0
        taxes_list = []
        gst_tax_list = []
        cess_tax_list = []
        surcharge_tax_list = []
        for m in products:
            sum_qty = sum_qty + m.qty
            sum_amount = sum_amount + (m.qty * m.price)
            inline_sum_amount = (m.qty * m.price)
            for n in m.cart_product.product_pro_tax.all():
                divisor = (1+(n.tax.tax_percentage/100))
                original_amount = (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type == 'gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type == 'cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type == 'surcharge':
                    surcharge_tax_list.append(tax_amount)
                taxes_list.append(tax_amount)
                igst = sum(gst_tax_list)
                cgst = (sum(gst_tax_list))/2
                sgst = (sum(gst_tax_list))/2
                cess = sum(cess_tax_list)
                surcharge = sum(surcharge_tax_list)
        total_amount = sum_amount
        data = {
            "object": order_obj,
            "products": products,
            "shop": shop,
            "sum_qty": sum_qty,
            "sum_amount": sum_amount,
            "url": request.get_host(),
            "scheme": request.is_secure() and "https" or "http",
            "igst": igst,
            "cgst": cgst,
            "sgst": sgst,
            "cess": cess,
            "surcharge": surcharge,
            "total_amount": total_amount,
            "order_id": order_id,
            "gram_factory_billing_gstin": gram_factory_billing_gstin,
            "gram_factory_shipping_gstin": gram_factory_shipping_gstin}
        cmd_option = {
            'encoding': 'utf8',
            'margin-top': 3
        }
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )
        return response


class DownloadDebitNote(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'debit_note.pdf'
    template_name = 'admin/debit_note/debit_note.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(GRNOrder, pk=self.kwargs.get('pk'))
        pk = self.kwargs.get('pk')
        a = GRNOrder.objects.get(pk=pk)
        shop = a
        debit_note_id = a.grn_order_brand_note.all()
        products = a.grn_order_grn_order_product.all()
        order = shop.order
        order_id = order.order_no
        gram_factory_billing_gstin = shop.order.ordered_cart.\
            gf_billing_address.shop_name.shop_name_documents\
            .filter(shop_document_type='gstin').last()
        gram_factory_shipping_gstin = shop.order.ordered_cart.\
            gf_shipping_address.shop_name.shop_name_documents\
            .filter(shop_document_type='gstin').last()
        sum_qty = 0
        sum_amount = 0
        tax_inline = 0
        taxes_list = []
        gst_tax_list = []
        cess_tax_list = []
        surcharge_tax_list = []
        for m in products:
            sum_qty = sum_qty + m.returned_qty
            sum_amount = sum_amount + (m.returned_qty * m.po_product_price)
            inline_sum_amount = (m.returned_qty * m.po_product_price)
            for n in m.product.product_pro_tax.all():
                divisor = (1+(n.tax.tax_percentage/100))
                original_amount = (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type == 'gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type == 'cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type == 'surcharge':
                    surcharge_tax_list.append(tax_amount)
                taxes_list.append(tax_amount)
                igst = sum(gst_tax_list)
                cgst = (sum(gst_tax_list))/2
                sgst = (sum(gst_tax_list))/2
                cess = sum(cess_tax_list)
                surcharge = sum(surcharge_tax_list)
        total_amount = sum_amount
        total_amount_int = int(total_amount)
        data = {
            "object": order_obj, "products": products, "shop": shop,
            "sum_qty": sum_qty, "sum_amount": sum_amount,
            "url": request.get_host(),
            "scheme": request.is_secure() and "https" or "http",
            "igst": igst, "cgst": cgst, "sgst": sgst,"cess": cess,
            "surcharge": surcharge, "total_amount": total_amount,
            "order_id": order_id, "total_amount_int": total_amount_int,
            "debit_note_id": debit_note_id,
            "gram_factory_billing_gstin": gram_factory_billing_gstin,
            "gram_factory_shipping_gstin": gram_factory_shipping_gstin
        }
        cmd_option = {'encoding': 'utf8', 'margin-top': 3}
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )
        return response


class VendorProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = None
        supplier_id = self.forwarded.get('supplier_name', None)
        if supplier_id:
            qs = Product.objects.all()
            product_id = ProductVendorMapping.objects\
                .filter(vendor__id=supplier_id).values('product')
            qs = qs.filter(id__in=[product_id])
            if self.q:
                qs = qs.filter(product_name__icontains=self.q)
        return qs


class VendorProductPrice(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        supplier_id = self.request.GET.get('supplier_id')
        product_id = self.request.GET.get('product_id')
        vendor_product_price,product_case_size,product_inner_case_size = 0,0,0
        vendor_mapping = ProductVendorMapping.objects.filter(vendor__id=supplier_id, product__id=product_id)
        if vendor_mapping.exists():
            product = vendor_mapping.last().product
            vendor_product_price = vendor_mapping.last().product_price
            product_case_size = vendor_mapping.last().product.product_case_size
            product_inner_case_size = vendor_mapping.last().product.product_inner_case_size
            taxes = ([field.tax.tax_percentage for field in vendor_mapping.last().product.product_pro_tax.all()])
            taxes = str(sum(taxes))
            tax_percentage = taxes+'%'
        return Response({
            "price": vendor_product_price,
            "case_size": product_case_size,
            "inner_case_size": product_inner_case_size,
            "tax_percentage": tax_percentage,
            "success": True})


class GRNProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        order_id = self.forwarded.get('order_no', None)
        if order_id:
            qs = Product.objects.all()
            product_ids = CartProductMapping.objects.filter(
                cart__id=order_id).values('cart_product')
            qs = qs.filter(id__in=[product_ids])
        return qs


class GRNProductPriceMappingData(APIView):
    permission_classes =( AllowAny, )

    def get(self, *args, **kwargs):
        order_id = self.request.GET.get('order_id')
        cart_product_id = self.request.GET.get('cart_product_id')
        order = Order.objects.get(id=order_id)
        po_product_price = CartProductMapping.objects.get(
            cart__id=order.ordered_cart.id, cart_product__id=cart_product_id)
        return Response({
            "message": [""], "response_data": po_product_price.price,
            "success": True
        })


class GRNProductMappingData(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        order_id = self.request.GET.get('order_id')
        cart_product_id = self.request.GET.get('cart_product_id')
        order = Order.objects.get(id=order_id)
        po_product_quantity = CartProductMapping.objects.get(
            cart__id=order.ordered_cart.id, cart_product__id=cart_product_id)
        return Response({
            "message": [""], "response_data": po_product_quantity.qty,
            "success": True
        })


class GRNOrderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        order_id = self.forwarded.get('order_no', None)
        if order_id:
            qs = CartProductMapping.objects.filter(cart__id=order_id)
        return qs


class GRNProduct1MappingData(APIView):
    permission_classes = (AllowAny, )

    def get(self, *args, **kwargs):
        order_id = self.request.GET.get('order_id')
        data = CartProductMapping.objects.filter(cart__id=order_id)
        products = Product.objects.filter(
            id__in=CartProductMapping.objects.filter(
                cart__id=order_id).values_list('cart_product')
        )
        product_qty = data.values_list('qty')
        product_price = data.values_list('price')
        return Response({
            "products": products,
            "product_qty": product_qty,
            "product_price": product_price,
            "success": True
        })


class GRNedProductData(APIView):
    permission_classes =(AllowAny, )

    def get(self, *args, **kwargs):
        order_id = self.request.GET.get('order_id')
        product_id = self.request.GET.get('product_id')
        delivered_qty = []
        grn_by_order_id = GRNOrder.objects.filter(order_id=order_id)
        products_grn_by_order = GRNOrderProductMapping.objects.filter(
            grn_order__in=grn_by_order_id)
        for product in products_grn_by_order:
            if product.product_id == int(product_id):
                delivered_qty.append(product.delivered_qty)
        delivered_qty_sum = sum(delivered_qty)
        return Response({
            "message": [""],
            "response_data": delivered_qty_sum,
            "success": True
        })


class ApproveView(UpdateView):
    permission_classes = (IsAuthenticated,)
    template_name = 'admin/gram_to_brand/cart/change_form.html'
    model = Cart
    fields = ('is_approve',)
    success_message = "Approve Successfully"

    def get_object(self):
        cart_obj = get_object_or_404(Cart, pk=self.kwargs.get('pk'))
        return cart_obj

    def form_valid(self, form):
        cart_obj = get_object_or_404(Cart, pk=self.kwargs.get('pk'))
        cart_obj.is_approve = True
        cart_obj.save()
        return super(ApproveView, self).form_valid(form)

    def get_success_url(self, **kwargs):
        return reverse_lazy('approve-account', args=(self.kwargs.get('pk'),))


class DisapproveView(UpdateView):
    permission_classes = (IsAuthenticated,)
    template_name = 'admin/gram_to_brand/cart/change_form.html'
    model = Cart
    fields = ('is_approve',)
    success_message = "Dis-approve Successfully"

    def get_object(self):
        cart_obj = get_object_or_404(Cart, pk=self.kwargs.get('pk'))
        return cart_obj

    def form_valid(self, form):
        cart_obj = get_object_or_404(Cart, pk=self.kwargs.get('pk'))
        cart_obj.is_approve = False
        cart_obj.save()
        return super(DisapproveView, self).form_valid(form)

    def get_success_url(self, **kwargs):
        return reverse_lazy(
            'dis-approve-account', args=(self.kwargs.get('pk'),)
        )
