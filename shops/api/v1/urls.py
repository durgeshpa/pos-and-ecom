from django.conf.urls import url
from django.urls import path
from shops.api.v1.views import (RetailerTypeView, ShopTypeView, AddShopView,
            ShopView, ShopPhotoView, ShopDocumentView)
from addresses.api.v1.views import AddressView

urlpatterns = [
    path('add-user-shops/', AddShopView.as_view(), name='add-user-shops', ),
    path('user-shops/', ShopView.as_view(), name='user-shops', ),
    path('user-shop-address/', AddressView.as_view(), name='user-shop-address',),
    path('retailer-type/', RetailerTypeView.as_view(), name='retailer-type', ),
    path('shop-type/', ShopTypeView.as_view(), name='shop-type', ),
    path('shop-photo/', ShopPhotoView.as_view(), name='shop-photo', ),
    path('shop-document/', ShopDocumentView.as_view(), name='shop-document', ),

]
