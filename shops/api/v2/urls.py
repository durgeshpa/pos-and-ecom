from rest_framework import routers
from django.conf.urls import url
from django.urls import path

from shops.api.v2.views import (ApprovalStatusListView, AddressListView, ParentShopsListView, RelatedUsersListView, ServicePartnerShopsListView, ShopDocumentTypeListView,
                                ShopInvoiceStatusListView, ShopOwnerNameListView, ShopSalesReportView, ShopTypeListView, ShopTypeDetailView, ShopUserMappingList, ShopView,
                                ShopListView, ShopManagerListView, ShopEmployeeListView)

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
    url('shop-list/', ShopListView.as_view(), name='shop-list'),
    url('shop-sales-report-download/', ShopSalesReportView.as_view(), name='shop-sales-report-download'),
    url('sp-shop/', ServicePartnerShopsListView.as_view(), name='sp-shop'),
    url('parent-shop/', ParentShopsListView.as_view(), name='parent-shop'),
    url('shop-users/', ShopUserMappingList.as_view(), name='shop-users'),
    url('shop-managers/', ShopManagerListView.as_view(), name='shop-managers'),
    url('shop-employees/', ShopEmployeeListView.as_view(), name='shop-employees'),

]

urlpatterns += router.urls
