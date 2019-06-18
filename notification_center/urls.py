from django.conf.urls import url,include

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^fcm/', include('fcm.urls')),
    url(r'', include('retailer_to_sp.api.urls')),
]
