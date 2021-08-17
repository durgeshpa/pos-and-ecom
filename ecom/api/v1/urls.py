from django.conf.urls import url

from .views import AccountView, RewardsView, ShopView, AddressView, AddressListView, CategoriesView, SubCategoriesView

urlpatterns = [
    url(r'^shop/', ShopView.as_view(), name='ecom-shop'),
    url(r'^account/', AccountView.as_view(), name='ecom-user-account'),
    url(r'^rewards/', RewardsView.as_view(), name='ecom-user-rewards'),
    url(r'^address/$', AddressView.as_view(), name='ecom-user-address'),
    url(r'^address/(?P<pk>\d+)/$', AddressView.as_view(), name='ecom-user-address-create'),
    url(r'^address-list/', AddressListView.as_view(), name='ecom-user-address-list'),
    url(r'^categories/', CategoriesView.as_view(), name='ecom-shop-categories'),
    url(r'^sub-categories/', SubCategoriesView.as_view(), name='ecom-shop-subcategories'),
]
