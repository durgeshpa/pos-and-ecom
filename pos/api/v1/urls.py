from django.conf.urls import url

from .views import PosProductView, CouponOfferCreation

urlpatterns = [
    url(r'^catalogue-product/', PosProductView.as_view(), name='catalogue-product'),
    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),
]
