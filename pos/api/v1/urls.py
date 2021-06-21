from django.conf.urls import url

from .views import PosProductView, CouponOfferCreation, InventoryReport, InventoryLogReport, SalesReport

urlpatterns = [
    url(r'^catalogue-product/', PosProductView.as_view(), name='catalogue-product'),
    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),
    url(r'^inventory-report/', InventoryReport.as_view(), name='inventory-report'),
    url(r'^product-inventory-log/(?P<pk>\d+)/$', InventoryLogReport.as_view(), name='product-inventory-log'),
    url(r'^sales-report/', SalesReport.as_view(), name='sales-report'),
]
