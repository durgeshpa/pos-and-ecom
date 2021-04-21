from django.conf.urls import include, url
from pos.views import RetailerProductShopAutocomplete

urlpatterns = [
    url(r'^retailer-product-autocomplete/', RetailerProductShopAutocomplete.as_view(),
        name='retailer-product-autocomplete'),
    url(r'^api/', include('pos.api.urls')),
]
