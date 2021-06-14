import csv
import math
import datetime
from io import StringIO

import django_filters
from decouple import config
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db.models import F, Sum, Count, Subquery
from django.views.generic import View, ListView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q
from django.shortcuts import get_object_or_404, get_list_or_404
from django_filters.views import FilterView
from django_tables2 import SingleTableView, tables
from django_tables2.export import ExportMixin
import django_tables2 as tables


from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from wkhtmltopdf.views import PDFTemplateResponse
from dal import autocomplete

from barCodeGenerator import merged_barcode_gen
from common import constants
from products.models import Product
from gram_to_brand.models import (
    Order, CartProductMapping, Cart,
    GRNOrder, GRNOrderProductMapping
)
from addresses.models import Address, State
from brand.models import Brand
from brand.models import Vendor
from products.models import ProductVendorMapping, ParentProduct

from global_config.views import get_config
from retailer_backend.common_function import send_mail
from retailer_backend.messages import SUCCESS_MESSAGES

import logging
logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


class VendorAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Vendor.objects.all()
        if self.q:
            qs = qs.filter(vendor_name__startswith=self.q)
        return qs

class SupplierAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = None
        state = self.forwarded.get('supplier_state', None)
        brand = self.forwarded.get('brand', None)
        if state and brand:
            qs = Vendor.objects.filter(state__id=state, vendor_products_brand__contains=[brand])
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
        qs = Brand.objects.filter(active_status='active')
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


class ParentProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = None
        supplier_id = self.forwarded.get('supplier_name', None)
        if supplier_id is None:
            return qs

        product_qs = Product.objects.exclude(repackaging_type='destination')
        product_qs = product_qs.exclude(status='deactivated')
        product_id = ProductVendorMapping.objects \
            .filter(vendor__id=supplier_id, case_size__gt=0, status=True).values('product')
        parent_product_ids = product_qs.filter(id__in=[product_id]).values('parent_product')
        qs = ParentProduct.objects.filter(id__in=[parent_product_ids])

        if self.q:
            qs = qs.filter(Q(name__icontains=self.q) | Q(parent_id__icontains=self.q))

        return qs


class ProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Product.objects.all()
        order_id = self.forwarded.get('order', None)
        if order_id:
            cp_products = Order.objects \
                .get(id=order_id).ordered_cart.cart_list \
                .values_list('cart_product', flat=True)
            qs = qs.filter(id__in=cp_products).order_by('product_name')

        if self.forwarded.get('price-slab', None):
            qs = qs.filter(repackaging_type__in=['none', 'source', 'destination'])

        if self.q:
            qs = qs.filter(Q(product_name__istartswith=self.q) | Q(product_sku__istartswith=self.q))
        return qs


