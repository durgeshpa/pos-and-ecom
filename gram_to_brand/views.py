from django.shortcuts import render
from products.models import Product
from django.http import HttpResponse
from dal import autocomplete
#from shops.models import Shop
from addresses.models import Address,State
from brand.models import Brand

from gram_to_brand.models import Order,CartProductMapping, OrderItem, Cart, GRNOrder, GRNOrderProductMapping
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
    def get_queryset(self,*args,**kwargs):

        qs = Address.objects.filter(shop_name__shop_type__shop_type='gf',address_type='shipping')

        state_id = self.forwarded.get('state', None)
        if state_id:
            qs = qs.filter(state__id=state_id)

        return qs


class BillingAddressAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = Address.objects.filter(shop_name__shop_type__shop_type='gf',address_type='billing')
        state_id = self.forwarded.get('state', None)

        if state_id:
            qs = qs.filter(state__id=state_id)

        return qs

class BrandAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = Brand.objects.all()
        return qs

class StateAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = State.objects.all()
        return qs

class OrderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = Order.objects.all()
        return qs

class ProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        qs = Product.objects.all()
        order_id = self.forwarded.get('order', None)
        #print(order_id)

        if order_id:
            order = Order.objects.get(id=order_id)
            cp_products = CartProductMapping.objects.filter(cart=order.ordered_cart).values('cart_product')
            qs = qs.filter(id__in=[cp_products])

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
        order= shop.order_cart_mapping.get(pk=pk)
        order_id= order.order_no
        sum_qty=0
        sum_amount=0
        tax_inline=0
        for m in products:
            sum_qty=sum_qty + m.qty
            sum_amount = sum_amount + (m.qty * m.price)
            for n in m.cart_product.product_pro_tax.all():
                tax_inline = tax_inline + ((n.tax.tax_percentage/100)* m.price)
        total_amount = sum_amount + tax_inline
        print(sum_amount)
        print (tax_inline)
        data = {"object": order_obj,"products":products, "shop":shop,"sum_qty":sum_qty, "sum_amount":sum_amount,"url":request.get_host(), "scheme": request.is_secure() and "https" or "http" , "tax_inline":tax_inline, "total_amount":total_amount,"order_id":order_id}
        # for m in products:
        #     data = {"object": order_obj,"products":products,"amount_inline": m.qty * m.price }
        #     print (data)
        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response

class VendorProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        #qs = Product.objects.all()
        supplier_id = self.forwarded.get('supplier_name', None)
        print(supplier_id)
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
       return Response({"message": [""], "response_data": price.product_price, "success": True})

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
        po_product_price = CartProductMapping.objects.get( cart__id=order_id,cart_product__id=cart_product_id)
        return Response({"message": [""], "response_data": po_product_price.price, "success": True})

class GRNProductMappingData(APIView):
    permission_classes =(AllowAny, )
    def get(self,*args,**kwargs):
        order_id =self.request.GET.get('order_id')
        cart_product_id= self.request.GET.get('cart_product_id')
        po_product_quantity = CartProductMapping.objects.get( cart__id=order_id,cart_product__id=cart_product_id)
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
        data = CartProductMapping.objects.filter( cart__id=order_id).values_list('cart_product')
        products = Product.objects.filter(id__in=CartProductMapping.objects.filter( cart__id=order_id).values_list('cart_product')).values('product_name')

        # delivered_qty = []
        # grn_by_order_id = GRNOrder.objects.filter(order_id=order_id)
        # products_grn_by_order = GRNOrderProductMapping.objects.filter(grn_order__in=grn_by_order_id)
        # for product in products_grn_by_order:
        #     if product.product_id == int(product_id):
        #         delivered_qty.append(product.delivered_qty)
        # delivered_qty_sum = sum(delivered_qty)
        product_count = Product.objects.annotate(product_no=Count('product_grn_order_product'))

        return Response({"products": products, "product_qty": data.values_list('qty'),"product_price": data.values_list('price'),"already_grned_pro":product_count, "success": True})
        #return Response(products)
        #data1= CartProductMapping.objects.filter( cart__id=order_id).values_list('qty')
        #print (serializer.data)

        #return Response({"message": [""], "response_data": serializer.data , "success": True})
class GRNProduct2MappingData(APIView):
    permission_classes =(AllowAny, )
    def get(self,*args,**kwargs):
        order_id =self.request.GET.get('order_id')
        #cart_product_id= self.request.GET.get('cart_product_id')
        data= CartProductMapping.objects.filter( cart__id=order_id).values_list('qty')
        #products = Product.objects.filter(id__in=CartProductMapping.objects.filter( cart__id=order_id).values_list('cart_product')).values('product_name')
        return Response(data)

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
