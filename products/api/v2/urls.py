from django.conf.urls import url
from .views import BulkCreateUpdateAttributesView, BulkDownloadProductAttributes, ParentProductMultiImageUploadView, \
    ChildProductMultiImageUploadView, BulkChoiceView, BrandMultiImageUploadView, CategoryMultiImageUploadView, \
    CategoryListView, CreateProductVendorMappingSampleView, CreateProductVendorMappingView, SlabProductPriceSampleCSV, \
    CreateBulkSlabProductPriceView, DiscountedProductPriceSampleCSV, CreateBulkDiscountedProductPriceView, \
        B2cCategoryListView, B2cCategoryMultiImageUploadView

urlpatterns = [
    url(r'^upload_type/bulk-choice/', BulkChoiceView.as_view(),
        name='upload_type/bulk-choice'),
    url(r'^upload_type/category-options/', CategoryListView.as_view(),
        name='upload_type/category-options'),
    url(r'^upload_type/b2c-category-options/', B2cCategoryListView.as_view(),
        name='upload_type/b2c-category-options'),
    url(r'^upload/bulk-upload-master-data/', BulkCreateUpdateAttributesView.as_view(),
        name='upload/bulk-upload-master-data'),
    url(r'^download/bulk-download-master-data/', BulkDownloadProductAttributes.as_view(),
        name='download/bulk-download-master-data'),
    url(r'^upload/parent-product-multiple-image-upload/', ParentProductMultiImageUploadView.as_view(),
        name='upload/parent-product-multiple-image-upload'),
    url(r'^upload/child-product-multiple-image-upload/', ChildProductMultiImageUploadView.as_view(),
        name='upload/child-product-multiple-image-upload'),
    url(r'^upload/brand-multiple-image-upload/', BrandMultiImageUploadView.as_view(),
        name='upload/brand-multiple-image-upload'),
    url(r'^upload/category-multiple-image-upload/', CategoryMultiImageUploadView.as_view(),
        name='upload/category-multiple-image-upload'),
    url(r'^upload/b2c-category-multiple-image-upload/', B2cCategoryMultiImageUploadView.as_view(),
        name='upload/b2c-category-multiple-image-upload'),
    url(r'^download/product-vendor-mapping-sample/', CreateProductVendorMappingSampleView.as_view(),
        name='download/product-vendor-mapping-sample'),
    url(r'^upload/product-vendor-mapping/', CreateProductVendorMappingView.as_view(),
        name='upload/product-vendor-mapping'),
    url(r'^download/product-slab-price-sample/', SlabProductPriceSampleCSV.as_view(),
        name='download/product-slab-price-sample'),
    url(r'^download/discounted-product-price-sample/', DiscountedProductPriceSampleCSV.as_view(),
        name='download/discounted-product-price-sample'),
    url(r'^upload/bulk-product-slab-price/', CreateBulkSlabProductPriceView.as_view(),
        name='upload/bulk-product-slab-price'),
    url(r'^upload/discounted-bulk-product-price/', CreateBulkDiscountedProductPriceView.as_view(),
        name='upload/discounted-bulk-product-price'),

]
