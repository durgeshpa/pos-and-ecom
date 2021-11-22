from django.conf.urls import include, url
from franchise.filters import FranchiseShopAutocomplete
from franchise.views import StockCsvConvert, DownloadFranchiseStockCSV, AddSales

urlpatterns = [
    url(r'^franchise-shop-autocomplete/$', FranchiseShopAutocomplete.as_view(), name='franchise-shop-autocomplete'),
    url(r'^stockcsvconvert/$', StockCsvConvert.as_view(), name='stockcsvconvert'),
    url(r'^download/stockconvert/csv/$', DownloadFranchiseStockCSV.as_view(), name="download-inventory-csv-sample"),
    url(r'^create-sales/$', AddSales.as_view(), name='create-sales')
]
