from django.conf.urls import include, url
from django.contrib import admin
from banner import views
from . import views
from .views import BrandAutocomplete,CategoryAutocomplete,ProductAutocomplete

urlpatterns = [

url(r'^api/', include('banner.api.urls')),
url(r'^banner-brand-autocomplete/$',
    BrandAutocomplete.as_view(),
    name='banner-brand-autocomplete', ),
url(r'^category-autocomplete/$',
    CategoryAutocomplete.as_view(),
    name='category-autocomplete', ),
url(r'^banner-product-autocomplete/$',
    ProductAutocomplete.as_view(),
    name='banner-product-autocomplete', ),
]
