from django.conf.urls import include, url
from .views import PutAwayViewSet, BinViewSet, PutAwayProduct, PickupList, BinIDList, PickupDetail, PickupComplete, \
    CheckBinID, DecodeBarcode, PickupRemarksList

urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^bins/$', BinViewSet.as_view(), name='bins'),
    url(r'^put-away/$', PutAwayViewSet.as_view(), name='put-away'),
    url(r'^putaway-products/$', PutAwayProduct.as_view(), name='putaway-products'),
    url(r'^pickup/$', PickupList.as_view(), name='pick-up'),
    url(r'order-bins/$', BinIDList.as_view(), name='order-bins'),
    url(r'pickup-detail/$', PickupDetail.as_view(), name='details'),
    url(r'^pick-complete/$', PickupComplete.as_view(), name='pickup-complete'),
    url(r'^check-bins/$', CheckBinID.as_view(), name='check-bins'),
    url(r'^decode-barcode/$', DecodeBarcode.as_view(), name='decode-barcode'),
    url(r'^pickup-remarks/$', PickupRemarksList.as_view(), name='pickup-remarks')

]