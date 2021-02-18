from django.conf.urls import include, url
from .views import ProductDetail, RetailerProductsList

urlpatterns = [
    url('^product-detail/(?P<pk>\d+)/$', ProductDetail.as_view()),
    url('^search/retailer-product/$', RetailerProductsList.as_view())
]
