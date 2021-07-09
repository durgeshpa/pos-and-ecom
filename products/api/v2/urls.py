from django.conf.urls import url
from .views import BulkUploadProductAttributes, BulkDownloadProductAttributes, \
    ParentProductMultiImageUploadView, ChildProductMultiImageUploadView, ChildProductBulkCreateView, \
    ParentProductBulkCreateView, ParentProductsDownloadSampleCSV, ChildProductsDownloadSampleCSV

urlpatterns = [
    url(r'^upload/create-parent-bulk-product/', ParentProductBulkCreateView.as_view(),
        name='create-parent-bulk-product'),
    url(r'^download/parent-bulk-product-sample/', ParentProductsDownloadSampleCSV.as_view(),
        name='download/parent-bulk-product-sample'),
    url(r'^download/child-bulk-product-sample/', ChildProductsDownloadSampleCSV.as_view(),
        name='download/child-bulk-product-sample'),
    url(r'^upload/create-child-bulk-product/', ChildProductBulkCreateView.as_view(), name='create-child-bulk-product'),
    url(r'^upload/bulk-upload-master-data/', BulkUploadProductAttributes.as_view(),
        name='upload/bulk-upload-master-data'),
    url(r'^download/bulk-download-master-data/', BulkDownloadProductAttributes.as_view(),
        name='download/bulk-download-master-data'),
    url(r'^upload/parent-product-multiple-image-upload/', ParentProductMultiImageUploadView.as_view(),
        name='upload/parent-product-multiple-image-upload'),
    url(r'^upload/child-product-multiple-image-upload/', ChildProductMultiImageUploadView.as_view(),
        name='upload/child-product-multiple-image-upload'),

]
