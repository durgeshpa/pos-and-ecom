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
