from retailer_backend.admin import InputFilter
from dal import autocomplete
from dal_admin_filters import AutocompleteFilter

from shops.models import Shop


class ShopLocFilter(InputFilter):
    title = 'Shop Location'
    parameter_name = 'shop_loc'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(shop_loc__icontains=value)
        return queryset


class ShopLocFilter1(InputFilter):
    title = 'Shop Location'
    parameter_name = 'location_name'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(location_name__icontains=value)
        return queryset


class BarcodeFilter(InputFilter):
    title = 'Barcode / Product Ean'
    parameter_name = 'barcode'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(barcode=value)
        return queryset


class SkuFilter(InputFilter):
    title = 'Product SKU'
    parameter_name = 'product_sku'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(product_sku=value)
        return queryset


class ShopFilter(AutocompleteFilter):
    title = 'Shop'
    field_name = 'shop'
    autocomplete_url = 'franchise-shop-autocomplete'


class FranchiseShopAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()
        qs = Shop.objects.filter(
            shop_type__shop_type='f')
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class WarehouseFilter(AutocompleteFilter):
    title = 'Warehouse'
    field_name = 'warehouse'
    autocomplete_url = 'franchise-shop-autocomplete'