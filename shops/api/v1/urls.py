from django.conf.urls import url
from django.urls import path
from shops.api.v1.views import (RetailerTypeView, ShopTypeView,ShopView, ShopPhotoView, ShopDocumentView,
        TeamListView, SellerShopView, SellerShopOrder, SellerShopProfile, SalesPerformanceView, SellerShopListView)
from addresses.api.v1.views import AddressView, DefaultAddressView, AddressDetail

urlpatterns = [
    path('user-shops/', ShopView.as_view(), name='user-shops', ),
    path('user-shop-address/', AddressView.as_view(), name='user-shop-address',),
    path('user-shop-address/default/', DefaultAddressView.as_view(), name='user-shop-address-default',),
    path('user-shop-address/<int:pk>/', AddressDetail.as_view(), name='user-shop-address-edit', ),
    path('retailer-type/', RetailerTypeView.as_view(), name='retailer-type', ),
    path('shop-type/', ShopTypeView.as_view(), name='shop-type', ),
    path('shop-photo/', ShopPhotoView.as_view(), name='shop-photo', ),
    path('shop-document/', ShopDocumentView.as_view(), name='shop-document', ),
    path('seller-team-list/', TeamListView.as_view(), name='team-list', ),
    path('seller-shops/', SellerShopView.as_view(), name='seller-shops', ),
    path('seller-shop-profile/', SellerShopProfile.as_view(), name='seller-shop-profile', ),
    path('seller-shop-order/', SellerShopOrder.as_view(), name='seller-shops', ),
    path('seller-performance/', SalesPerformanceView.as_view(), name='seller-performance', ),
    path('seller-shop-list/', SellerShopListView.as_view(), name='seller-shop-list', ),

]
