from django.shortcuts import render
from shops.models import Shop
from dal import autocomplete
from django.db.models import Q
# Create your views here.
class ShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['sp',])
        if self.q:
            qs = qs.filter(Q(shop_owner__phone_number__icontains=self.q) | Q(shop_name__icontains=self.q))
        return qs

def save_vendor(vendor):
    parent_brands=[]
    for brand_dt in vendor.vendor_brand_mapping.filter(status=True):
        parent_brands.append(vendor.get_parent_or_self(brand_dt))
    vendor.vendor_products_brand = list(set(parent_brands))
    vendor.save()