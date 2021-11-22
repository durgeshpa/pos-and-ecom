from django.conf.urls import url

from . import views
from .views import ARSWareHouseComplete, ARSParentProductAutocomplete

urlpatterns = [
     url(r'^ars-warehouse-autocomplete/$', ARSWareHouseComplete.as_view(), name='ars-warehouse-autocomplete'),
     url(r'^ars-parent-product-autocomplete/$', ARSParentProductAutocomplete.as_view(), name='ars-parent-product-autocomplete'),
]