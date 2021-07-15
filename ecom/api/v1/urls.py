from django.conf.urls import url

from .views import AccountView, RewardsView, ShopView

urlpatterns = [
    url(r'^shop/', ShopView.as_view(), name='ecom-shop'),
    url(r'^account/', AccountView.as_view(), name='ecom-account'),
    url(r'^rewards/', RewardsView.as_view(), name='user-rewards'),
]
