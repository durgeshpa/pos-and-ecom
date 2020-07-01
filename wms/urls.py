from django.conf.urls import include, url

from .views import bins_upload, CreatePickList, StockMovementCsvSample, StockMovementCsvView

urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^api/', include('wms.api.urls')),
    url(r'^create-pick-list/(?P<pk>\d+)/picklist/$', CreatePickList.as_view(), name='create-picklist'),
    url(r'^download/inventory_csv/sample/$', StockMovementCsvSample.as_view(), name="download-inventory-csv-sample"),
    url(r'^upload/csv/$', StockMovementCsvView.as_view(), name="inventory-upload-csv"),
]