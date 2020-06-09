from django.conf.urls import include, url
from django.contrib import admin
from .views import ShopParentAutocomplete, ShopRetailerAutocomplete, BeatUserMappingCsvSample

urlpatterns = [
    url(r'^api/', include('shops.api.urls')),
    url(r'^shop-parent-autocomplete/$', ShopParentAutocomplete.as_view(), name='shop-parent-autocomplete',),
    url(r'^shop-retailer-autocomplete/$', ShopRetailerAutocomplete.as_view(), name='shop-retailer-autocomplete',),
    url(r'^upload/beat_csv/sample/$', BeatUserMappingCsvSample.as_view(), name="shop-beat-upload-csv-sample")
]
