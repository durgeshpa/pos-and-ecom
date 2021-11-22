from django.conf.urls import include, url

urlpatterns = [
    url(r'^v1/', include('audit.api.v1.urls')),
]