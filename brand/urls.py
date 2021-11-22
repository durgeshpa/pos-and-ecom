from django.conf.urls import include, url
from .views import ShopAutocomplete

urlpatterns = [
    url(r'^api/', include('brand.api.urls')),
    url(r'^shop-autocomplete/$', ShopAutocomplete.as_view(), name='shop-autocomplete',),
]
