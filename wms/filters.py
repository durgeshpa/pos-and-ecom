from dal import autocomplete
from shops.models import Shop
from wms.models import InventoryType, InventoryState


class WareHouseComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()

        qs = Shop.objects.filter(
            shop_type__shop_type='sp')

        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class InventoryTypeFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return InventoryType.objects.none()

        qs = InventoryType.objects.all()

        if self.q:
            qs = qs.filter(inventory_type_name__icontains=self.q)
        return qs


class InventoryStateFilter(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return InventoryState.objects.none()

        qs = InventoryState.objects.all()

        if self.q:
            qs = qs.filter(inventory_state_name__icontains=self.q)
        return qs
