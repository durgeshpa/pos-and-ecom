from django.conf.urls import include, url
from banner.api.v1 import views
from .views import (CategoryProductReport, GRNReport, MasterReport, OrderReport, RetailerProfileReport)

urlpatterns = [
    url(r'^product-category-report/$', CategoryProductReport.as_view(), name='product_category_report'),
    url(r'^grn-report/$', GRNReport.as_view(), name='grn_report'),
    url(r'^master-report/$', MasterReport.as_view(), name='master_report'),
    url(r'^order-report/$', OrderReport.as_view(), name='order_report'),
    url(r'^retailer-report/$', RetailerProfileReport.as_view(), name='retailer_profile_report'),
]
