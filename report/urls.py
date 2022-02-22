from django.conf.urls import include, url

urlpatterns = [
    url(r'^api/v1/', include('report.api.urls')),
]