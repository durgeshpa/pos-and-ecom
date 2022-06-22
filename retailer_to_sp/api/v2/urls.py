from django.conf.urls import url

from .views import (CustomerCareApi, CustomerOrdersList, 
                    GFReturnOrderList, GetReturnChallan, ReturnChallanList)

urlpatterns = [
    # url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    # url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
    url('^gf-return-order-list/$', GFReturnOrderList.as_view(), name='gf_return_order_list'),
    url(r'^gf-return-order-list/(?P<pk>\d+)/$', GFReturnOrderList.as_view(), name='gf_return_order_list_detail'),
    url(r'^get-return-challan/$', GetReturnChallan.as_view(), name='get_return_challan'),
    url(r'^get-return-challan-list/$', ReturnChallanList.as_view(), name='return_challan_list')
]
