from django.conf.urls import url, include

urlpatterns = [
    url(r'^v1/', include('rest_auth.api.v1.urls')),
]
