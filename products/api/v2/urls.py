from django.conf.urls import url
from .views import BulkUploadProductAttributes, BulkDownloadProductAttributes

urlpatterns = [
    url(r'^upload/bulk-upload-master-data/', BulkUploadProductAttributes.as_view(),
        name='upload/bulk-upload-master-data'),
    url(r'^download/bulk-download-master-data/', BulkDownloadProductAttributes.as_view(),
        name='download/bulk-download-master-data'),

]
