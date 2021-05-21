from django.conf.urls import url
from django.urls import path, include

from . import views
from .views import WareHouseComplete, ParentProductAutocomplete

urlpatterns = [
     url(r'^warehouse-autocomplete/$', WareHouseComplete.as_view(), name='warehouse-autocomplete'),
     url(r'^parent-product-autocomplete/$', ParentProductAutocomplete.as_view(), name='parent-product-autocomplete'),
     
]