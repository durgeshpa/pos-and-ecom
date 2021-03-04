from django.conf.urls import include, url
from pos.views import CatalogueProductCreation, OfferCreation

urlpatterns = [
    url(r'^catalogue_product/', CatalogueProductCreation.as_view(), name='catalogue_product'),
    url(r'^catalogue_offers/', OfferCreation.as_view(), name='catalogue_offers'),
     url(r'^api/', include('pos.api.urls')),
]
