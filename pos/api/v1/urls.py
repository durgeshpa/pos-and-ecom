from django.conf.urls import include, url
from .views import ProductDetail, RetailerProductsList, EanSearch, GramProductsList, CartCentral

urlpatterns = [
    url('^search/gram-ean/$', EanSearch.as_view()),
    url('^gram-product-detail/(?P<pk>\d+)/$', ProductDetail.as_view()),
    url('^search/retailer-product/$', RetailerProductsList.as_view()),
    url('^search/gram-product/$', GramProductsList.as_view()),
    url('^cart/$', CartCentral.as_view())
]
