from django.conf.urls import include, url
from django.contrib import admin
from .views import ShopParentAutocomplete, ShopRetailerAutocomplete, ShopMappedProduct,StockCorrectionUploadSample

urlpatterns = [
    url(r'^api/', include('shops.api.urls')),
    url(r'^shop-parent-autocomplete/$', ShopParentAutocomplete.as_view(), name='shop-parent-autocomplete',),
    url(r'^shop-retailer-autocomplete/$', ShopRetailerAutocomplete.as_view(), name='shop-retailer-autocomplete',),
    url(r'^shop-mapped/(?P<pk>\d+)/product/$',ShopMappedProduct.as_view(),name="shop_mapped_product"),
    url(r'^stock-correction-upload-sample/$',StockCorrectionUploadSample,name="stock_correction_upload_sample"),
]
