import django_filters 
from django_filters import rest_framework as filters

from retailer_to_sp.models import PickerDashboard
from shops.models import Shop


class PickerDashboardFilter(filters.FilterSet):
    '''
    Filter class for picker
    '''
    shop_id = django_filters.CharFilter(method='filter_shop_id')

    def filter_shop_id(self, queryset, name, value):
        if value:
            shop = Shop.objects.filter(pk=value)
            return queryset.filter(order__seller_shop=shop, picking_status='picking_pending')
        return queryset

    class Meta:
        model = PickerDashboard
        fields = ['shop_id']#'__all__' 
