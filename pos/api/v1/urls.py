from django.conf.urls import include, url
from .views import ProductDetail

urlpatterns = [
    url('^product-detail/(?P<pk>\d+)/$', ProductDetail.as_view()),
]
