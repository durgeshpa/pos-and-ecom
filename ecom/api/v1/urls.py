from django.conf.urls import url

from .views import AccountView, RewardsView, ShopView, AddressView, AddressListView, CategoriesView, SubCategoriesView, TagView, TagProductView, UserShopView \
,Contect_Us, ParentProductDetails


urlpatterns = [
    url(r'^shop/', ShopView.as_view(), name='ecom-shop'),
    url(r'^account/', AccountView.as_view(), name='ecom-user-account'),
    url(r'^rewards/', RewardsView.as_view(), name='ecom-user-rewards'),
    url(r'^address/$', AddressView.as_view(), name='ecom-user-address'),
    url(r'^address/(?P<pk>\d+)/$', AddressView.as_view(), name='ecom-user-address-create'),
    url(r'^address-list/', AddressListView.as_view(), name='ecom-user-address-list'),
    url(r'^categories/', CategoriesView.as_view(), name='ecom-shop-categories'),
    url(r'^sub-categories/', SubCategoriesView.as_view(), name='ecom-shop-subcategories'),
    url(r'^tags/', TagView.as_view(), name='ecom-tag'),
    url(r'^tag-product/(?P<pk>\d+)/$', TagProductView.as_view(), name='ecom-tag-product'),
    url(r'^shop-user-mapping/$', UserShopView.as_view(), name='shop-user-mapping'),
    url(r'^contect_us_details/', Contect_Us.as_view(), name='contect_us_ecom'),
    url(r'^parent_product/(?P<pk>\d+)/$', ParentProductDetails.as_view(),name='parent_product_discription'),
]
