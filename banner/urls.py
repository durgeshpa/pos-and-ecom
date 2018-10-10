from django.conf.urls import include, url
from django.contrib import admin
from banner import views
from . import views

urlpatterns = [

url(r'^api/', include('banner.api.urls')),
]
