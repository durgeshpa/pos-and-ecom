from django.conf.urls import url
from .views import ParentProduct, ParentProductBulkUpload, ParentProductExportAsCSV, \
    ActiveDeactivateSelectedProduct, ProductCapping, ProductVendorMapping, ChildProduct

urlpatterns = [
    url(r'^parent-product/', ParentProduct.as_view(), name='parent-product'),
    url(r'^child-product/', ChildProduct.as_view(), name='child-product'),
    url(r'^parent-bulk-product/', ParentProductBulkUpload.as_view(), name='parent-bulk-product'),
    url(r'^parent-download-bulk-product/', ParentProductExportAsCSV.as_view(), name='parent-download-bulk-product'),
    url(r'^parent-active-deactive-product/', ActiveDeactivateSelectedProduct.as_view(), name='parent-active-deactive-product'),
    url(r'^product-capping/', ProductCapping.as_view(), name='product-capping'),
    url(r'^product-vendor-mapping/', ProductVendorMapping.as_view(), name='product-vendor-mapping')
]
