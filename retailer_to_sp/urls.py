from django.conf.urls import include, url
from django.contrib import admin

from .views import ReturnProductAutocomplete, DownloadCreditNote

urlpatterns = [
    url(r'^api/', include('retailer_to_sp.api.urls')),
    url(r'^return-product-autocomplete/$',
        ReturnProductAutocomplete.as_view(),
        name='return-product-autocomplete', ),
    url('^download-credit-note/(?P<pk>\d+)/note/$',
        DownloadCreditNote.as_view(),
        name='download_credit_note'),
    ]
