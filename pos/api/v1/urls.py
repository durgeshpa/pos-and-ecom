from django.conf.urls import url

from rest_framework.routers import DefaultRouter

from .views import (PosProductView, CouponOfferCreation, InventoryReport, SalesReport, CustomerReport, VendorView,
                    POView, POProductInfoView, POListView, GrnOrderView, GrnOrderListView, VendorListView,
                    PaymentTypeDetailView, IncentiveView, ShopSpecificationView, GrnReturnOrderView,
                    GetGrnOrderListView, ReturnStatusListView, MeasurementCategoryView, StockUpdateReasonListView,
                    PRNwithoutGRNView, CreateBulkProductView, UpdateInventoryStockView, Contect_Us, PaymentStatusList,
                    EcomPaymentTypeDetailView, PaymentModeChoicesList, RefundPayment, RetailerProductListViewSet,
                    DownloadRetailerProductCsvShopWiseView, DownloadUploadRetailerProductsCsvSampleFileView, 
                    BulkCreateUpdateRetailerProductsView, LinkRetailerProductsBulkUploadCsvSampleView, LinkRetailerProductBulkUploadView,
                    RetailerProductImageBulkUploadView, PosShopListView)

router = DefaultRouter()

router.register('retailer-products', RetailerProductListViewSet, base_name='retailer-products')

urlpatterns = [
    url(r'^catalogue-product/', PosProductView.as_view(), name='catalogue-product'),
    url(r'^product/measurement-category/', MeasurementCategoryView.as_view(), name='pos-measurement-category'),
    url(r'contct_us_details/', Contect_Us.as_view(), name='contect_us'),

    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),

    url(r'^inventory-report/', InventoryReport.as_view(), name='inventory-report'),
    url(r'^sales-report/', SalesReport.as_view(), name='sales-report'),
    url(r'^customer-report/', CustomerReport.as_view(), name='customer-report'),

    url(r'^vendor/$', VendorView.as_view(), name='pos-vendor'),
    url(r'^vendor/(?P<pk>\d+)/$', VendorView.as_view()),
    url(r'^vendor-list/$', VendorListView.as_view()),

    url(r'^purchase-order/$', POView.as_view()),
    url(r'^purchase-order/(?P<pk>\d+)/$', POView.as_view()),
    url(r'^product-info-po/(?P<pk>\d+)/$', POProductInfoView.as_view()),
    url(r'^purchase-order-list/$', POListView.as_view()),

    url(r'^grn-order/$', GrnOrderView.as_view()),
    url(r'^grn-order/(?P<pk>\d+)/$', GrnOrderView.as_view()),
    url(r'^grn-order-list/$', GrnOrderListView.as_view()),

    url(r'^get-grn-order-list/$', GetGrnOrderListView.as_view()),
    url(r'^return-grn-order/$', GrnReturnOrderView.as_view()),
    url(r'^return-order-without-grn/$', PRNwithoutGRNView.as_view()),

    url(r'^payment-type/$', PaymentTypeDetailView.as_view()),
    url(r'^ecom-payment-type/$', EcomPaymentTypeDetailView.as_view()),

    url(r'^incentive/$', IncentiveView.as_view()),

    url(r'^return-status-choice/$', ReturnStatusListView.as_view()),

    url(r'^shop-specification/$', ShopSpecificationView.as_view()),
    url(r'^stock-update-reason-list/$', StockUpdateReasonListView.as_view()),

    url(r'^upload/catalogue-bulk-product/', CreateBulkProductView.as_view(), name='catalogue-bulk-product'),
    url(r'^upload/update-inventory/', UpdateInventoryStockView.as_view(), name='update-inventory'),

    url(r'^payment-status-choice/$', PaymentStatusList.as_view()),
    url(r'^payment-mode-choice/$', PaymentModeChoicesList.as_view()),
    url(r'^payment-refund/$', RefundPayment.as_view(), name='payment-refund'),
    url(r'^download-retailer-products-csv/$', DownloadRetailerProductCsvShopWiseView.as_view(), name='download-retailer-products-csv'),
    url(r'^download-upload-retailer-products-sample-file/$', DownloadUploadRetailerProductsCsvSampleFileView.as_view(), name='download-upload-retailer-products-sample-file'),
    url(r'^create-update-bulk-retailer-products/$', BulkCreateUpdateRetailerProductsView.as_view(), name='create-update-bulk-retailer-products-file'),
    url(r'^link-retailer-products-sample-file/$', LinkRetailerProductsBulkUploadCsvSampleView.as_view(), name='link-retailer-products-sample-file'),
    url(r'^link-retailer-products-bulk-upload/$', LinkRetailerProductBulkUploadView.as_view(), name='link-retailer-products-bulk-upload'),
    url(r'^upload-retailer-product-images/$', RetailerProductImageBulkUploadView.as_view(), name='upload-retailer-product-images'),
    url(r'^shop-list/$', PosShopListView.as_view(), name='shop-list')
]

urlpatterns += router.urls