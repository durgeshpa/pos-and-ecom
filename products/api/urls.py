from django.conf.urls import url, include

# url pattern
urlpatterns = [
    url(r'^v1/', include('products.api.v1.urls')),
    url(r'^v2/', include('products.api.v2.urls')),
]
