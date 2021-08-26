from django.conf.urls import include, url

urlpatterns = [
    url(r'^api/', include('ecom.api.urls')),
]
