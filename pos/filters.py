from dal import autocomplete
from dal_admin_filters import AutocompleteFilter

from django.db.models import Q

from retailer_backend.admin import InputFilter
from shops.models import Shop


class ShopFilter(AutocompleteFilter):
    title = 'Shop'
    field_name = 'shop'
    autocomplete_url = 'pos-shop-autocomplete'


class PosShopAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return Shop.objects.none()
        qs = Shop.objects.filter()
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class ProductEanSearch(InputFilter):
    parameter_name = 'product_ean_search'
    title = 'Product Ean Code'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(Q(product_ean_code__icontains=self.value()))


class ProductInvEanSearch(InputFilter):
    parameter_name = 'product_ean_search'
    title = 'Product Ean Code'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(Q(product__product_ean_code__icontains=self.value()))
