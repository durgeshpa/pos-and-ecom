from django.conf.urls import url
from .views import ParentProduct, ParentProductBulkUpload, ParentProductExportAsCSV, \
    ActiveDeactivateSelectedProduct, ProductCapping

urlpatterns = [
    url(r'^parent-product/', ParentProduct.as_view(), name='parent-product'),
    url(r'^parent-bulk-product/', ParentProductBulkUpload.as_view(), name='parent-bulk-product'),
    url(r'^parent-download-bulk-product/', ParentProductExportAsCSV.as_view(), name='parent-download-bulk-product'),
    url(r'^parent-active-deactive-product/', ActiveDeactivateSelectedProduct.as_view(), name='parent-active-deactive-product'),
    url(r'^product-capping/', ProductCapping.as_view(), name='product-capping')
]
