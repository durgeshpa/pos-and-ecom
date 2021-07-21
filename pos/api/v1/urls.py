from django.conf.urls import url

from .views import (PaymentTypeDetailView, PosProductView, CouponOfferCreation, InventoryReport, SalesReport, CustomerReport, VendorView,
                    POView, POProductInfoView)

urlpatterns = [
    url(r'^catalogue-product/', PosProductView.as_view(), name='catalogue-product'),

    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),

    url(r'^inventory-report/', InventoryReport.as_view(), name='inventory-report'),
    url(r'^sales-report/', SalesReport.as_view(), name='sales-report'),
    url(r'^customer-report/', CustomerReport.as_view(), name='customer-report'),

    url(r'^vendor/$', VendorView.as_view(), name='pos-vendor'),
    url(r'^vendor/(?P<pk>\d+)/$', VendorView.as_view()),

    url(r'^purchase-order/$', POView.as_view()),
    url(r'^purchase-order/(?P<pk>\d+)/$', POView.as_view()),
    url(r'^product-info-po/(?P<pk>\d+)/$', POProductInfoView.as_view()),
    url(r'^payment-type/$', PaymentTypeDetailView.as_view()),
]
