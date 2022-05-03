from django.conf.urls import url,include

urlpatterns = [
    url(r'^v1/', include('pos.api.v1.urls')),
    url(r'^v2/', include('pos.api.v2.urls')),
]
