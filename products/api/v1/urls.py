from django.conf.urls import url
from .views import ParentProduct, ParentProductBulkUpload, ParentProductExportAsCSV

urlpatterns = [
    url(r'^parent-product/', ParentProduct.as_view(), name='parent-product'),
    url(r'^parent-bulk-product/', ParentProductBulkUpload.as_view(), name='parent-bulk-product'),
    url(r'^parent-download-bulk-product/', ParentProductExportAsCSV.as_view(), name='parent-download-bulk-product'),
]
