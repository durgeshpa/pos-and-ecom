from django.conf.urls import include, url
from .views import EcomProductAutoCompleteView, EcomShopAutoCompleteView

urlpatterns = [
    url(r'^api/', include('ecom.api.urls')),
    url(r'^ecom-shop-autocomplete', EcomShopAutoCompleteView.as_view(), name='ecom-shop-autocomplete'),
    url(r'^ecom-tagproduct-autocomplete', EcomProductAutoCompleteView.as_view(), name='ecom-tagproduct-autocomplete'),
]
