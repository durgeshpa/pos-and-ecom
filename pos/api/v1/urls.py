from django.conf.urls import url

from .views import OrderListCentral, \
    OrderedItemCentralDashBoard, OrderReturns, OrderReturnsCheckout, OrderReturnComplete,\
    CatalogueProductCreation, CouponOfferCreation

urlpatterns = [
    url(r'^catalogue-product/', CatalogueProductCreation.as_view(), name='catalogue-product'),
    url('^order-list/$', OrderListCentral.as_view()),
    url('^order-dashboard/$', OrderedItemCentralDashBoard.as_view()),
    url('^return/$', OrderReturns.as_view()),
    url('^return/checkout/$', OrderReturnsCheckout.as_view()),
    url('^return/complete/$', OrderReturnComplete.as_view()),
    url(r'^offers/', CouponOfferCreation.as_view(), name='offers'),
]
