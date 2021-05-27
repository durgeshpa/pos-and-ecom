from django.conf.urls import url
from .views import ParentProductView, ParentProductBulkUploadView, ParentProductExportAsCSVView, ProductHSNView, \
    ActiveDeactivateSelectedProductView, ProductCappingView, ProductVendorMappingView, ChildProductView

urlpatterns = [
    url(r'^parent-product/', ParentProductView.as_view(), name='parent-product'),
    url(r'^child-product/', ChildProductView.as_view(), name='child-product'),
    url(r'^parent-bulk-product/', ParentProductBulkUploadView.as_view(), name='parent-bulk-product'),
    url(r'^parent-download-bulk-product/', ParentProductExportAsCSVView.as_view(), name='parent-download-bulk-product'),
    url(r'^parent-active-deactive-product/', ActiveDeactivateSelectedProductView.as_view(), name='parent-active-deactive-product'),
    url(r'^product-capping/', ProductCappingView.as_view(), name='product-capping'),
    url(r'^product-vendor-mapping/', ProductVendorMappingView.as_view(), name='product-vendor-mapping'),
    url(r'^product-hsn/', ProductHSNView.as_view(), name='product-hsn'),
]
