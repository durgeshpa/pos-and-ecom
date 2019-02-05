from django.shortcuts import render
from products.models import Product
from django.http import HttpResponse
from dal import autocomplete
#from shops.models import Shop
from addresses.models import Address,State
from brand.models import Brand

from gram_to_brand.models import Order,CartProductMapping, Cart, GRNOrder, GRNOrderProductMapping
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, get_list_or_404
from wkhtmltopdf.views import PDFTemplateResponse

from .serializers import CartProductMappingSerializer
from gram_to_brand.models import Order,CartProductMapping
from brand.models import Vendor
from products.models import ProductVendorMapping
from django.db.models import F,Sum,Count
from django.views.generic import View,ListView,UpdateView
from django.urls import reverse_lazy
from django.db.models import Q

# Create your views here.

class SupplierAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        # if not self.request.is_authenticated():
        #     return City.objects.none()

        qs = Vendor.objects.all()

        state = self.forwarded.get('supplier_state', None)
        brand = self.forwarded.get('brand', None)

        # if state:
        #     state_shops = Address.objects.filter(state__id=state).values('shop_name')
        #     qs = qs.filter(id__in=[state_shops])

        if state and brand:
            vendos_id = ProductVendorMapping.objects.filter(product__product_brand__id=brand).values('vendor')
            print(vendos_id)
            qs = qs.filter(state__id=state,id__in=[vendos_id])

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)
            print(qs)
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
    def get_queryset(self,*args,**kwargs):
        qs = Brand.objects.all()
        if self.q:
            qs = qs.filter(brand_name__icontains=self.q)
        return qs

class StateAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = State.objects.all()
        if self.q:
            qs = qs.filter(state_name__icontains=self.q)
        return qs

class OrderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = Order.objects.all()
        # if self.request.user.is_superuser:
        #     return qs
        qs = qs.filter(
            Q(ordered_cart__gf_shipping_address__shop_name__shop_owner=self.request.user) |
            Q(ordered_cart__gf_shipping_address__shop_name__related_users=self.request.user),
            ordered_cart__po_status='finance_approved'
        )
        if self.q:
            qs = qs.filter(order_no__icontains=self.q)
        return qs

class ProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = Product.objects.all()
        order_id = self.forwarded.get('order', None)
        #print(order_id)

        if order_id:
            order = Order.objects.get(id=order_id)
            cp_products = CartProductMapping.objects.filter(cart=order.ordered_cart).values('cart_product')
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

        #order_obj1= get_object_or_404(OrderedProductMapping)
        pk=self.kwargs.get('pk')
        a = Cart.objects.get(pk=pk)
        shop =a
        products = a.cart_list.all()
        order= shop.order_cart_mapping
        order_id= order.order_no
        gram_factory_billing_gstin= shop.gf_billing_address.shop_name.shop_name_documents.filter(shop_document_type='gstin').last()
        gram_factory_shipping_gstin= shop.gf_shipping_address.shop_name.shop_name_documents.filter(shop_document_type='gstin').last()
        sum_qty = 0
        sum_amount=0
        tax_inline=0
        taxes_list = []
        gst_tax_list= []
        cess_tax_list= []
        surcharge_tax_list=[]
        for m in products:

            sum_qty = sum_qty + m.qty
            sum_amount = sum_amount + (m.qty * m.price)
            inline_sum_amount = (m.qty * m.price)

            for n in m.cart_product.product_pro_tax.all():

                divisor= (1+(n.tax.tax_percentage/100))
                original_amount= (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type=='gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type=='cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type=='surcharge':
                    surcharge_tax_list.append(tax_amount)

                taxes_list.append(tax_amount)
                igst= sum(gst_tax_list)
                cgst= (sum(gst_tax_list))/2
                sgst= (sum(gst_tax_list))/2
                cess= sum(cess_tax_list)
                surcharge= sum(surcharge_tax_list)
                #tax_inline = tax_inline + (inline_sum_amount - original_amount)
                #tax_inline1 =(tax_inline / 2)
            print(surcharge_tax_list)
            print(gst_tax_list)
            print(cess_tax_list)
            print(taxes_list)

        total_amount = sum_amount
        print(sum_amount)
        # print (tax_inline)
        # print (tax_inline1)
        data = {"object": order_obj,"products":products, "shop":shop, "sum_qty": sum_qty, "sum_amount":sum_amount,"url":request.get_host(), "scheme": request.is_secure() and "https" or "http" , "igst":igst, "cgst":cgst,"sgst":sgst,"cess":cess,"surcharge":surcharge, "total_amount":total_amount,"order_id":order_id,"gram_factory_billing_gstin":gram_factory_billing_gstin, "gram_factory_shipping_gstin":gram_factory_shipping_gstin}
        # for m in products:
        #     data = {"object": order_obj,"products":products,"amount_inline": m.qty * m.price }
        #     print (data)

        #cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      #"no-stop-slow-scripts": True, "quiet": True}


        cmd_option = {"encoding":"utf8","margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        cmd_option = {'encoding':'utf8','margin-top': 3}

        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
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

        #order_obj1= get_object_or_404(OrderedProductMapping)
        pk=self.kwargs.get('pk')
        a = GRNOrder.objects.get(pk=pk)
        shop =a
        debit_note_id = a.grn_order_brand_note.all()
        products = a.grn_order_grn_order_product.all()
        order= shop.order
        order_id= order.order_no
        gram_factory_billing_gstin= shop.order.billing_address.shop_name.shop_name_documents.filter(shop_document_type='gstin').last()
        gram_factory_shipping_gstin= shop.order.shipping_address.shop_name.shop_name_documents.filter(shop_document_type='gstin').last()
        sum_qty = 0
        sum_amount=0
        tax_inline=0
        taxes_list = []
        gst_tax_list= []
        cess_tax_list= []
        surcharge_tax_list=[]
        for m in products:

            sum_qty = sum_qty + m.returned_qty
            sum_amount = sum_amount + (m.returned_qty * m.po_product_price)
            inline_sum_amount = (m.returned_qty * m.po_product_price)

            for n in m.product.product_pro_tax.all():

                divisor= (1+(n.tax.tax_percentage/100))
                original_amount= (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type=='gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type=='cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type=='surcharge':
                    surcharge_tax_list.append(tax_amount)

                taxes_list.append(tax_amount)
                igst= sum(gst_tax_list)
                cgst= (sum(gst_tax_list))/2
                sgst= (sum(gst_tax_list))/2
                cess= sum(cess_tax_list)
                surcharge= sum(surcharge_tax_list)
                #tax_inline = tax_inline + (inline_sum_amount - original_amount)
                #tax_inline1 =(tax_inline / 2)
            print(surcharge_tax_list)
            print(gst_tax_list)
            print(cess_tax_list)
            print(taxes_list)

        total_amount = sum_amount
        total_amount_int = int(total_amount)
        print(sum_amount)
        # print (tax_inline)
        # print (tax_inline1)
        data = {"object": order_obj,"products":products, "shop":shop, "sum_qty": sum_qty, "sum_amount":sum_amount,"url":request.get_host(), "scheme": request.is_secure() and "https" or "http" , "igst":igst, "cgst":cgst,"sgst":sgst,"cess":cess,"surcharge":surcharge, "total_amount":total_amount,"order_id":order_id, "total_amount_int":total_amount_int,"debit_note_id":debit_note_id, "gram_factory_billing_gstin":gram_factory_billing_gstin, "gram_factory_shipping_gstin":gram_factory_shipping_gstin}
        # for m in products:
        #     data = {"object": order_obj,"products":products,"amount_inline": m.qty * m.price }
        #     print (data)

        #cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      #"no-stop-slow-scripts": True, "quiet": True}


        cmd_option = {"encoding":"utf8","margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        cmd_option = {'encoding':'utf8','margin-top': 3}

        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response

class VendorProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = None
        supplier_id = self.forwarded.get('supplier_name', None)
        if supplier_id:
            qs = Product.objects.all()
            product_id = ProductVendorMapping.objects.filter(vendor__id=supplier_id).values('product')
            qs = qs.filter(id__in=[product_id])

        return qs

class VendorProductPrice(APIView):
   permission_classes = (AllowAny,)

   def get(self,*args,**kwargs):
       supplier_id = self.request.GET.get('supplier_id')
       product_id = self.request.GET.get('product_id')
       price = ProductVendorMapping.objects.get(vendor__id=supplier_id,product__id=product_id)
       case_size = ProductVendorMapping.objects.get(vendor__id=supplier_id,product__id=product_id).product.product_case_size
       inner_case_size = ProductVendorMapping.objects.get(vendor__id=supplier_id,product__id=product_id).product.product_inner_case_size
       return Response({ "price": price.product_price,"case_size":case_size,"inner_case_size":inner_case_size, "success": True})

class GRNProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        #qs = Product.objects.all()
        order_id = self.forwarded.get('order_no', None)
        if order_id:
            qs = Product.objects.all()
            product_ids = CartProductMapping.objects.filter(cart__id=order_id).values('cart_product')
            qs = qs.filter(id__in=[product_ids])

        return qs



class GRNProductPriceMappingData(APIView):
    permission_classes =(AllowAny, )
    def get(self,*args,**kwargs):
        order_id =self.request.GET.get('order_id')
        cart_product_id= self.request.GET.get('cart_product_id')
        order = Order.objects.get(id=order_id)
        po_product_price = CartProductMapping.objects.get( cart__id=order.ordered_cart.id,cart_product__id=cart_product_id)
        return Response({"message": [""], "response_data": po_product_price.price, "success": True})

class GRNProductMappingData(APIView):
    permission_classes =(AllowAny, )
    def get(self,*args,**kwargs):
        order_id =self.request.GET.get('order_id')
        cart_product_id= self.request.GET.get('cart_product_id')
        order = Order.objects.get(id=order_id)
        po_product_quantity = CartProductMapping.objects.get( cart__id=order.ordered_cart.id,cart_product__id=cart_product_id)
        return Response({"message": [""], "response_data": po_product_quantity.qty, "success": True})

class GRNOrderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        #qs = Product.objects.all()
        order_id = self.forwarded.get('order_no', None)
        if order_id:
            #qs = Product.objects.all()
            qs = CartProductMapping.objects.filter(cart__id=order_id)
            #qs = qs.filter(id__in=[product_ids])

        return qs

class GRNProduct1MappingData(APIView):
    permission_classes =(AllowAny, )
    def get(self,*args,**kwargs):
        order_id =self.request.GET.get('order_id')
        #cart_product_id= self.request.GET.get('cart_product_id')
        data = CartProductMapping.objects.filter(cart__id=order_id)
        products = Product.objects.filter(id__in=CartProductMapping.objects.filter( cart__id=order_id).values_list('cart_product'))
        product_qty= data.values_list('qty')
        product_price =data.values_list('price')
        #product_count_val = Product.objects.annotate(product_count=Count('product_grn_order_product')).filter('product_grn_order_product').values('product_name','product_count')
        #print(product_count_val)
        return Response({"products": products, "product_qty":product_qty ,"product_price": product_price,"success": True})

class GRNedProductData(APIView):
    permission_classes =(AllowAny, )
    def get(self,*args,**kwargs):
        order_id =self.request.GET.get('order_id')
        product_id= self.request.GET.get('product_id')
        delivered_qty = []
        grn_by_order_id = GRNOrder.objects.filter(order_id=order_id)
        products_grn_by_order = GRNOrderProductMapping.objects.filter(grn_order__in=grn_by_order_id)
        for product in products_grn_by_order:
            if product.product_id == int(product_id):
                delivered_qty.append(product.delivered_qty)
        delivered_qty_sum = sum(delivered_qty)
        #already_grned_product = CartProductMapping.objects.get( cart__id=order_id,cart_product__id=cart_product_id)

        #a= GRNOrder.objects.get(order__id=order_id)
        #b= a.grn_order_grn_order_product.get(product__id=product_id)
        #already_grned_product = b.already_grned_product + int(b.delivered_qty)
        return Response({"message": [""], "response_data": delivered_qty_sum, "success": True})

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
        return reverse_lazy('dis-approve-account', args=(self.kwargs.get('pk'),))
