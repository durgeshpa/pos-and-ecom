from django.conf.urls import url
from .views import ParentProductView, ParentProductBulkUploadView, ParentProductExportAsCSVView, ProductHSNView, \
    ActiveDeactiveSelectedParentProductView, ProductCappingView, ProductVendorMappingView, ChildProductView, TaxView, \
    BrandView, CategoryView, ProductPackingMappingView, SourceProductMappingView, ParentProductGetView, \
    ActiveDeactiveSelectedChildProductView, ChildProductExportAsCSVView, GetTaxView, BulkUploadProductAttributes

urlpatterns = [
    url(r'^parent-product/', ParentProductView.as_view(), name='parent-product'),
    url(r'^get-parent-product/', ParentProductGetView.as_view(), name='get-parent-product'),
    url(r'^child-product/', ChildProductView.as_view(), name='child-product'),
    url(r'^parent-bulk-product/', ParentProductBulkUploadView.as_view(), name='parent-bulk-product'),
    url(r'^parent-download-bulk-product/', ParentProductExportAsCSVView.as_view(), name='parent-download-bulk-product'),
    url(r'^parent-product-active-deactive/', ActiveDeactiveSelectedParentProductView.as_view(), name='parent-product-active-deactive'),
    url(r'^product-capping/', ProductCappingView.as_view(), name='product-capping'),
    url(r'^product-vendor-mapping/', ProductVendorMappingView.as_view(), name='product-vendor-mapping'),
    url(r'^product-hsn/', ProductHSNView.as_view(), name='product-hsn'),
    url(r'^tax/', GetTaxView.as_view(), name='tax'),
    url(r'^product-tax/', TaxView.as_view(), name='product-tax'),
    url(r'^brand/', BrandView.as_view(), name='brand'),
    url(r'^category/', CategoryView.as_view(), name='category'),
    url(r'^product-package-mapping/', ProductPackingMappingView.as_view(), name='product-source'),
    url(r'^source-product-mapping/', SourceProductMappingView.as_view(), name='product-source'),
    url(r'^child-product-active-deactive/', ActiveDeactiveSelectedChildProductView.as_view(),
        name='child-product-active-deactive'),
    url(r'^child-download-bulk-product/', ChildProductExportAsCSVView.as_view(), name='child-download-bulk-product'),
    url(r'^bulk-upload-master-data/', BulkUploadProductAttributes.as_view(), name='bulk-upload-master-data'),

]
