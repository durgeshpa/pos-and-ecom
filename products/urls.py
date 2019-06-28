from django.conf.urls import include, url
from django.contrib import admin

from .views import ProductCategoryAutocomplete

urlpatterns = [
url(r'^category-autocomplete/$', ProductCategoryAutocomplete.as_view(), name='category-autocomplete',),
]
