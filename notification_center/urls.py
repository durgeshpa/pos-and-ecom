from django.conf.urls import url,include

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'', include('notification_center.api.urls')),
]
