from dal import autocomplete
from django.shortcuts import render

# Create your views here.
from addresses.models import Route


class RouteAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        city = self.forwarded.get('city', None)
        shop = self.forwarded.get('shop', None)
        qs = Route.objects.all()
        if shop:
            qs = qs.filter(city__city_address__shop_name_id=shop,
                           city__city_address__address_type='shipping')
            return qs
        if city:
            qs = qs.filter(city_id=city)
        return qs
