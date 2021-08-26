from django.conf.urls import include, url
from .views import test

urlpatterns = [
    url(r'^api/', include('ecom.api.urls')),
    url(r'^test/', test)
]
