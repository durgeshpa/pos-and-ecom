from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^v1/', include('analytics.api.v1.urls')),
]
