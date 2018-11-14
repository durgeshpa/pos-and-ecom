from django.shortcuts import render
from products.models import Product
from django.http import HttpResponse
from dal import autocomplete
from shops.models import Shop
from addresses.models import Address,State
from brand.models import Brand
# Create your views here.

class SupplierAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        # if not self.request.is_authenticated():
        #     return City.objects.none()

        qs = Shop.objects.all()

        state = self.forwarded.get('state', None)
        brand = self.forwarded.get('brand', None)

        if state and brand:
            qs = qs.filter(shop_type__shop_type='b')

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