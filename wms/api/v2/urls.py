from django.conf.urls import include, url
from .views import InOutLedger, InOutLedgerCSV, BinInventoryDataView, InventoryTypeView

urlpatterns = [
    url(r'^in-out-ledger/$', InOutLedger.as_view(), name='in-out-ledger'),
    url('download/in-out-ledger/', InOutLedgerCSV.as_view(), name='download-in-out-ledger'),
    url('bin-inventory/', BinInventoryDataView.as_view(), name='bin-inventory'),
    url('inventory-type/', InventoryTypeView.as_view(), name='inventory-type'),
]