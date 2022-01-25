from rest_framework import routers
from django.conf.urls import url
from django.urls import path

from shops.api.v1.views import (PosShopUserMappingView, RetailerTypeView, ShopListView, ShopTypeView,
                                ShopView, ShopPhotoView, ShopDocumentView, FavouriteProductView,
                                FavouriteProductListView, UserTypeListView, UserDocumentChoices,
                                ShopDocumentChoices, FOFOConfigurationsView, FOFOConfigCategoryView,
                                FOFOConfigSubCategoryView)
from addresses.api.v1.views import AddressView, DefaultAddressView, AddressDetail

from shops.api.v1.views import (RetailerTypeView, ShopTypeView,ShopView, ShopPhotoView, ShopDocumentView, ShopTimingView,
        TeamListView, SellerShopView, SellerShopOrder, SellerShopProfile, SalesPerformanceView,
        SellerShopListView, CheckUser, CheckAppVersion, StatusChangedAfterAmountCollected, SalesPerformanceUserView,
        ShopRequestBrandViewSet, FavouriteProductView, FavouriteProductListView, DayBeatPlan, ExecutiveReport, set_shop_map_cron)
from addresses.api.v1.views import AddressView, DefaultAddressView, AddressDetail, SellerShopAddress

router = routers.DefaultRouter()
router.register(r'request-brand', ShopRequestBrandViewSet)
router.register(r'favourite-product', FavouriteProductView)
router.register('beat-plan-user', DayBeatPlan)
router.register('executive-report', ExecutiveReport)
#router.register(r'list-favourite-product', FavouriteProductListView)

urlpatterns = [
    path('user-shops/', ShopView.as_view(), name='user-shops', ),
    path('user-shop-address/', AddressView.as_view(), name='user-shop-address',),
    path('user-shop-address/default/', DefaultAddressView.as_view(), name='user-shop-address-default',),
    path('user-shop-address/<int:pk>/', AddressDetail.as_view(), name='user-shop-address-edit', ),
    path('list-favourite-product/', FavouriteProductListView.as_view(), name='list-favourite-product', ),
    path('retailer-type/', RetailerTypeView.as_view(), name='retailer-type', ),
    path('shop-type/', ShopTypeView.as_view(), name='shop-type', ),
    path('shop-photo/', ShopPhotoView.as_view(), name='shop-photo', ),
    path('shop-document/', ShopDocumentView.as_view(), name='shop-document', ),
    path('shop-timing/', ShopTimingView.as_view(), name='shop-timing', ),
    url('shop-timing/(?P<shop_id>\d+)/shop/', ShopTimingView.as_view(), name='shop-timing-list', ),

# --------------------------------------------------Sales Person APIs---------------------------------------------------
    path('seller-team-list/', TeamListView.as_view(), name='seller-team-list', ),
    path('seller-shops/', SellerShopView.as_view(), name='seller-shops', ),
    path('seller-shop-profile/', SellerShopProfile.as_view(), name='seller-shop-profile', ),
    path('seller-shop-order/', SellerShopOrder.as_view(), name='seller-shops', ),
    path('seller-performance/', SalesPerformanceView.as_view(), name='seller-performance', ),
    path('seller-performance-user-list/', SalesPerformanceUserView.as_view(), name='seller-performance-user-list', ),
    path('seller-shop-list/', SellerShopListView.as_view(), name='seller-shop-list', ),
    path('seller-check-user/', CheckUser.as_view(), name='seller-check-user', ),
    path('seller-shop-address/', SellerShopAddress.as_view(), name='seller-shop-address', ),
    path('check-app-version/', CheckAppVersion.as_view(), name='check-app-version', ),
    # path('beat-plan-user/', DayBeatPlan.as_view(), name='beat-plan-user', ),
#------------------------------------------------------------------------------------------------------------------------
    url('^amount-collected/(?P<shipment>\d+)/$', StatusChangedAfterAmountCollected.as_view(), name='amount-collected'),


# --------------------------------------------------POS APIs---------------------------------------------------
    path('pos-shop-user/', PosShopUserMappingView.as_view(), name='pos-shop-user', ),
    url(r'^pos-shop-user/(?P<pk>\d+)/$', PosShopUserMappingView.as_view()),
    url('shop-list/', ShopListView.as_view(), name='shop-list'),
    url('pos-user-type-list/', UserTypeListView.as_view(), name='pos-user-type-list'),
    url('shop-doc-user-choices/', UserDocumentChoices.as_view(), name='shop-doc-user-choices'),
    url('shop-doc-shop-choices/', ShopDocumentChoices.as_view(), name='shop-doc-shop-choices'),

    url('fofo-category-configurations/', FOFOConfigCategoryView.as_view(),
        name='fofo-category-configurations'),
    url('fofo-subcategory-configurations/', FOFOConfigSubCategoryView.as_view(),
        name='fofo-subcategory-configurations'),
    url('fofo-configurations/', FOFOConfigurationsView.as_view(), name='fofo-configurations'),

]

urlpatterns += router.urls