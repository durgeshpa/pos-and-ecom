from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
url(r'^api/', include('retailer_to_gram.api.urls')),
]
