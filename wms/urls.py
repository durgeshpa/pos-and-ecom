from django.conf.urls import include, url

import views
import wms
from .api.v2.views import ProductSkuAutocomplete
from .views import bins_upload, CreatePickList, StockMovementCsvSample, StockMovementCsvView, DownloadBinCSV, MergeBarcode
from .filters import WareHouseComplete, InventoryTypeFilter, InventoryStateFilter, PutawayUserFilter



urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^api/', include('wms.api.urls')),
    url(r'^create-pick-list/(?P<pk>\d+)/picklist/$', CreatePickList.as_view(), name='create-picklist'),
    url(r'^create-pick-list/(?P<pk>\d+)/picklist/(?P<type>\d+)$', CreatePickList.as_view(), name='create-picklist'),
    url(r'^download/inventory_csv/sample/$', StockMovementCsvSample.as_view(), name="download-inventory-csv-sample"),
    url(r'^upload/csv/$', StockMovementCsvView.as_view(), name="inventory-upload-csv"),
    url(r'^download/bin/csv/$', DownloadBinCSV.as_view(), name="download-inventory-csv-sample"),
    url(r'^warehouse-autocomplete/$', WareHouseComplete.as_view(), name='warehouse-autocomplete'),
    url(r'^inventory-type-autocomplete/$', InventoryTypeFilter.as_view(), name='inventory-type-autocomplete'),
    url(r'^inventory-state-autocomplete/$', InventoryStateFilter.as_view(), name='inventory-state-autocomplete'),
    url(r'^putaway-user-autocomplete/$', PutawayUserFilter.as_view(), name='putaway-user-autocomplete'),
    url(r'^merged_barcode/(?P<id>[\w-]+)/$', MergeBarcode.as_view(), name='merged_barcodes'),
    url(r'^archive/$', wms.views.archive_inventory_cron, name='archive'),
    url(r'^populate-expiry-date/$', wms.views.populate_expiry_date, name="populate-expiry-date"),
    url(r'^move-expired-inventory/$', wms.views.move_expired_inventory_manual, name="move-expired-inventory"),
    url(r'^rectify-batch-ids/$', wms.views.rectify_batch_ids, name="rectify-batch-ids"),
    url(r'^audit_ordered_data/$', wms.views.audit_ordered_data, name='audit_ordered_data'),
    url(r'^auto_report_for_expired_product/$', wms.views.auto_report_for_expired_product, name='expired_product'),
    # url(r'^test/$', wms.views.test, name='test'),
    url(r'^product-sku-autocomplete/$', ProductSkuAutocomplete.as_view(), name='product-sku-autocomplete',),


]