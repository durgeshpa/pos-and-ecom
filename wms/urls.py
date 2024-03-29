from django.conf.urls import include, url


import wms
from .api.v2.views import ProductSkuAutocomplete
from .views import bins_upload, CreatePickList, StockMovementCsvSample, StockMovementCsvView, DownloadBinCSV, \
    MergeBarcode, QCAreaBarcodeGenerator, PutawayUserAutcomplete, PickerUserAutcomplete, PickerUsersCompleteAutcomplete, \
    PutawayUsersCompleteAutcomplete, CrateBarcodeGenerator
from .filters import WarehousesAutocomplete, InventoryTypeFilter, InventoryStateFilter, PutawayUserFilter, \
    SupervisorFilter, CoordinatorFilter, ParentProductFilter, ZoneFilter, CoordinatorAvailableFilter, \
    PutawayUserAutcomplete, PickerUserAutcomplete, UserFilter, QCAreaFilter, CrateFilter, QCDeskFilter, \
    QCExecutiveFilter, QCAreaNonMappedFilter, QCExecutiveNonMappedFilter, AlternateDeskFilter

urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^api/', include('wms.api.urls')),
    url(r'^create-pick-list/(?P<pk>\d+)/picklist/$', CreatePickList.as_view(), name='create-picklist'),
    url(r'^create-pick-list/(?P<pk>\d+)/picklist/(?P<type>\d+)$', CreatePickList.as_view(), name='create-picklist'),
    url(r'^generate-pick-list/(?P<pk>\d+)/(?P<zone>\d+)/$', CreatePickList.as_view(), name='generate-picklist'),
    url(r'^generate-pick-list/(?P<pk>\d+)/(?P<zone>\d+)/(?P<type>\d+)$', CreatePickList.as_view(),
        name='generate-picklist'),
    url(r'^download/inventory_csv/sample/$', StockMovementCsvSample.as_view(), name="download-inventory-csv-sample"),
    url(r'^upload/csv/$', StockMovementCsvView.as_view(), name="inventory-upload-csv"),
    url(r'^download/bin/csv/$', DownloadBinCSV.as_view(), name="download-inventory-csv-sample"),
    url(r'^warehouses-autocomplete/$', WarehousesAutocomplete.as_view(), name='warehouses-autocomplete'),
    url(r'^inventory-type-autocomplete/$', InventoryTypeFilter.as_view(), name='inventory-type-autocomplete'),
    url(r'^inventory-state-autocomplete/$', InventoryStateFilter.as_view(), name='inventory-state-autocomplete'),
    url(r'^putaway-user-autocomplete/$', PutawayUserFilter.as_view(), name='putaway-user-autocomplete'),
    url(r'^putaway-users-autocomplete/$', PutawayUserAutcomplete.as_view(), name='putaway-users-autocomplete'),
    url(r'^all-putaway-users-autocomplete/$', PutawayUsersCompleteAutcomplete.as_view(),
        name='all-putaway-users-autocomplete'),
    url(r'^picker-users-autocomplete/$', PickerUserAutcomplete.as_view(), name='picker-users-autocomplete'),
    url(r'^all-picker-users-autocomplete/$', PickerUsersCompleteAutcomplete.as_view(),
        name='all-picker-users-autocomplete'),
    url(r'^supervisor-autocomplete/$', SupervisorFilter.as_view(), name='supervisor-autocomplete'),
    url(r'^coordinator-autocomplete/$', CoordinatorFilter.as_view(), name='coordinator-autocomplete'),
    url(r'^coordinator-available-autocomplete/$', CoordinatorAvailableFilter.as_view(),
        name='coordinator-available-autocomplete'),
    url(r'^parent-product-filter/$', ParentProductFilter.as_view(), name='parent-product-filter'),
    url(r'^zone-autocomplete/$', ZoneFilter.as_view(), name='zone-autocomplete'),
    url(r'^crate-autocomplete/$', CrateFilter.as_view(), name='crate-autocomplete'),
    url(r'^qc-area-autocomplete/$', QCAreaFilter.as_view(), name='qc-area-autocomplete'),
    url(r'^non-mapped-qc-area-autocomplete/$', QCAreaNonMappedFilter.as_view(), name='non-mapped-qc-area-autocomplete'),
    url(r'^qc-desk-autocomplete/$', QCDeskFilter.as_view(), name='qc-desk-autocomplete'),
    url(r'^qc-executive-autocomplete/$', QCExecutiveFilter.as_view(), name='qc-executive-autocomplete'),
    url(r'^non-mapped-qc-executive-autocomplete/$', QCExecutiveNonMappedFilter.as_view(),
        name='non-mapped-qc-executive-autocomplete'),
    url(r'^alternate-desk-autocomplete/$', AlternateDeskFilter.as_view(), name='alternate-desk-autocomplete'),
    url(r'^users-autocomplete/$', UserFilter.as_view(), name='users-autocomplete'),
    url(r'^merged_barcode/(?P<id>[\w-]+)/$', MergeBarcode.as_view(), name='merged_barcodes'),
    url(r'^archive/$', wms.views.archive_inventory_cron, name='archive'),
    url(r'^populate-expiry-date/$', wms.views.populate_expiry_date, name="populate-expiry-date"),
    url(r'^move-expired-inventory/$', wms.views.move_expired_inventory_manual, name="move-expired-inventory"),
    url(r'^rectify-batch-ids/$', wms.views.rectify_batch_ids, name="rectify-batch-ids"),
    url(r'^audit_ordered_data/$', wms.views.audit_ordered_data, name='audit_ordered_data'),
    url(r'^auto_report_for_expired_product/$', wms.views.auto_report_for_expired_product, name='expired_product'),
    url(r'^product-sku-autocomplete/$', ProductSkuAutocomplete.as_view(), name='product-sku-autocomplete'),
    url(r'^qc_barcode/(?P<id>[\w-]+)/$', QCAreaBarcodeGenerator.as_view(), name='qc_barcode'),
    url(r'^crate-barcode/(?P<id>[\w-]+)/$', CrateBarcodeGenerator.as_view(), name='crate_barcode'),
]