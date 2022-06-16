from django.conf.urls import url

from .views import (CustomerCareApi, CustomerOrdersList, 
                    GFReturnOrderList, GetReturnChallan)

urlpatterns = [
    # url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    # url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
    url('^gf-return-order-list/$', GFReturnOrderList.as_view(), name='gf_return_order_list'),
    url(r'^get-return-challan/(?P<pk>\d+)/$', GetReturnChallan.as_view(), name='get_return_challan')
]
