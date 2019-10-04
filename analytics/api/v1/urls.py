from django.conf.urls import include, url
from banner.api.v1 import views
from .views import (CategoryProductReport)

urlpatterns = [
    url(r'^product-category-report/$', CategoryProductReport.as_view(), name='product_category_report'),
]
