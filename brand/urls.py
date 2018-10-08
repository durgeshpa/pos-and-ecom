from django.conf.urls import include, url
from django.contrib import admin
from brand import views

urlpatterns = [
url(r'^api/', include('brand.api.urls')),
]
