from django.shortcuts import render
from shops.models import Shop
from dal import autocomplete
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from products.models import Product
# Create your views here.
class ShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['sp',])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs

class SearchProduct(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        product_id = int(self.request.GET.get('product_id'))
        product_sku = '-'
        product_obj = Product.objects.filter(id=product_id)
        if product_obj.exists():
            product_sku = product_obj.last().product_sku
        return Response({
            "product_sku": product_sku,
            "success": True})