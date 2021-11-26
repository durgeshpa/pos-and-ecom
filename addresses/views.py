from dal import autocomplete
from addresses.models import City, Pincode


class CityNonMappedToDispatchCenterAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        dispatch_center = self.forwarded.get('dispatch_center', None)
        state = self.forwarded.get('state', None)
        qs = City.objects.all()
        if dispatch_center:
            qs = qs.filter(city_center_mapping__dispatch_center_id=dispatch_center)
        else:
            qs = qs.filter(city_center_mapping__isnull=True)
        if state:
            qs = qs.filter(state=state)
        if self.q:
            qs = qs.filter(city_name__icontains=self.q)
        return qs.distinct('city_name')


class PincodeNonMappedToDispatchCenterAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        dispatch_center = self.forwarded.get('dispatch_center', None)
        city = self.forwarded.get('city', None)
        qs = Pincode.objects.all()
        if dispatch_center:
            qs = qs.filter(pincode_center_mapping__dispatch_center_id=dispatch_center)
        else:
            qs = qs.filter(pincode_center_mapping__isnull=True)
        if city:
            qs = qs.filter(city_id=city)
        if self.q:
            qs = qs.filter(pincode__icontains=self.q)
        return qs.distinct('pincode')
