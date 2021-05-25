from django.conf.urls import url
from django.urls import path, include

from . import views
from .views import WareHouseComplete, ParentProductAutocomplete

urlpatterns = [
     url(r'^warehouse-autocomplete/$', WareHouseComplete.as_view(), name='warehouse-autocomplete'),
     url(r'^parent-product-autocomplete/$', ParentProductAutocomplete.as_view(), name='parent-product-autocomplete'),
     url(r'^daily_average_sales/$', views.daily_average_sales, name='daily_average_sales'),
     url(r'^create_po/$', views.create_ars_po, name='create_po'),
     url(r'^start_ars/$', views.start_ars, name='start_ars'),

]