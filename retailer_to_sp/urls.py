from django.conf.urls import include, url

from .views import (
    ReturnProductAutocomplete, DownloadCreditNote, DownloadPickList, DownloadTripPdf, SellerShopAutocomplete,
    BuyerShopAutocomplete, RetailerCart, PickerNameAutocomplete, DownloadPickListPicker, ShippingAddressAutocomplete,
    BillingAddressAutocomplete, shipment_status, create_franchise_po, ShipmentMergedBarcode
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
    url(r'^buyer-shop-autocomplete/$', BuyerShopAutocomplete.as_view(), name='buyer-shop-autocomplete'),
    url('^download-trip-pdf/(?P<pk>\d+)/trip_pdf/$', DownloadTripPdf.as_view(), name='download_trip_pdf'),
    url('^retailer-cart/$', RetailerCart.as_view(), name='retailer_cart'),
    url(r'^picker-name-autocomplete/$', PickerNameAutocomplete.as_view(), name='picker-name-autocomplete'),
    url(r'^bulk-shipping-address-autocomplete/$',ShippingAddressAutocomplete.as_view(),name='bulk-shipping-address-autocomplete',),
    url(r'^bulk-billing-address-autocomplete/$',BillingAddressAutocomplete.as_view(),name='bulk-billing-address-autocomplete',),
    url(r'^shipment_status/$', shipment_status, name='shipment-status'),
    url(r'^create-franchise-po/(?P<pk>\d+)/$', create_franchise_po, name='create-franchise-po'),
    url(r'^shipment-merged-barcode/(?P<pk>\d+)/$', ShipmentMergedBarcode.as_view(), name='shipment_barcodes', ),
    ]
