from django.conf.urls import include, url
from django.contrib import admin
from banner import views
from . import views
from .views import BrandAutocomplete,CategoryAutocomplete,ProductAutocomplete,BannerShopAutocomplete, SubCategoryAutocomplete, SubBrandAutocomplete, BannerDataAutocomplete

urlpatterns = [

url(r'^api/', include('banner.api.urls')),
url(r'^banner-brand-autocomplete/$',
    BrandAutocomplete.as_view(),
    name='banner-brand-autocomplete', ),
url(r'^banner-sub-brand-autocomplete/$',
    SubBrandAutocomplete.as_view(),
    name='banner-sub-brand-autocomplete', ),
url(r'^category-autocomplete/$',
    CategoryAutocomplete.as_view(),
    name='category-autocomplete', ),
url(r'^sub-category-autocomplete/$',
    SubCategoryAutocomplete.as_view(),
    name='sub-category-autocomplete', ),
url(r'^banner-product-autocomplete/$',
    ProductAutocomplete.as_view(),
    name='banner-product-autocomplete', ),
url(r'^banner-shop-autocomplete/$', BannerShopAutocomplete.as_view(), name='banner-shop-autocomplete',),
url(r'^banner-data-autocomplete/$', BannerDataAutocomplete.as_view(), name='banner-data-autocomplete',),
]
