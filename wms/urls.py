from django.conf.urls import include, url

from .views import bins_upload, CreatePickList, StockMovementCsvSample, StockMovementCsvView, DownloadBinCSV
from .filters import WareHouseComplete, InventoryTypeFilter, InventoryStateFilter

urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^api/', include('wms.api.urls')),
    url(r'^create-pick-list/(?P<pk>\d+)/picklist/$', CreatePickList.as_view(), name='create-picklist'),
    url(r'^download/inventory_csv/sample/$', StockMovementCsvSample.as_view(), name="download-inventory-csv-sample"),
    url(r'^upload/csv/$', StockMovementCsvView.as_view(), name="inventory-upload-csv"),
    url(r'^download/bin/csv/$', DownloadBinCSV.as_view(), name="download-inventory-csv-sample"),
    url(r'^warehouse-autocomplete/$', WareHouseComplete.as_view(), name='warehouse-autocomplete'),
    url(r'^inventory-type-autocomplete/$', InventoryTypeFilter.as_view(), name='inventory-type-autocomplete'),
    url(r'^inventory-state-autocomplete/$', InventoryStateFilter.as_view(), name='inventory-state-autocomplete'),
]