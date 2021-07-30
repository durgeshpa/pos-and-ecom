from django.conf.urls import url, include

from .filters import MlmUserAutocomplete

urlpatterns = [
    url(r'^mlm-user-autocomplete/$', MlmUserAutocomplete.as_view(), name='mlm-user-autocomplete'),
    url(r'^api/', include('marketing.api.urls')),
]
