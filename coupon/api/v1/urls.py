from django.conf.urls import url
from .views import CouponView

urlpatterns = [
    url(r'^coupons/$', CouponView.as_view(), name='retailer-coupon'),
]