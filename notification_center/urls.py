from django.conf.urls import url,include

from .views import (
	SellerAutocomplete,
)

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'', include('notification_center.api.urls')),
    url(r'^seller-autocomplete1/$',
        SellerAutocomplete.as_view(),
        name='seller-autocomplete1', ),
]
