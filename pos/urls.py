from django.conf.urls import include, url

from pos import views
from pos.api.v1.views import UpdateInventoryStockView
from pos.views import RetailerProductShopAutocomplete, DownloadPurchaseOrder, RetailerProductAutocomplete, \
    InventoryRetailerProductAutocomplete, RetailerOrderReturnCreditNoteView, RetailerOrderProductInvoiceView, \
    products_list_status, RetailerProductStockDownload, RetailerCatalogueSampleFile
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
    url(r'^retailer-order-return-credit-note/(?P<pk>\d+)/', RetailerOrderReturnCreditNoteView.as_view(),
        name='retailer-order-return-credit-note'),
    url(r'^retailer-order-invoice/(?P<pk>\d+)/', RetailerOrderProductInvoiceView.as_view(),
        name='retailer-order-invoice'),
    url(r'^products_list_status/(?P<product_status_info>(.*))/', views.products_list_status,
        name='products_list_status'),
    url(r'^download/update-inventory-sample/', views.RetailerProductStockDownload, name='update-inventory-sample'),
    url(r'^download/create-update-product-sample/', views.RetailerCatalogueSampleFile,
        name='create-update-product-sample'),
    url(r'^download/retailer_products_csv_download/', views.DownloadRetailerCatalogue,
        name='retailer_products_csv_download'),
    
]
