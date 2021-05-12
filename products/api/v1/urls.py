from django.conf.urls import url
from .views import ParentProductView, ParentProductBulkUploadView

urlpatterns = [
    url(r'^parent-product/', ParentProductView.as_view(), name='parent-product'),
    url(r'^parent-bulk-product/', ParentProductBulkUploadView.as_view(), name='parent-bulk-product'),
]
