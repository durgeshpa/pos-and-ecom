from django.conf.urls import url
from .views import DiscountView

urlpatterns = [
    url(r'^discount/$', DiscountView.as_view(), name='retailer-discount'),
]