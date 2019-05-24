from django.conf.urls import include, url
from .views import (CustomerCareApi, CustomerOrdersList)

urlpatterns = [
    url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
]
