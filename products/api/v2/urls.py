from django.conf.urls import url
from .views import BulkUploadProductAttributes

urlpatterns = [
    url(r'^bulk-upload-master-data/', BulkUploadProductAttributes.as_view(), name='bulk-upload-master-data'),

]
