from django.conf.urls import include, url
from django.contrib import admin
from .views import ShopParentAutocomplete

urlpatterns = [
    url(r'^api/', include('shops.api.urls')),
    url(r'^shop-parent-autocomplete/$', ShopParentAutocomplete.as_view(), name='shop-parent-autocomplete',)
]
