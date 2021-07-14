from django.conf.urls import url
from .views import BulkCreateUpdateAttributesView, BulkDownloadProductAttributes, ParentProductMultiImageUploadView, \
    ChildProductMultiImageUploadView, BulkChoiseView
urlpatterns = [

    url(r'^upload/bulk-upload-master-data/', BulkCreateUpdateAttributesView.as_view(),
        name='upload/bulk-upload-master-data'),
    url(r'^download/bulk-download-master-data/', BulkDownloadProductAttributes.as_view(),
        name='download/bulk-download-master-data'),
    url(r'^upload/parent-product-multiple-image-upload/', ParentProductMultiImageUploadView.as_view(),
        name='upload/parent-product-multiple-image-upload'),
    url(r'^upload/child-product-multiple-image-upload/', ChildProductMultiImageUploadView.as_view(),
        name='upload/child-product-multiple-image-upload'),
    url(r'^upload_type/bulk-choice/', BulkChoiseView.as_view(),
        name='upload_type/bulk-choice'),
]
