from django.conf.urls import url
from django.urls import path
from accounts.api.v1.views import (GroupsListView, UserDetail, UserDocumentView, 
CheckAppVersion, CheckDeliveryAppVersion)

urlpatterns = [
    path('user/', UserDetail.as_view(), name='user', ),
    path('user-document/', UserDocumentView.as_view(), name='user-document', ),
    url(r'check-app-version/', CheckAppVersion.as_view(), name='check-app-version', ),
    url(r'check-delivery-app-version/', CheckDeliveryAppVersion.as_view(), name='check delivery app version', ),
    path('groups/', GroupsListView.as_view(), name='groups', ),

]
