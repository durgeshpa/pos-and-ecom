from django.conf.urls import include, url
from rest_framework import routers

from .views import (ShipmentPaymentView, CashPaymentView)

router = routers.DefaultRouter()
router.register(r'shipment-payment', ShipmentPaymentView)

urlpatterns = [
]

urlpatterns += router.urls