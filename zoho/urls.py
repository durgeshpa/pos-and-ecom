from django.conf.urls import include, url
from .filters import ZohoUserFilter

urlpatterns = [
    url(r'^zoho-users-autocomplete/$', ZohoUserFilter.as_view(), name='zoho-users-autocomplete'),
    ]