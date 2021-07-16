from django.conf.urls import url

from .views import AccountView, RewardsView, ShopView, AddressView, AddressListView

urlpatterns = [
    url(r'^shop/', ShopView.as_view(), name='ecom-shop'),
    url(r'^account/', AccountView.as_view(), name='ecom-account'),
    url(r'^rewards/', RewardsView.as_view(), name='user-rewards'),

    url('^address/$', AddressView.as_view(), name='ecom-address'),
    url('^address/(?P<pk>\d+)/$', AddressView.as_view()),
    
    url(r'^address-list/', AddressListView.as_view(), name='ecom-address-list'),
]
