from django.conf.urls import include, url
from pos.views import CatalogueProductCreation, CouponOfferCreation, RetailerProductShopAutocomplete

urlpatterns = [
    url(r'^catalogue_product/', CatalogueProductCreation.as_view(), name='catalogue_product'),
    url(r'^retailer-product-autocomplete/', RetailerProductShopAutocomplete.as_view(), name='retailer-product-autocomplete'),
    url(r'^cart_product_offers/', CouponOfferCreation.as_view(), name='cart_product_offers'),
    url(r'^api/', include('pos.api.urls')),

]
