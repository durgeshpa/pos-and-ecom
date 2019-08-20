from django.conf.urls import url,include
from rest_framework import routers

urlpatterns = [
    url(r'^v1/', include('notification_center.api.v1.urls')),
]