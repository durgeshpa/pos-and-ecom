from django.conf.urls import include, url
from django.urls import path

from .filters import SkuFilterComplete
from .views import ShopParentAutocomplete, ShopRetailerAutocomplete, BeatUserMappingCsvSample, BeatUserMappingCsvView, \
    UserAutocomplete, CityNonMappedToDispatchCenterAutocomplete, PincodeNonMappedToDispatchCenterAutocomplete

urlpatterns = [
    url(r'^api/', include('shops.api.urls')),
    url(r'^shop-parent-autocomplete/$', ShopParentAutocomplete.as_view(), name='shop-parent-autocomplete',),
    url(r'^shop-retailer-autocomplete/$', ShopRetailerAutocomplete.as_view(), name='shop-retailer-autocomplete',),
    url(r'^upload/beat_csv/sample/$', BeatUserMappingCsvSample.as_view(), name="shop-beat-upload-csv-sample"),
    url(r'^upload/csv/$', BeatUserMappingCsvView.as_view(), name="user-upload-csv"),
    url(r'^sku-autocomplete/$',SkuFilterComplete.as_view(),name='sku-autocomplete'),
    url(r'^user-autocomplete/$', UserAutocomplete.as_view(), name='user-autocomplete'),
    path('dispatch-center-cities-autocomplete/', CityNonMappedToDispatchCenterAutocomplete.as_view(),
         name='dispatch-center-cities-autocomplete', ),
    path('dispatch-center-pincodes-autocomplete/', PincodeNonMappedToDispatchCenterAutocomplete.as_view(),
         name='dispatch-center-pincodes-autocomplete', ),
]
