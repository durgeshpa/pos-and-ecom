from django.conf.urls import url
from .views import ProductPriceAutocomplete

urlpatterns = [
    url(r'^product-price-autocomplete/$', ProductPriceAutocomplete.as_view(), name="product-price-autocomplete"),
]
