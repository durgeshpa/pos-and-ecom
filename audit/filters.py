from dal import autocomplete

from accounts.models import User
from shops.models import Shop


class WareHouseComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()

        qs = Shop.objects.filter(shop_type__shop_type='sp')

        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class AssignedUserFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return User.objects.none()

        qs = User.objects.all()

        if self.q:
            qs = qs.filter(first_name__icontains=self.q)
        return qs

