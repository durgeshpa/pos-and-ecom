from django.conf.urls import include, url

urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^v1/', include('wms.api.v1.urls')),
]