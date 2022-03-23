from django.conf.urls import url
from .views import ParentProductView, ParentProductExportAsCSVView, HSNListView, \
    ActiveDeactiveSelectedParentProductView, ProductCappingView, ProductVendorMappingView, ChildProductView, TaxView, \
    BrandListView, CategoryListView, ProductPackingMappingView, SourceProductMappingView, ParentProductListView, \
    ActiveDeactiveSelectedChildProductView, ChildProductExportAsCSVView, TaxListView, TaxExportAsCSVView, \
    WeightView, WeightExportAsCSVView, ProductHSNView, HSNExportAsCSVView, ChildProductListView, VendorListView, \
    ProductStatusListView, ProductVendorMappingExportAsCSVView, ActiveChildProductListView, SellerShopListView, \
    BuyerShopListView, CityListView, PinCodeListView, SlabProductPriceView, ProductPriceStatusListView, \
    DisapproveSelectedProductPriceView, ProductSlabPriceExportAsCSVView, ProductListView, DiscountProductView, \
    DiscountProductListForManualPriceView, B2cCategoryListView, HSNExportAsCSVUploadView, \
    ParentProductsTaxStatusChoicesView, ParentProductApprovalView, HSNExportAsCSVSampleDownloadView

urlpatterns = [
    url(r'^parent-product/', ParentProductView.as_view(), name='parent-product'),
    url(r'^get-parent-product/', ParentProductListView.as_view(), name='get-parent-product'),
    url(r'^child-product/', ChildProductView.as_view(), name='child-product'),
    url(r'^discounted-child-product/', DiscountProductView.as_view(), name='discounted-child-product'),
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
    url(r'^b2c-category/', B2cCategoryListView.as_view(), name='b2c-category'),
    url(r'^product-package-mapping/', ProductPackingMappingView.as_view(), name='product-package-mapping'),
    url(r'^source-product-mapping/', SourceProductMappingView.as_view(), name='source-product-mapping'),
    url(r'^child-product-active-deactive/', ActiveDeactiveSelectedChildProductView.as_view(),
        name='child-product-active-deactive'),
    url(r'^child-download-bulk-product/', ChildProductExportAsCSVView.as_view(), name='child-download-bulk-product'),
    url(r'^export-csv-tax/', TaxExportAsCSVView.as_view(), name='export-csv-tax'),
    url(r'^weight/', WeightView.as_view(), name='weight'),
    url(r'^export-csv-weight/', WeightExportAsCSVView.as_view(), name='export-csv-weight'),
    url(r'^export-csv-hsn/', HSNExportAsCSVView.as_view(), name='export-csv-hsn'),
    url(r'^download-csv-hsn-sample/', HSNExportAsCSVSampleDownloadView.as_view(), name='download-csv-hsn-sample'),
    url(r'^upload-csv-hsn/', HSNExportAsCSVUploadView.as_view(), name='upload-csv-hsn'),
    url(r'^hsn/', ProductHSNView.as_view(), name='hsn'),
    url(r'^child-product-list/', ActiveChildProductListView.as_view(), name='child-product-list'),
    url(r'^vendor-list/', VendorListView.as_view(), name='vendor-list'),
    url(r'^status-list/', ProductStatusListView.as_view(), name='status-list'),
    url(r'^export-csv-product-vendor-mapping/', ProductVendorMappingExportAsCSVView.as_view(),
        name='export-csv-product-vendor-mapping'),
    url(r'^all-child-product-list/', ChildProductListView.as_view(), name='all-child-product-list'),
    url(r'^seller-shop-list/', SellerShopListView.as_view(), name='seller-shop-list'),
    url(r'^buyer-shop-list/', BuyerShopListView.as_view(), name='buyer-shop-list'),
    url(r'^pincode-list/', PinCodeListView.as_view(), name='pincode-list'),
    url(r'^city-list/', CityListView.as_view(), name='city-list'),
    url(r'^slab-product-price/', SlabProductPriceView.as_view(), name='slab-product-price'),
    url(r'^disapprove-selected-product-price/', DisapproveSelectedProductPriceView.as_view(),
        name='disapprove-selected-product-price'),
    url(r'^export-slab-product-price-csv/', ProductSlabPriceExportAsCSVView.as_view(),
        name='export-slab-product-price-csv'),
    url(r'^product-price-status-list/', ProductPriceStatusListView.as_view(), name='product-price-status-list'),
    url(r'^product-list/', ProductListView.as_view(), name='product-list'),
    url(r'^discounted-product-list/', DiscountProductListForManualPriceView.as_view(), name='discounted-product-list'),
    url(r'^parent-product-tax-status-list/', ParentProductsTaxStatusChoicesView.as_view(), name='tax-status-list'),
    url(r'^parent-product-approval/', ParentProductApprovalView.as_view(), name='parent-product-approval'),

]
