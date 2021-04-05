from django.conf.urls import url

from .views import CatalogueProductCreation, CouponOfferCreation

urlpatterns = [
    url(r'^catalogue-product/', CatalogueProductCreation.as_view(), name='catalogue-product'),
    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),
]
