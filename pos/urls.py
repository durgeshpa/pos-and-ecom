from django.conf.urls import include, url
from pos.views import CatalogueProductCreation, CouponOfferCreation, RetailerProductShopAutocomplete

urlpatterns = [
    url(r'^catalogue-product/', CatalogueProductCreation.as_view(), name='catalogue-product'),
    url(r'^retailer-product-autocomplete/', RetailerProductShopAutocomplete.as_view(), name='retailer-product-autocomplete'),
    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),
    url(r'^api/', include('pos.api.urls')),

]
