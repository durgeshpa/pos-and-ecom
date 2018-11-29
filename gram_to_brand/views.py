from django.shortcuts import render
from products.models import Product
from django.http import HttpResponse
from dal import autocomplete
#from shops.models import Shop
from addresses.models import Address,State
from brand.models import Brand

from gram_to_brand.models import Order,CartProductMapping, OrderItem, Cart
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, get_list_or_404
from wkhtmltopdf.views import PDFTemplateResponse


from gram_to_brand.models import Order,CartProductMapping
from brand.models import Vendor
from products.models import ProductVendorMapping

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
        print(a)

        products = a.cart_list.all()
        data = {"object": order_obj,"products":products, "shop":shop }
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
