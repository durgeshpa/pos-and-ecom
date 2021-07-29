from django.conf.urls import include, url

from pos import views
from pos.views import RetailerProductShopAutocomplete, DownloadPurchaseOrder, RetailerProductAutocomplete, InventoryRetailerProductAutocomplete
from pos.filters import PosShopAutocomplete

urlpatterns = [
    url(r'^retailer-product-autocomplete/', RetailerProductShopAutocomplete.as_view(),
        name='retailer-product-autocomplete'),
    url(r'^discounted-product-autocomplete/', RetailerProductAutocomplete.as_view(),
        name='discounted-product-autocomplete'),
    url(r'^fetch-retailer-product/$', views.get_retailer_product, name='fetch-retailer-product',),
    url(r'^pos-shop-autocomplete/$', PosShopAutocomplete.as_view(), name='pos-shop-autocomplete'),
    url(r'^download-purchase-order/(?P<pk>\d+)/$', DownloadPurchaseOrder.as_view(), name='pos_download_purchase_order'),
    url(r'^api/', include('pos.api.urls')),
    url(r'^inventory-product-autocomplete/', InventoryRetailerProductAutocomplete.as_view(),
        name='inventory-product-autocomplete'),
    
]
