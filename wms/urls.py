from django.conf.urls import include, url

from .views import bins_upload, CreatePickList

urlpatterns = [
    # url(r'^upload-csv/$', bins_upload, name="bins_upload"),
    url(r'^api/', include('wms.api.urls')),
    url(r'^create-pick-list/$', CreatePickList.as_view(), name='create-picklist'),
]