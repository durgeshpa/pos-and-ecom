from django.conf.urls import include, url
from franchise.filters import FranchiseShopAutocomplete


urlpatterns = [
    url(r'^franchise-shop-autocomplete/$', FranchiseShopAutocomplete.as_view(), name='franchise-shop-autocomplete')
]