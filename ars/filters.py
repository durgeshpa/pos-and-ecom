from dal import autocomplete
from dal_admin_filters import AutocompleteFilter
from django.db.models import Q

from products.models import ParentProduct
from shops.models import Shop


class WarehouseFilter(AutocompleteFilter):
    title = 'Warehouse'
    field_name = 'warehouse'
    autocomplete_url = 'ars-warehouse-autocomplete'

class ParentProductFilter(AutocompleteFilter):
    title = 'Parent Product ID/Name'
    field_name = 'parent_product'
    autocomplete_url = 'ars-parent-product-autocomplete'

