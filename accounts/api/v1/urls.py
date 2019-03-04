from django.conf.urls import url
from django.urls import path
from accounts.api.v1.views import UserDetail, UserDocumentView, CheckAppVersion
urlpatterns = [
    path('user/', UserDetail.as_view(), name='user', ),
    path('user-document/', UserDocumentView.as_view(), name='user-document', ),
    url(r'check-app-version/', CheckAppVersion.as_view(), name='check-app-version', ),

]
