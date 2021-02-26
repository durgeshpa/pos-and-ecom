from django.conf.urls import url
from django.urls import path, include

from . import views

urlpatterns = [
    url(r'^api/', include('retailer_inventive.api.v1.urls'))
]