from django.shortcuts import render
from dal import autocomplete
from django.db.models import Q

from shops.models import Shop
from pos.models import RetailerProduct

# Create your views here.
class EcomShopAutoCompleteView(autocomplete.Select2QuerySetView):
    """
    shop filter for ecom tagged product
    """

    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['f'], status=True, approval_status=2, 
                                pos_enabled=True)
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs

class EcomProductAutoCompleteView(autocomplete.Select2QuerySetView):
    """
    product filter for ecom tagged product on basis of shop
    """
    
    def get_queryset(self, *args, **kwargs):
        qs = RetailerProduct.objects.none()
        shop = self.forwarded.get('shop', None)
        if shop:
            qs = RetailerProduct.objects.filter(~Q(sku_type=4), shop=shop, online_enabled = True).order_by('-created_at')
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs