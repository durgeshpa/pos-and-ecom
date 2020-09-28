from django.conf.urls import include, url
from django.contrib import admin

from .views import ProductCategoryAutocomplete, FetchDefaultChildDdetails

urlpatterns = [
url(r'^category-autocomplete/$', ProductCategoryAutocomplete.as_view(), name='category-autocomplete',),
url(r'^fetch-default-child-details/$', FetchDefaultChildDdetails, name='fetch-default-child-details',),
]
