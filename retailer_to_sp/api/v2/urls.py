from django.conf.urls import include, url
from .views import (CustomerCareApi, CustomerOrdersList, PickerDashboardCrudView, OrderSummaryView)

urlpatterns = [
    url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
    url('^picker-dashboards/$', PickerDashboardCrudView.as_view(), name='picker-dashboards'),
    url('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
]
