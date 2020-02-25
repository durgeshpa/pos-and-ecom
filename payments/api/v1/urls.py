from django.conf.urls import include, url
from rest_framework import routers

from .views import (
    ShipmentPaymentView, SendCreditRequestAPI,
    CreditOTPResponseAPI, BharatpeCallbackAPI, OrderPaymentView,
    PaymentImageUploadView,
)


router = routers.DefaultRouter()
router.register(r'shipment-payment', ShipmentPaymentView)
router.register(r'order-payment', OrderPaymentView)


urlpatterns = [
    url('^credit-request/$', SendCreditRequestAPI.as_view()),
    url('^bharatpe-otp-response/$', CreditOTPResponseAPI.as_view()),
    url('^payment-callback/$', BharatpeCallbackAPI.as_view()),
    url('^payment-image-upload/$', PaymentImageUploadView.as_view(), name='payment-screenshot', ),
    url('^payment-image-upload/(?P<pk>\d{0,50})/$', PaymentImageUploadView.as_view()),
]

urlpatterns += router.urls