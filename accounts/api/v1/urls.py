from django.conf.urls import url
from django.urls import path
from accounts.api.v1.views import UserDetail
urlpatterns = [
    path('user/', UserDetail.as_view(), name='user', ),
]
