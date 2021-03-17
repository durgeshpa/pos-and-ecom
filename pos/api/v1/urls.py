from django.conf.urls import include, url

from .views import ProductDetail, SearchView, CartCentral, OrderCentral, CartCheckout, OrderListCentral

urlpatterns = [
    url('^gram-product-detail/(?P<pk>\d+)/$', ProductDetail.as_view()),
    url('^search/$', SearchView.as_view()),
    url('^cart/$', CartCentral.as_view()),
    url('^cart/(?P<pk>\d+)/$', CartCentral.as_view()),
    url('^cart/checkout/$', CartCheckout.as_view()),
    url('^order/$', OrderCentral.as_view()),
    url('^order-list/$', OrderListCentral.as_view())
]
