from django.conf.urls import include, url
from .views import InOutLedger, InOutLedgerCSV, ZoneCrudView, ZoneSupervisorsView, ZoneCoordinatorsView, \
    ZonePutawaysView, WarehouseAssortmentCrudView, WarehouseAssortmentExportAsCSVView, \
    WarehouseAssortmentSampleCSV, WarehouseAssortmentUploadView

urlpatterns = [
    url(r'^in-out-ledger/$', InOutLedger.as_view(), name='in-out-ledger'),
    url('download/in-out-ledger/', InOutLedgerCSV.as_view(), name='download-in-out-ledger'),
    url('zones/', ZoneCrudView.as_view(), name='zones'),
    url('zone-supervisors/', ZoneSupervisorsView.as_view(), name='zone-supervisors'),
    url('zone-coordinators/', ZoneCoordinatorsView.as_view(), name='zone-coordinators'),
    url('zone-putaway-users/', ZonePutawaysView.as_view(), name='zone-putaway-users/'),
    url('download/whc-assortment-sample/', WarehouseAssortmentSampleCSV.as_view(), name='download-whc-asrtmnt-sample'),
    url('upload/whc-assortments/', WarehouseAssortmentUploadView.as_view(), name='upload-whc-assortments'),
    url('export-csv-whc-assortments/', WarehouseAssortmentExportAsCSVView.as_view(), name='export-csv-whc-assortments'),
    url('whc-assortments/', WarehouseAssortmentCrudView.as_view(), name='whc-assortments'),
]