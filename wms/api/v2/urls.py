from django.conf.urls import include, url

from .views import InOutLedger, InOutLedgerCSV, ZoneCrudView, ZoneSupervisorsView, ZoneCoordinatorsView, \
    ZonePutawaysView, WarehouseAssortmentCrudView, WarehouseAssortmentExportAsCSVView, BinTypeView, \
    WarehouseAssortmentSampleCSV, WarehouseAssortmentUploadView, BinCrudView, BinExportAsCSVView, \
    BinExportBarcodeView, ZonePutawayAssignmentsView, CancelPutawayCrudView, UpdateZoneForCancelledPutawayView, \
    GroupedByGRNPutawaysView, PutawayItemsCrudView, AssignPutawayUserByGRNAndZoneView, PutawayUsersListView, \
    ZoneFilterView, PutawayStatusListView, UserDetailsPostLoginView, BinInventoryDataView, BinFilterView,\
    PerformPutawayView, PutawayRemarkView

urlpatterns = [
    url(r'^in-out-ledger/$', InOutLedger.as_view(), name='in-out-ledger'),
    url('download/in-out-ledger/', InOutLedgerCSV.as_view(), name='download-in-out-ledger'),
    url('zones/', ZoneCrudView.as_view(), name='zones'),
    url('zone-putaway-assignments/', ZonePutawayAssignmentsView.as_view(), name='zone-putaway-assignments'),
    url('zone-supervisors/', ZoneSupervisorsView.as_view(), name='zone-supervisors'),
    url('zone-coordinators/', ZoneCoordinatorsView.as_view(), name='zone-coordinators'),
    url('zone-putaway-users/', ZonePutawaysView.as_view(), name='zone-putaway-users/'),
    url('download/whc-assortment-sample/', WarehouseAssortmentSampleCSV.as_view(), name='download-whc-asrtmnt-sample'),
    url('upload/whc-assortments/', WarehouseAssortmentUploadView.as_view(), name='upload-whc-assortments'),
    url('export-csv-whc-assortments/', WarehouseAssortmentExportAsCSVView.as_view(), name='export-csv-whc-assortments'),
    url('whc-assortments/', WarehouseAssortmentCrudView.as_view(), name='whc-assortments'),
    url('bin-types/', BinTypeView.as_view(), name='bin-types'),
    url('export-csv-bins/', BinExportAsCSVView.as_view(), name='export-csv-bins'),
    url('export-bins-barcode/', BinExportBarcodeView.as_view(), name='export-bins-barcode'),
    url('bins/', BinCrudView.as_view(), name='bins'),
    url('cancel-putaway/', CancelPutawayCrudView.as_view(), name='cancel-putaway'),
    url('assign-zone-cancelled-putaway/', UpdateZoneForCancelledPutawayView.as_view(),
        name='assign-zone-cancelled-putaway'),
    url('assign-putaway-user-by-grn-zone/', AssignPutawayUserByGRNAndZoneView.as_view(),
        name='assign-putaway-user-by-grn-zone'),
    url('grouped-putaways/', GroupedByGRNPutawaysView.as_view(), name='grouped-putaways'),
    url('putaway-items/', PutawayItemsCrudView.as_view(), name='putaway-items'),
    url('putaway-users-under-zone/', PutawayUsersListView.as_view(), name='putaway-users-under-zone'),
    url('zone-list/', ZoneFilterView.as_view(), name='zone-list'),
    url('putaway-status-list/', PutawayStatusListView.as_view(), name='putaway-status-list'),
    url('user-details/', UserDetailsPostLoginView.as_view(), name='user-details'),
    url('bin-inventory/', BinInventoryDataView.as_view(), name='bin-inventory'),
    url('bin-list/', BinFilterView.as_view(), name='bin-list'),
    url('putaway-action/', PerformPutawayView.as_view(), name='putaway-action'),
    url('putaway-remark/', PutawayRemarkView.as_view(), name='putaway-remark'),
]