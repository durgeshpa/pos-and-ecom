from rest_framework import routers
from django.conf.urls import url
from django.urls import path

from shops.api.v1.views import (RetailerTypeView, ShopTypeView,
        ShopView, ShopPhotoView, ShopDocumentView, FavouriteProductView)
from addresses.api.v1.views import AddressView, DefaultAddressView, AddressDetail

router = routers.DefaultRouter()
router.register(r'favourite-product', FavouriteProductView)

urlpatterns = [
    path('user-shops/', ShopView.as_view(), name='user-shops', ),
    path('user-shop-address/', AddressView.as_view(), name='user-shop-address',),
    path('user-shop-address/default/', DefaultAddressView.as_view(), name='user-shop-address-default',),
    path('user-shop-address/<int:pk>/', AddressDetail.as_view(), name='user-shop-address-edit', ),
    path('retailer-type/', RetailerTypeView.as_view(), name='retailer-type', ),
    path('shop-type/', ShopTypeView.as_view(), name='shop-type', ),
    path('shop-photo/', ShopPhotoView.as_view(), name='shop-photo', ),
    path('shop-document/', ShopDocumentView.as_view(), name='shop-document', ),

]

urlpatterns += router.urls