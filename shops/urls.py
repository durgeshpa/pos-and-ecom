from django.conf.urls import include, url
from django.contrib import admin

from .filters import SkuFilterComplete
from .views import PosShopAutocomplete, ShopParentAutocomplete, ShopRetailerAutocomplete, BeatUserMappingCsvSample, BeatUserMappingCsvView, \
    Skufilter, UserAutocomplete

urlpatterns = [
    url(r'^api/', include('shops.api.urls')),
    url(r'^shop-parent-autocomplete/$', ShopParentAutocomplete.as_view(), name='shop-parent-autocomplete',),
    url(r'^shop-retailer-autocomplete/$', ShopRetailerAutocomplete.as_view(), name='shop-retailer-autocomplete',),
    url(r'^upload/beat_csv/sample/$', BeatUserMappingCsvSample.as_view(), name="shop-beat-upload-csv-sample"),
    url(r'^upload/csv/$', BeatUserMappingCsvView.as_view(), name="user-upload-csv"),
    url(r'^sku-autocomplete/$',SkuFilterComplete.as_view(),name='sku-autocomplete'),
    url(r'^user-autocomplete/$', UserAutocomplete.as_view(), name='user-autocomplete'),
    url(r'^pos-shop-autocomplete/$', PosShopAutocomplete.as_view(), name='pos-shop-autocomplete',),

]
