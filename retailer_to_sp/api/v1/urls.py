from django.conf.urls import include, url
from .views import ProductsList, GramGRNProductsList

urlpatterns = [
    url('^search/(?P<product_name>.+)/$', ProductsList.as_view()),
    url('^GRN/search/$', GramGRNProductsList.as_view()),

]
