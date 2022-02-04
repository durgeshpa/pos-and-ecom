from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path

from .views import *

urlpatterns = [
    url(r'^api/', include('payments.api.urls')),

    url(r'^order-payment-autocomplete/$',
    OrderPaymentAutocomplete.as_view(),
    name='order-payment-autocomplete', ),

    url(r'^order-autocomplete/$',
    OrderAutocomplete.as_view(),
    name='order-autocomplete', ),

    path('order-payment-amount/<order_payment>/',
        GetOrderPaymentAmount,
        name='order-payment-amount', ),
    ]
