from django.conf.urls import url,include

urlpatterns = [
    url(r'^v1/', include('notification_center.api.v1.urls')),
]
