from django.conf.urls import include, url
from pos.views import RetailerProductShopAutocomplete
from pos.filters import PosShopAutocomplete

urlpatterns = [
    url(r'^retailer-product-autocomplete/', RetailerProductShopAutocomplete.as_view(),
        name='retailer-product-autocomplete'),
    url(r'^pos-shop-autocomplete/$', PosShopAutocomplete.as_view(), name='pos-shop-autocomplete'),
    url(r'^api/', include('pos.api.urls')),
]
