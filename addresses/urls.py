from django.conf.urls import url, include
from django.urls import path

from addresses.views import CityNonMappedToDispatchCenterAutocomplete, PincodeNonMappedToDispatchCenterAutocomplete

urlpatterns = [
    url(r'^api/', include('addresses.api.urls')),
    path('dispatch-center-cities-autocomplete/', CityNonMappedToDispatchCenterAutocomplete.as_view(),
         name='dispatch-center-cities-autocomplete', ),
    path('dispatch-center-pincodes-autocomplete/', PincodeNonMappedToDispatchCenterAutocomplete.as_view(),
         name='dispatch-center-pincodes-autocomplete', ),
]
