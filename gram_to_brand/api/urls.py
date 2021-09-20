from django.conf.urls import include, url

urlpatterns = [
    url(r'^v1/', include('gram_to_brand.api.v1.urls')),
]