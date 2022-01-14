from django.conf.urls import url

from .views import (PosProductView, CouponOfferCreation, InventoryReport, SalesReport, CustomerReport, VendorView,
                    POView, POProductInfoView, POListView, GrnOrderView, GrnOrderListView, VendorListView,
                    PaymentTypeDetailView, IncentiveView, ShopSpecificationView, GrnReturnOrderView,
                    GetGrnOrderListView, ReturnStatusListView, MeasurementCategoryView, StockUpdateReasonListView,
                    PRNwithoutGRNView, CreateBulkProductView, UpdateInventoryStockView)

urlpatterns = [
    url(r'^catalogue-product/', PosProductView.as_view(), name='catalogue-product'),
    url(r'^product/measurement-category/', MeasurementCategoryView.as_view(), name='pos-measurement-category'),

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

    url(r'^incentive/$', IncentiveView.as_view()),

    url(r'^return-status-choice/$', ReturnStatusListView.as_view()),

    url(r'^shop-specification/$', ShopSpecificationView.as_view()),
    url(r'^stock-update-reason-list/$', StockUpdateReasonListView.as_view()),

    url(r'^upload/catalogue-bulk-product/', CreateBulkProductView.as_view(), name='catalogue-bulk-product'),
    url(r'^upload/update-inventory/', UpdateInventoryStockView.as_view(), name='update-inventory'),

]
