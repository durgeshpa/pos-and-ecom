from django.conf.urls import include, url
from django.contrib import admin

from .views import (
    ReturnProductAutocomplete, DownloadCreditNote, DownloadPickList, DownloadTripPdf, SellerShopAutocomplete, BuyerShopAutocomplete,
    RetailerCart, PickerNameAutocomplete, DownloadPickListPicker,SellerAutocomplete,
)
urlpatterns = [
    url(r'^api/', include('retailer_to_sp.api.urls')),
    url(r'^return-product-autocomplete/$',
        ReturnProductAutocomplete.as_view(),
        name='return-product-autocomplete', ),
    url('^download-credit-note/(?P<pk>\d+)/note/$',
        DownloadCreditNote.as_view(),
        name='download_credit_note'),
    url('^download-pick-list-sp/(?P<pk>\d+)/list/$',
        DownloadPickList.as_view(),
        name='download_pick_list_sp'),
    url('^download-pick-list-picker-sp/(?P<pk>\d+)/(?P<shipment_id>\d+)/list/$',
        DownloadPickListPicker.as_view(),
        name='download_pick_list_picker_sp'),

    url(r'^seller-shop-autocomplete/$', SellerShopAutocomplete.as_view(), name='seller-shop-autocomplete'),
    url(r'^seller-autocomplete/$', SellerAutocomplete.as_view(), name='seller-autocomplete'),
    url(r'^buyer-shop-autocomplete/$', BuyerShopAutocomplete.as_view(), name='buyer-shop-autocomplete'),
    url('^download-trip-pdf/(?P<pk>\d+)/trip_pdf/$', DownloadTripPdf.as_view(), name='download_trip_pdf'),
    url('^retailer-cart/$', RetailerCart.as_view(), name='retailer_cart'),
    url(r'^picker-name-autocomplete/$', PickerNameAutocomplete.as_view(), name='picker-name-autocomplete'),    
    ]
