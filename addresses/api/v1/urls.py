from django.conf.urls import url
from django.urls import path
from addresses.api.v1.views import (CountryView, StateView, CityView, AreaView,
        AddressView, AddressDetail, PinCityStateView)

urlpatterns = [
    path('country/', CountryView.as_view(), name='coutry-list', ),
    path('state/', StateView.as_view(), name='state-list', ),
    path('city/', CityView.as_view(), name='city-list', ),
    path('area/', AreaView.as_view(), name='area-list', ),
    path('address/', AddressView.as_view(), name='address-list', ),
    path('get-city-state/', PinCityStateView.as_view()),
]