class MergedBarcode(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        bin_id_list = {}
        pk = self.kwargs.get('pk')
        grn_product = GRNOrderProductMapping.objects.filter(pk=pk).last()
        grn_order = grn_product.grn_order
        product_mrp = grn_product.vendor_product
        barcode_id=grn_product.barcode_id
        if barcode_id is None:
            product_id = str(grn_product.product_id).zfill(5)
            expiry_date = datetime.datetime.strptime(str(grn_product.expiry_date), '%Y-%m-%d').strftime('%d%m%y')
            barcode_id = str("2" + product_id + str(expiry_date))
        temp_data = {"qty": math.ceil(grn_product.delivered_qty / int(grn_product.vendor_product.case_size)),
                     "data": {"SKU": grn_product.product.product_name,
                              "Batch":grn_product.batch_id,
                              "MRP": product_mrp.product_mrp if product_mrp.product_mrp else ''}}

        bin_id_list[barcode_id] = temp_data
        return merged_barcode_gen(bin_id_list)


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
        gram_factory_billing_gstin = shop.gf_billing_address.shop_name. \
            shop_name_documents.filter(shop_document_type='gstin').last()
        gram_factory_shipping_gstin = shop.gf_shipping_address.shop_name. \
            shop_name_documents.filter(shop_document_type='gstin').last()
        shop_id = order_obj.gf_billing_address.shop_name_id
        gf_shops = get_config('GF_SHOPS', constants.GF_SHOPS)
        is_gf_shop = False
        if shop_id in gf_shops:
            is_gf_shop = True
        tax_inline, sum_amount, sum_qty = 0, 0, 0
        gst_list = []
        cess_list = []
        surcharge_list = []
        for m in products:
            sum_qty = sum_qty + m.qty
            sum_amount = sum_amount + m.total_price
            inline_sum_amount = m.total_price
            tax_percentage = 0
            for n in m.cart_product.product_pro_tax.all():
                tax_percentage += n.tax.tax_percentage
            divisor = (1 + (tax_percentage / 100))
            original_amount = (inline_sum_amount / divisor)
            for n in m.cart_product.product_pro_tax.all():
                if n.tax.tax_type == 'gst':
                    gst_list.append((original_amount * (n.tax.tax_percentage / 100)))
                elif n.tax.tax_type == 'cess':
                    cess_list.append((original_amount * (n.tax.tax_percentage / 100)))
                elif n.tax.tax_type == 'surcharge':
                    surcharge_list.append((original_amount * (n.tax.tax_percentage / 100)))

        igst = sum(gst_list)
        cgst = igst / 2
        sgst = igst / 2
        cess = sum(cess_list)
        surcharge = sum(surcharge_list)
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
            "gram_factory_shipping_gstin": gram_factory_shipping_gstin,
            "is_gf_shop" : is_gf_shop
        }


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
        shop_id = order_obj.order.ordered_cart.gf_billing_address.shop_name_id
        gf_shops = get_config('GF_SHOPS', constants.GF_SHOPS)
        is_gf_shop = False
        if shop_id in gf_shops:
            is_gf_shop = True
        debit_note_id = a.grn_order_brand_note.all()
        products = a.grn_order_grn_order_product.all()
        product_list = {}
        for product in products:
            if product.product.product_sku in product_list.keys():
                temp_prod = product_list[product.product.product_sku]
                temp_prod.product_invoice_qty += product.product_invoice_qty
                temp_prod.delivered_qty += product.delivered_qty
                temp_prod.available_qty += product.available_qty
                temp_prod.returned_qty += product.returned_qty
                temp_prod.damaged_qty += product.damaged_qty
                product_list[product.product.product_sku] = temp_prod

            else:
                product_list[product.product.product_sku] = product

        order = shop.order
        order_id = order.order_no
        gram_factory_billing_gstin = shop.order.ordered_cart. \
            gf_billing_address.shop_name.shop_name_documents \
            .filter(shop_document_type='gstin').last()
        gram_factory_shipping_gstin = shop.order.ordered_cart. \
            gf_shipping_address.shop_name.shop_name_documents \
            .filter(shop_document_type='gstin').last()
        sum_qty = 0
        sum_amount = 0
        tax_inline = 0
        taxes_list = []
        gst_tax_list = []
        cess_tax_list = []
        surcharge_tax_list = []
        for key, value in product_list.items():
            sum_qty = sum_qty + value.returned_qty
            sum_amount = sum_amount + (value.returned_qty * value.po_product_price)
            inline_sum_amount = (value.returned_qty * value.po_product_price)
            for n in value.product.product_pro_tax.all():
                divisor = (1 + (n.tax.tax_percentage / 100))
                original_amount = (inline_sum_amount / divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type == 'gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type == 'cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type == 'surcharge':
                    surcharge_tax_list.append(tax_amount)
                taxes_list.append(tax_amount)
                igst = sum(gst_tax_list)
                cgst = (sum(gst_tax_list)) / 2
                sgst = (sum(gst_tax_list)) / 2
                cess = sum(cess_tax_list)
                surcharge = sum(surcharge_tax_list)
        total_amount = sum_amount
        total_amount_int = int(total_amount)
        data = {
            "object": order_obj, "products": product_list, "shop": shop,
            "sum_qty": sum_qty, "sum_amount": sum_amount,
            "url": request.get_host(),
            "scheme": request.is_secure() and "https" or "http",
            "igst": igst, "cgst": cgst, "sgst": sgst, "cess": cess,
            "surcharge": surcharge, "total_amount": total_amount,
            "order_id": order_id, "total_amount_int": total_amount_int,
            "debit_note_id": debit_note_id,
            "gram_factory_billing_gstin": gram_factory_billing_gstin,
            "gram_factory_shipping_gstin": gram_factory_shipping_gstin,
            "is_gf_shop": is_gf_shop
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
        parent_product_pk = self.forwarded.get('cart_parent_product', None)
        if supplier_id:
            qs = Product.objects.filter(parent_product__pk=parent_product_pk).exclude(repackaging_type='destination')
            product_id = ProductVendorMapping.objects \
                .filter(vendor__id=supplier_id, case_size__gt=0, status=True).values('product')
            qs = qs.filter(id__in=[product_id])
            if self.q:
                qs = qs.filter(
                    Q(product_name__icontains=self.q) |
                    Q(product_sku__iexact=self.q)
                )
        return qs


def FetchLastGRNProduct(request):
    data = {
        'found': False
    }
    parent_product_pk = request.GET.get('parent_product', None)
    if parent_product_pk:
        products = GRNOrderProductMapping.objects.filter(product__parent_product__pk=parent_product_pk).order_by('-created_at').values('created_at', 'product__id', 'product__product_name', 'product__product_sku')
        if products:
            product = products[0]
            if product:
                data = {
                    'found': True,
                    'product_id': product.get('product__id'),
                    'product_name': "{}-{}".format(product.get('product__product_name'), product.get('product__product_sku'))
                }

    return JsonResponse(data, safe=False)


class VendorProductPrice(APIView):
    permission_classes = (AllowAny,)
    

    def get(self, *args, **kwargs):
        supplier_id = self.request.GET.get('supplier_id')
        product_id = self.request.GET.get('product_id')
        vendor_product_price, vendor_product_mrp, product_case_size, product_inner_case_size = 0, 0, 0, 0
        vendor_mapping = ProductVendorMapping.objects.filter(vendor__id=supplier_id, product__id=product_id)

        if vendor_mapping.exists():
            product = vendor_mapping.last().product
            product_sku = vendor_mapping.last().product.product_sku
            
            if vendor_mapping.last().product_price:
                vendor_product_price = vendor_mapping.last().product_price
              
            elif vendor_mapping.last().product_price_pack:
                vendor_product_price = vendor_mapping.last().product_price_pack
          
            vendor_product_price_unit = vendor_mapping.last().brand_to_gram_price_unit

            vendor_product_mrp = vendor_mapping.last().product.product_mrp
            product_case_size = vendor_mapping.last().case_size if vendor_mapping.last().case_size else vendor_mapping.last().product.product_case_size
            product_inner_case_size = vendor_mapping.last().product.product_inner_case_size
            # if product.parent_product:
            #     taxes = product.parent_product.gst + product.parent_product.cess + product.parent_product.surcharge
            #     taxes = str(taxes)
            # else:
            #     taxes = ([field.tax.tax_percentage for field in vendor_mapping.last().product.product_pro_tax.all()])
            #     taxes = str(sum(taxes))
            taxes = ([field.tax.tax_percentage for field in vendor_mapping.last().product.product_pro_tax.all()])
            taxes = str(sum(taxes))
            tax_percentage = taxes + '%'
        
        return Response({
            "price": vendor_product_price,
            "brand_to_gram_price_unit" : vendor_product_price_unit,
            "mrp": vendor_product_mrp,
            "sku": product_sku,
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
    permission_classes = (AllowAny,)
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
    permission_classes = (AllowAny,)

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
    permission_classes = (AllowAny,)

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
        cart_obj.approved_by = self.request.user
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


class GetMessage(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        data, is_success, po_obj = [], False, ''
        if request.GET.get('po'):
            po_obj = Cart.objects.get(id=request.GET.get('po'))
            if request.GET.get('po') and po_obj.po_message is not None:
                is_success = True
                dt = {
                    'user': po_obj.po_message.created_by.phone_number,
                    'message': po_obj.po_message.message,
                    'created_at': po_obj.po_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
                data.append(dt)
        return Response({
            "message": [""],
            "response_data": data,
            "is_success": is_success,
            "po_status": po_obj.po_status if po_obj else ''
        })


def mail_warehouse_for_approved_po():

    try:
        info_logger.info("mail_warehouse_for_approved_po|STARTED")

        today = datetime.datetime.today().date()
        po_to_send_mail_for = Cart.objects.filter(po_status=Cart.OPEN, cart_type=Cart.CART_TYPE_CHOICE.AUTO,
                                                  approved_at__date=today)
        if po_to_send_mail_for.count() > 0:
            sender = get_config("ARS_MAIL_SENDER")

            recipient_list = get_config("MAIL_DEV")
            if config('OS_ENV') and config('OS_ENV') in ['Production']:
                recipient_list = get_config("ARS_MAIL_WAREHOUSE_RECIEVER")
            subject = SUCCESS_MESSAGES['ARS_MAIL_WAREHOUSE_SUBJECT'].format(today)
            body = SUCCESS_MESSAGES['ARS_MAIL_WAREHOUSE_BODY'].format(today)
            f = StringIO()
            writer = csv.writer(f)
            filename = 'PO_approved-{}.csv'.format(today)
            columns = ['PO Number', 'Brand', 'Supplier State', 'Supplier Name', 'PO Creation Date', 'PO Status',
                       'PO Delivery Date']
            writer.writerow(columns)
            for po in po_to_send_mail_for:
                writer.writerow([po.po_no, po.brand, po.supplier_state, po.supplier_name, po.created_at,
                                po.po_status, po.po_delivery_date])
            attachment = {'name' : filename, 'type' : 'text/csv', 'value' : f.getvalue()}
            send_mail(sender, recipient_list, subject, body, [attachment])
            po_to_send_mail_for.update(is_warehouse_notified=True)
        info_logger.info("mail_warehouse_for_approved_po|COMPLETED")
    except Exception as e:
        info_logger.error("Exception|mail_warehouse_for_approved_po|{}".format(e))


def mail_to_vendor_on_po_approval(po_instance):
    """
    Send mail to vendor once po is approved.
    """
    sender = get_config("ARS_MAIL_SENDER", "consultant1@gramfactory.com")
    recipient_list = get_config("MAIL_DEV")
    if config('OS_ENV') and config('OS_ENV') in ['Production']:
        recipient_list = [po_instance.email]
    vendor_name = po_instance.supplier_name.vendor_name
    po_no = po_instance.po_no
    subject = SUCCESS_MESSAGES['ARS_MAIL_VENDOR_SUBJECT'].format(po_no,
                                                                 vendor_name,
                                                                 po_instance.brand.brand_name)
    body = SUCCESS_MESSAGES['ARS_MAIL_VENDOR_BODY']

    filename = 'PO_PDF_{}_{}_{}.pdf'.format(po_no, datetime.datetime.today().date(), vendor_name)
    template_name = 'admin/purchase_order/purchase_order.html'

    cmd_option = {
        'encoding': 'utf8',
        'margin-top': 3
    }

    data = generate_pdf_data(po_instance)
    response = PDFTemplateResponse(
        request=None, template=template_name,
        filename=filename, context=data,
        show_content_in_browser=False, cmd_options=cmd_option
    )
    attachment = {'name': filename, 'type': 'application/pdf', 'value': response.rendered_content}
    send_mail(sender, recipient_list, subject, body, [attachment])


def generate_pdf_data(po_instance):
    """
    Takes PO(Cart) instance and generated the data required for PO PDF
    """
    products = po_instance.cart_list.all()
    order = po_instance.order_cart_mapping
    order_id = order.order_no
    gram_factory_billing_gstin = po_instance.gf_billing_address.shop_name. \
        shop_name_documents.filter(shop_document_type='gstin').last()
    gram_factory_shipping_gstin = po_instance.gf_shipping_address.shop_name. \
        shop_name_documents.filter(shop_document_type='gstin').last()
    tax_inline, sum_amount, sum_qty = 0, 0, 0
    gst_list = []
    cess_list = []
    surcharge_list = []
    for m in products:
        sum_qty = sum_qty + m.qty
        sum_amount = sum_amount + m.total_price
        inline_sum_amount = m.total_price
        tax_percentage = 0
        for n in m.cart_product.product_pro_tax.all():
            tax_percentage += n.tax.tax_percentage
        divisor = (1 + (tax_percentage / 100))
        original_amount = (inline_sum_amount / divisor)
        for n in m.cart_product.product_pro_tax.all():
            if n.tax.tax_type == 'gst':
                gst_list.append((original_amount * (n.tax.tax_percentage / 100)))
            elif n.tax.tax_type == 'cess':
                cess_list.append((original_amount * (n.tax.tax_percentage / 100)))
            elif n.tax.tax_type == 'surcharge':
                surcharge_list.append((original_amount * (n.tax.tax_percentage / 100)))
    igst = sum(gst_list)
    cgst = igst / 2
    sgst = igst / 2
    cess = sum(cess_list)
    surcharge = sum(surcharge_list)
    total_amount = sum_amount
    data = {
        "object": po_instance,
        "products": products,
        "shop": po_instance,
        "sum_qty": sum_qty,
        "sum_amount": sum_amount,
        "url": get_config('SITE_URL'),
        "scheme": get_config('CONNECTION'),
        "igst": igst,
        "cgst": cgst,
        "sgst": sgst,
        "cess": cess,
        "surcharge": surcharge,
        "total_amount": total_amount,
        "order_id": order_id,
        "gram_factory_billing_gstin": gram_factory_billing_gstin,
        "gram_factory_shipping_gstin": gram_factory_shipping_gstin}
    return data


class DownloadPOItems(APIView):

    permission_classes = (AllowAny,)
    filename = 'purchase_order.pdf'

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        cart = Cart.objects.filter(pk=int(pk)).last()
        filename ="po_item_list_" + cart.po_no + ".csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(['parent_id', 'parent_name', 'id', 'product_name', 'sku', 'case_size', 'number_of_cases', 'mrp',
                         'brand_to_gram_price_unit', 'brand_to_gram_price'])
        po_items = CartProductMapping.objects.filter(cart=cart)

        for p in po_items:
            writer.writerow([p.cart_parent_product.parent_id, p.cart_parent_product.name, p.cart_product_id, p.cart_product.product_name,
                             p.cart_product.product_sku, p.case_size, p.no_of_cases, p.cart_product.product_mrp,
                             p.vendor_product.brand_to_gram_price_unit, p.price])

        return response
