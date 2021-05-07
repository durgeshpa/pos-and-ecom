from django.conf.urls import url
from .views import ParentProductView

urlpatterns = [
    url(r'^parent-product/', ParentProductView.as_view(), name='parent-product'),
]
