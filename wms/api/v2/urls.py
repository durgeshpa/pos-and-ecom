from django.conf.urls import include, url
from .views import InOutLedger, InOutLedgerCSV

urlpatterns = [
    url(r'^in-out-ledger/$', InOutLedger.as_view(), name='in-out-ledger'),
    url('download/in-out-ledger/', InOutLedgerCSV.as_view(), name='download-in-out-ledger'),
]