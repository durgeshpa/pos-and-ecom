from django.conf.urls import url
from django.urls import path

from . import views
from .filters import AssignedUserFilter, WareHouseComplete

urlpatterns = [
     url(r'^warehouse-autocomplete/$', WareHouseComplete.as_view(), name='warehouse-autocomplete'),
     url(r'^assigned-user-autocomplete/$', AssignedUserFilter.as_view(), name='assigned-user-autocomplete'),
     url(r'^warehouse_transaction/$', views.WarehouseInventoryTransactionViewSet.as_view(), name="warehouse-transaction"),
     url(r'^bin_transactions/$', views.BinInventoryTransactionViewSet.as_view(), name="bin-transaction"),
     url(r'^bin_inventory/$', views.BinInventoryViewSet.as_view(), name="bin-inventory"),
     url(r'^warehouse_inventory/$', views.WarehouseInventoryViewSet.as_view(), name="warehouse-inventory"),
]