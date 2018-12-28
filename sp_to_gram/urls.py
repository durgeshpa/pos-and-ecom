from django.conf.urls import url,include
from .views import abc,GfShopAutocomplete, GfProductAutocomplete, SpProductPrice
urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^api/', abc, name='abc'),
    url(r'^gf-shop-autocomplete/$', GfShopAutocomplete.as_view(), name='gf-shop-autocomplete'),
    url(r'^gf-product-autocomplete/$', GfProductAutocomplete.as_view(), name='gf-product-autocomplete'),
    url(r'^sp-product-price/$', SpProductPrice.as_view(), name='sp-product-price'),
]
