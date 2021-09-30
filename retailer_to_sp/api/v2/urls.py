from django.conf.urls import url

from .views import (CustomerCareApi, CustomerOrdersList, PickerDashboardCrudView,
                    OrderStatusSummaryView, PickerDashboardStatusSummaryView)

urlpatterns = [
    url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
    url('^picker-dashboards/$', PickerDashboardCrudView.as_view(), name='picker-dashboards'),
    url('order-status-summary/', OrderStatusSummaryView.as_view(), name='order-status-summary'),
    url('picker-status-summary/', PickerDashboardStatusSummaryView.as_view(), name='picker-status-summary'),
]
