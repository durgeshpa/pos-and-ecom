from django.conf.urls import url
from django.urls import path
from accounts.api.v1.views import (GroupsListView, UserDetail, UserDocumentView, 
CheckAppVersion, CheckDeliveryAppVersion, CheckEcommerceAppVersion, CheckPosAppVersion, CheckWarehouseAppVersion)

urlpatterns = [
    path('user/', UserDetail.as_view(), name='user', ),
    path('user-document/', UserDocumentView.as_view(), name='user-document', ),
    url(r'check-app-version/', CheckAppVersion.as_view(), name='check-app-version', ),
    url(r'check-delivery-app-version/', CheckDeliveryAppVersion.as_view(), name='check delivery app version', ),
    url(r'check-ecommerce-app-version/', CheckEcommerceAppVersion.as_view(), name='check ecommerce app version', ),
    url(r'check-pos-app-version/', CheckPosAppVersion.as_view(), name='check pos app version', ),
    url(r'check-warehouse-app-version/', CheckWarehouseAppVersion.as_view(), name='check warehouse app version', ),
    path('groups/', GroupsListView.as_view(), name='groups', ),

]
