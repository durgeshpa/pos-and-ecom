from django.shortcuts import render
from products.models import Product
from django.http import HttpResponse
from dal import autocomplete
from shops.models import Shop
from addresses.models import Address,State
from brand.models import Brand
from gram_to_brand.models import Order,CartProductMapping
# Create your views here.

class SupplierAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        # if not self.request.is_authenticated():
        #     return City.objects.none()

        qs = Shop.objects.all()

        state = self.forwarded.get('supplier_state', None)
        brand = self.forwarded.get('brand', None)

        print(state)
        print(brand)
        # if state:
        #     state_shops = Address.objects.filter(state__id=state).values('shop_name')
        #     qs = qs.filter(id__in=[state_shops])

        if state and brand:
            state_shops = Address.objects.filter(state__id=state).values('shop_name')
            qs = qs.filter(id__in=[state_shops],shop_type__shop_type='b',brand__id=brand)

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)

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