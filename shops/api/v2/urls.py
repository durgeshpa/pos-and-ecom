from rest_framework import routers
from django.conf.urls import url
from django.urls import path

from shops.api.v2.views import (ApprovalStatusListView, AddressListView, RelatedUsersListView, ShopDocumentTypeListView,
                                ShopInvoiceStatusListView, ShopOwnerNameListView, ShopTypeListView, ShopTypeDetailView, ShopView)

router = routers.DefaultRouter()

urlpatterns = [

    # -------------- React Admin Urls --------------------------- #
    url('shop-owner-list/', ShopOwnerNameListView.as_view(), name='shop-owner-list'),
    url('address-list/', AddressListView.as_view(), name='address-list'),
    url('related-users-list/', RelatedUsersListView.as_view(), name='related-users-list'),
    url('approval-status-list/', ApprovalStatusListView.as_view(),
        name='approval-status-list'),
    url('shop-document-type-list/', ShopDocumentTypeListView.as_view(),
        name='shop-document-type-list'),
    url('shop-invoice-status-list/', ShopInvoiceStatusListView.as_view(),
        name='shop-invoice-status-list'),
    url('shop-type-list/', ShopTypeListView.as_view(), name='shop-type-list'),
    url('shop-type/', ShopTypeDetailView.as_view(), name='shop-type-list'),
    url('shops/', ShopView.as_view(), name='shops'),

]

urlpatterns += router.urls
