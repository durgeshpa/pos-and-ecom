from django.conf.urls import include, url
from django.contrib import admin

from .views import (ProductCategoryAutocomplete, FetchDefaultChildDdetails,
                    ParentProductAutocomplete, FetchProductDdetails,
                    ProductAutocomplete, FetchAllParentCategories,
                    FetchAllProductBrands, SourceProductAutocomplete)

urlpatterns = [
    url(r'^category-autocomplete/$', ProductCategoryAutocomplete.as_view(), name='category-autocomplete',),
    url(r'^fetch-default-child-details/$', FetchDefaultChildDdetails, name='fetch-default-child-details',),
    url(r'^parent-product-autocomplete/$', ParentProductAutocomplete.as_view(), name='parent-product-autocomplete',),
    url(r'^fetch-product-details/$', FetchProductDdetails, name='fetch-product-details',),
    url(r'^product-autocomplete/$', ProductAutocomplete.as_view(), name='product-autocomplete',),
    url(r'^source-product-autocomplete/$', SourceProductAutocomplete.as_view(), name='source-product-autocomplete',),
    url(r'^fetch-all-parent-categories/$', FetchAllParentCategories, name='fetch-all-parent-categories',),
    url(r'^fetch-all-product-brands/$', FetchAllProductBrands, name='fetch-all-product-brands',),
]
