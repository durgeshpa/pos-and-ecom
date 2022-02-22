from django.conf.urls import url,include

urlpatterns = [
    url(r'^v1/', include('shops.api.v1.urls')),
    url(r'^v2/', include('shops.api.v2.urls')),
]
