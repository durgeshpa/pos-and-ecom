import django_filters
from django_filters import rest_framework as filters
from rangefilter.filter import DateTimeRangeFilter

from retailer_backend.admin import InputFilter

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


class InvoiceAdminTripFilter(InputFilter):
    parameter_name = 'dispatch_no'
    title = 'Trip'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(shipment__trip__dispatch_no__icontains=self.value())


class InvoiceAdminOrderFilter(InputFilter):
    parameter_name = 'order_no'
    title = 'Order'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(shipment__order__order_no__icontains=self.value())


class InvoiceCreatedAt(DateTimeRangeFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = 'Invoice Created At'


class DeliveryStartsAt(DateTimeRangeFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = 'Delivery Starts At'


class DeliveryCompletedAt(DateTimeRangeFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = 'Delivery Completed At'


class OrderCreatedAt(DateTimeRangeFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = 'Order Created At'
