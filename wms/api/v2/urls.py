from django.conf.urls import include, url

from .views import InOutLedger, InOutLedgerCSV, ZoneCrudView, ZoneSupervisorsView, ZoneCoordinatorsView, \
    ZonePutawaysView, WarehouseAssortmentCrudView, WarehouseAssortmentExportAsCSVView, BinTypeView, \
    WarehouseAssortmentSampleCSV, WarehouseAssortmentUploadView, BinCrudView, BinExportAsCSVView, \
    BinExportBarcodeView, ZonePutawayAssignmentsView, CancelPutawayCrudView, UpdateZoneForCancelledPutawayView, \
    GroupedByGRNPutawaysView, PutawayItemsCrudView, AssignPutawayUserByGRNAndZoneView, PutawayUsersListView, \
    ZoneFilterView, PutawayStatusListView, UserDetailsPostLoginView, PerformPutawayView, PutawayRemarkView, \
    POSummaryView, PutawaySummaryView, ZoneWiseSummaryView, PutawayTypeListView, BinInventoryDataView, BinFilterView, \
    PickupEntryCreationView, UpdateQCAreaView, PickerUsersListView, ZonePickersView, PickerUserReAssignmentView, \
    OrderStatusSummaryView, PickerDashboardStatusSummaryView, ZoneWisePickerSummaryView, QCDeskCrudView, \
    PutawayTypeIDSearchView, QCAreaCrudView, QCAreaTypeListView, QCExecutivesView, QCDeskQCAreaAssignmentMappingView, \
    QCDeskHelperDashboardView, QCJobsDashboardView, PendingQCJobsView, PickingTypeListView, QCDeskFilterView, CrateView

urlpatterns = [
    url(r'^in-out-ledger/$', InOutLedger.as_view(), name='in-out-ledger'),
    url('download/in-out-ledger/', InOutLedgerCSV.as_view(), name='download-in-out-ledger'),
    url('zones/', ZoneCrudView.as_view(), name='zones'),
    url('zone-putaway-assignments/', ZonePutawayAssignmentsView.as_view(), name='zone-putaway-assignments'),
    url('zone-supervisors/', ZoneSupervisorsView.as_view(), name='zone-supervisors'),
    url('zone-coordinators/', ZoneCoordinatorsView.as_view(), name='zone-coordinators'),
    url('zone-putaway-users/', ZonePutawaysView.as_view(), name='zone-putaway-users/'),
    url('zone-picker-users/', ZonePickersView.as_view(), name='zone-picker-users/'),
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
    url('picker-users-under-zone/', PickerUsersListView.as_view(), name='picker-users-under-zone'),
    url('zone-list/', ZoneFilterView.as_view(), name='zone-list'),
    url('putaway-status-list/', PutawayStatusListView.as_view(), name='putaway-status-list'),
    url('user-details/', UserDetailsPostLoginView.as_view(), name='user-details'),
    url('bin-inventory/', BinInventoryDataView.as_view(), name='bin-inventory'),
    url('bin-list/', BinFilterView.as_view(), name='bin-list'),
    url('putaway-action/', PerformPutawayView.as_view(), name='putaway-action'),
    url('putaway-remark/', PutawayRemarkView.as_view(), name='putaway-remark'),
    url('temp/', PickupEntryCreationView.as_view(), name='temp'),
    url('move-to-qc/', UpdateQCAreaView.as_view(), name='move-to-qc'),
    url('po-summary/', POSummaryView.as_view(), name='po-summary'),
    url('zone-wise-summary/', ZoneWiseSummaryView.as_view(), name='zone-wise-summary'),
    url('putaway-summary/', PutawaySummaryView.as_view(), name='putaway-summary'),
    url('putaway-type-list/', PutawayTypeListView.as_view(), name='putaway-type-list'),
    url('^picker-user-reassignment/$', PickerUserReAssignmentView.as_view(), name='picker-user-reassignment'),
    url('order-status-summary/', OrderStatusSummaryView.as_view(), name='order-status-summary'),
    url('picker-status-summary/', PickerDashboardStatusSummaryView.as_view(), name='picker-status-summary'),
    url('zone-wise-picker-summary/', ZoneWisePickerSummaryView.as_view(), name='zone-wise-picker-summary'),
    url('putaway-type-search/', PutawayTypeIDSearchView.as_view(), name='putaway-type-search'),
    url('qc-executive/', QCExecutivesView.as_view(), name='qc-executive'),
    url('qc-desk/', QCDeskCrudView.as_view(), name='qc-desk'),
    url('qc-area-types/', QCAreaTypeListView.as_view(), name='qc-area-types'),
    url('qc-area/', QCAreaCrudView.as_view(), name='qc-area'),
    url('qc-desk-to-area-mapping/', QCDeskQCAreaAssignmentMappingView.as_view(), name='qc-desk-to-area-mapping'),
    url('qc-desk-helper-dashboard/', QCDeskHelperDashboardView.as_view(), name='qc-desk-helper-dashboard'),
    url('qc-jobs-dashboard/', QCJobsDashboardView.as_view(), name='qc-jobs-dashboard'),
    url('pending-qc-jobs/', PendingQCJobsView.as_view(), name='pending-qc-jobs'),
    url('picking-type-list/', PickingTypeListView.as_view(), name='picking-type-list'),
    url('qc-desk-list/', QCDeskFilterView.as_view(), name='qc-desk-list'),
    url('crates/', CrateView.as_view())
]
