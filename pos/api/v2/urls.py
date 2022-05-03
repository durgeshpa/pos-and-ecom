from django.conf.urls import url
from rest_framework import routers


from .views import (ShopOwnerNameListView, ShopNameListView,
                    ShopTypeListView, RewardConfigShopListView,
                    RewardConfigShopCrudView, ShopRewardConfigKeys)
from shops.api.v2.views import CityView, StateView, PinCodeView
router = routers.DefaultRouter()
"""
@Durgesh patel
"""
urlpatterns = [

    # -------------- React Admin Urls --------------------------- #
    url(r'^shop-owner-list/', ShopOwnerNameListView.as_view(), name='fofo-foco-shop-owner-list'),
    url(r'^shop-name-list/', ShopNameListView.as_view(), name='fofo-foco-shop-name-list'),
    url(r'^shop-type-list/', ShopTypeListView.as_view(), name='fofo-foco-shop-name-list'),
    url(r'^reward-config-shop-list/', RewardConfigShopListView.as_view(), name='reward-config-shop-list'),
    url(r'^reward-config-shop-crud/', RewardConfigShopCrudView.as_view(), name='reward-config-shop-crud'),
    url(r'^shop-city/', CityView.as_view(), name='fofo-foco-shop-city'),
    url(r'^shop-state/', StateView.as_view(), name='fofo-foco-shop-state'),
    url(r'^shop-pincode/', PinCodeView.as_view(), name='fofo-foco-shop-pincode'),
    url(r'^shop-reward-config-key/', ShopRewardConfigKeys.as_view(), name='shop-reward-config-key' ),
    url(r'^reward-config-shop-bulk-update', RewardConfigShopCrudView.as_view()),
    ]

urlpatterns += router.urls
