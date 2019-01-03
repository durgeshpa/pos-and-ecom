from django.shortcuts import render
from products.models import Product, ProductPrice
from categories.models import Category
from django.shortcuts import render, get_object_or_404
from gram_to_brand.models import GRNOrderProductMapping
from dal import autocomplete
from shops.models import Shop,ParentRetailerMapping
from addresses.models import Address
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response


# Create your views here.
def abc():
    pass

class GfShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        # if not self.request.is_authenticated():

        qs = Shop.objects.all()

        state = self.forwarded.get('state', None)
        if state:
            shop_id = Address.objects.filter(state__id=state).values('shop_name')
            qs = qs.filter(id__in=[shop_id])

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)

        return qs

class GfProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = None
        my_shop = self.forwarded.get('shop', None)

        if my_shop:
            parent_mapping = ParentRetailerMapping.objects.get(retailer__id=my_shop)
            grn_pro = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_shipping_address__shop_name=parent_mapping.parent).annotate(Sum('available_qty'))
            product = grn_pro.values('product')
            qs = Product.objects.filter(id__in=[product])

        if self.q:
            qs = Product.objects.filter(shop_name__startswith=self.q)

        return qs


class MyShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type='sp',shop_owner=self.request.user)

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)
            print(qs)
        return qs


class SpProductPrice(APIView):
    permission_classes = (AllowAny,)
    def get(self,*args,**kwargs):
        gf_id =self.request.GET.get('gf_id')
        product_id =self.request.GET.get('product_id')
        pro_price = ProductPrice.objects.get(product=product_id,shop=gf_id)
        service_partner_price = pro_price.price_to_service_partner
        product_case_size = pro_price.product.product_case_size
        return Response({"service_partner_price": service_partner_price, "product_case_size": product_case_size,"success": True})