from django.conf.urls import include, url

from .views import ProductDetail, RetailerProductsList, EanSearch, GramProductsList, CartCentral, \
    OrderCentral, CartCheckout, OrderListCentral

urlpatterns = [
    url('^search/ean/$', EanSearch.as_view()),
    url('^gram-product-detail/(?P<pk>\d+)/$', ProductDetail.as_view()),
    url('^search/retailer-product/$', RetailerProductsList.as_view()),
    url('^search/gram-product/$', GramProductsList.as_view()),
    url('^cart/$', CartCentral.as_view()),
    url('^cart/(?P<pk>\d+)/$', CartCentral.as_view()),
    url('^cart/checkout/$', CartCheckout.as_view()),
    url('^order/$', OrderCentral.as_view()),
    url('^order-list/$', OrderListCentral.as_view())
]
