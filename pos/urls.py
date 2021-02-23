from django.conf.urls import include, url
from pos.views import CatalogueProductCreation

urlpatterns = [
    url(r'^catalogue_product/', CatalogueProductCreation.as_view(), name='catalogue_product'),
     url(r'^api/', include('pos.api.urls')),
]
