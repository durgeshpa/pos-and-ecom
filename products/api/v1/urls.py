from django.conf.urls import url
from .views import ParentProductView, ParentProductExportAsCSVView, HSNListView, \
    ActiveDeactiveSelectedParentProductView, ProductCappingView, ProductVendorMappingView, ChildProductView, TaxView, \
    BrandListView, CategoryListView, ProductPackingMappingView, SourceProductMappingView, ParentProductListView, \
    ActiveDeactiveSelectedChildProductView, ChildProductExportAsCSVView, TaxListView, TaxExportAsCSVView, \
    WeightView, WeightExportAsCSVView, ProductHSNView, HSNExportAsCSVView, ChildProductListView, VendorListView, \
    ProductStatusListView

urlpatterns = [
    url(r'^parent-product/', ParentProductView.as_view(), name='parent-product'),
    url(r'^get-parent-product/', ParentProductListView.as_view(), name='get-parent-product'),
    url(r'^child-product/', ChildProductView.as_view(), name='child-product'),
    url(r'^parent-download-bulk-product/', ParentProductExportAsCSVView.as_view(), name='parent-download-bulk-product'),
    url(r'^parent-product-active-deactive/', ActiveDeactiveSelectedParentProductView.as_view(),
        name='parent-product-active-deactive'),
    url(r'^product-capping/', ProductCappingView.as_view(), name='product-capping'),
    url(r'^product-vendor-mapping/', ProductVendorMappingView.as_view(), name='product-vendor-mapping'),
    url(r'^product-hsn/', HSNListView.as_view(), name='product-hsn'),
    url(r'^tax/', TaxListView.as_view(), name='tax'),
    url(r'^product-tax/', TaxView.as_view(), name='product-tax'),
    url(r'^brand/', BrandListView.as_view(), name='brand'),
    url(r'^category/', CategoryListView.as_view(), name='category'),
    url(r'^product-package-mapping/', ProductPackingMappingView.as_view(), name='product-package-mapping'),
    url(r'^source-product-mapping/', SourceProductMappingView.as_view(), name='source-product-mapping'),
    url(r'^child-product-active-deactive/', ActiveDeactiveSelectedChildProductView.as_view(),
        name='child-product-active-deactive'),
    url(r'^child-download-bulk-product/', ChildProductExportAsCSVView.as_view(), name='child-download-bulk-product'),
    url(r'^export-csv-tax/', TaxExportAsCSVView.as_view(), name='export-csv-tax'),
    url(r'^weight/', WeightView.as_view(), name='weight'),
    url(r'^export-csv-weight/', WeightExportAsCSVView.as_view(), name='export-csv-weight'),
    url(r'^export-csv-hsn/', HSNExportAsCSVView.as_view(), name='export-csv-hsn'),
    url(r'^hsn/', ProductHSNView.as_view(), name='hsn'),
    url(r'^child-product-list/', ChildProductListView.as_view(), name='child-product-list'),
    url(r'^vendor-list/', VendorListView.as_view(), name='vendor-list'),
    url(r'^status-list/', ProductStatusListView.as_view(), name='status-list'),

]
