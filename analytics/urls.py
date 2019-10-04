from django.conf.urls import include, url
from django.contrib import admin
from .views import populate_category_product, populate_grn, populate_product, populate_order

urlpatterns = [
    url(r'^product-category-report/$', populate_category_product, name='product-category-report',),
    url(r'^grn-report/$', populate_grn, name='grn-report',),
    url(r'^api/', include('analytics.api.urls')),
]
