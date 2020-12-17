from django.conf.urls import url
from django.urls import path, include

from . import views
from .filters import AssignedUserFilter, WareHouseComplete, SKUComplete, BinComplete, AuditorFilter, \
 AssignedUserComplete

urlpatterns = [
    url(r'^api/', include('audit.api.urls')),
     url(r'^warehouse-autocomplete/$', WareHouseComplete.as_view(), name='warehouse-autocomplete'),
     url(r'^assigned-user-filter/$', AssignedUserFilter.as_view(), name='assigned-user-filter'),
     url(r'^assigned-user-autocomplete/$', AssignedUserComplete.as_view(), name='assigned-user-autocomplete'),
     url(r'^sku-autocomplete/$', SKUComplete.as_view(), name='sku-autocomplete'),
     url(r'^bin-autocomplete/$', BinComplete.as_view(), name='bin-autocomplete'),
     url(r'^auditor-autocomplete/$', AuditorFilter.as_view(), name='auditor-autocomplete'),
     url(r'^warehouse_transactions/$', views.WarehouseInventoryTransactionView.as_view(), name="warehouse-transaction"),
     url(r'^warehouse_inventory/$', views.WarehouseInventoryView.as_view(), name="warehouse-inventory"),
     url(r'^warehouse_history/$', views.WarehouseInventoryHistoryView.as_view(), name="warehouse-historic"),
     url(r'^bin_transactions/$', views.BinInventoryTransactionView.as_view(), name="bin-transaction"),
     url(r'^bin_inventory/$', views.BinInventoryView.as_view(), name="bin-inventory"),
     url(r'^bin_history/$', views.BinInventoryHistoryView.as_view(), name="bin-historic"),
     url(r'^pickup-blocked-inventory/$', views.PickupBlockedQuantityView.as_view(), name="pickup-blocked"),
     url(r'^run-audit/$', views.run_audit_manually, name="run-audit"),

     
]