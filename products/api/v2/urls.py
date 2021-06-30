from django.conf.urls import url
from .views import BulkUploadProductAttributes, BulkDownloadProductAttributes, ProductCategoryMapping, \
    ParentProductMultiImageUploadView, ChildProductMultiImageUploadView, BulkUploadLogView

urlpatterns = [
    url(r'^upload/bulk-upload-master-data/', BulkUploadProductAttributes.as_view(),
        name='upload/bulk-upload-master-data'),
    url(r'^download/bulk-download-master-data/', BulkDownloadProductAttributes.as_view(),
        name='download/bulk-download-master-data'),
    url(r'^upload/product-category-mapping/', ProductCategoryMapping.as_view(),
        name='upload/product-category-mapping'),
    url(r'^upload/parent-product-multiple-image-upload/', ParentProductMultiImageUploadView.as_view(),
        name='upload/parent-product-multiple-image-upload'),
    url(r'^upload/child-product-multiple-image-upload/', ChildProductMultiImageUploadView.as_view(),
        name='upload/child-product-multiple-image-upload'),
    url(r'^upload/bulk-upload-log/', BulkUploadLogView.as_view(),
        name='upload/bulk-upload-log/'),


]
