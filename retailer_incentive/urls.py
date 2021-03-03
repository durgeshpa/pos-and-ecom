from django.conf.urls import url
from django.urls import path, include

from . import views
from .views import ShopAutocomplete

urlpatterns = [
    url(r'^api/', include('retailer_incentive.api.v1.urls')),
    url(r'^shop-autocomplete/$', ShopAutocomplete.as_view(), name='shop-autocomplete',),
]