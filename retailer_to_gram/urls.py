from django.conf.urls import include, url
from django.contrib import admin
from .views import ordered_product_mapping

urlpatterns = [
url(r'^ordered-product-mapping/', ordered_product_mapping, name="ordered_product_mapping"),
]
