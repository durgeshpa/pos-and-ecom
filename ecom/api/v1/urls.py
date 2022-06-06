from django.conf.urls import url

from .views import AccountView, RewardsView, ShopView, AddressView, AddressListView, \
    CategoriesView, SubCategoriesView, TagView, TagProductView, UserShopView \
    , Contect_Us, ParentProductDetails, B2cCategoriesView, B2cSubCategoriesView, PastPurchasedProducts, \
    ProductFunctionView, ReferAndEarnView, SuperStoreCategoriesView, SuperStoreSubCategoriesView


urlpatterns = [
    url(r'^shop/', ShopView.as_view(), name='ecom-shop'),
    url(r'^account/', AccountView.as_view(), name='ecom-user-account'),
    url(r'^rewards/', RewardsView.as_view(), name='ecom-user-rewards'),
    url(r'^refer_and_earn/', ReferAndEarnView.as_view(), name='refer_and_earn'),
    url(r'^address/$', AddressView.as_view(), name='ecom-user-address'),
    url(r'^address/(?P<pk>\d+)/$', AddressView.as_view(), name='ecom-user-address-create'),
    url(r'^address-list/', AddressListView.as_view(), name='ecom-user-address-list'),
    url(r'^categories/', CategoriesView.as_view(), name='ecom-shop-categories'),
    url(r'^sub-categories/', SubCategoriesView.as_view(), name='ecom-shop-subcategories'),
    url(r'^b2c-categories/', B2cCategoriesView.as_view(), name='ecom-shop-b2c-categories'),
    url(r'^b2c-sub-categories/', B2cSubCategoriesView.as_view(), name='ecom-shop-b2c-subcategories'),
    url(r'^tags/', TagView.as_view(), name='ecom-tag'),
    url(r'^tag-product/(?P<pk>\d+)/$', TagProductView.as_view(), name='ecom-tag-product'),
    url(r'^product-function/(?P<pk>\d+)/$', ProductFunctionView.as_view(), name='product-function'),
    url(r'^shop-user-mapping/$', UserShopView.as_view(), name='shop-user-mapping'),
    url(r'^contect_us_details/', Contect_Us.as_view(), name='contect_us_ecom'),
    url(r'^parent_product/(?P<pk>\d+)/$', ParentProductDetails.as_view(),name='parent_product_discription'),
    url(r'^past-purchases/$', PastPurchasedProducts.as_view()),
    url(r'^super-store-categories/', SuperStoreCategoriesView.as_view(), name='super-store-categories'),
    url(r'^super-store-sub-categories/', SuperStoreSubCategoriesView.as_view(), name='super-store-sub-categories')
]
