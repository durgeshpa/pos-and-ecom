from django.conf.urls import url

from .views import PosProductView, CouponOfferCreation, InventoryReport, SalesReport, CustomerReport, VendorView

urlpatterns = [
    url(r'^catalogue-product/', PosProductView.as_view(), name='catalogue-product'),

    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),

    url(r'^inventory-report/', InventoryReport.as_view(), name='inventory-report'),
    url(r'^sales-report/', SalesReport.as_view(), name='sales-report'),
    url(r'^customer-report/', CustomerReport.as_view(), name='customer-report'),

    url(r'^vendor/$', VendorView.as_view(), name='pos-vendor'),
    url(r'^vendor/(?P<pk>\d+)/$', VendorView.as_view()),
]
