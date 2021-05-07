from django.conf.urls import url, include

urlpatterns = [
    url(r'^v1/', include('products.api.v1.urls')),
]
