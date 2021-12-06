from rest_framework import routers
from django.conf.urls import url

from shops.api.v2.views import (ApprovalStatusListView, AddressListView, BeatPlanningExportAsCSVView,
                                BeatPlanningListView, BeatPlanningSampleCSV, BeatPlanningView, ParentShopsListView,
                                RelatedUsersListView, ServicePartnerShopsListView, BulkCreateShopUserMappingView,
                                ShopDocumentTypeListView, ShopInvoiceStatusListView, ShopOwnerNameListView,
                                ShopSalesReportView, ShopTypeListView, ShopTypeView, ShopUserMappingView,
                                ShopListView, ShopManagerListView, ShopEmployeeListView, RetailerTypeList,
                                ShopTypeChoiceView, BulkUpdateShopView, BeatPlanningExecutivesListView,
                                DisapproveShopSelectedShopView, PinCodeView, StateView, CityView, AddressTypeChoiceView,
                                BulkUpdateShopSampleCSV, BulkCreateShopUserMappingSampleCSV, ShopCrudView,
                                ShopManagerListDisView, SellerShopFilterView, DispatchCenterFilterView)

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
    url('shop-type/', ShopTypeView.as_view(), name='shop-type'),
    # url('shop-type-crud/', ShopTypeCrudView.as_view(), name='shop-type-crud'),
    url('shop-list/', ShopListView.as_view(), name='shop-list'),
    url('shop-sales-report-download/', ShopSalesReportView.as_view(), name='shop-sales-report-download'),
    url('sp-shop/', ServicePartnerShopsListView.as_view(), name='sp-shop'),
    url('parent-shop/', ParentShopsListView.as_view(), name='parent-shop'),
    url('shop-users-mapping/', ShopUserMappingView.as_view(), name='shop-users-mapping'),
    url('shop-users-mapping-list/', ShopManagerListDisView.as_view(), name='shop-users-mapping-list'),
    url('shop-managers/', ShopManagerListView.as_view(), name='shop-managers'),
    url('shop-employees/', ShopEmployeeListView.as_view(), name='shop-employees'),
    url('retailer-type-list/', RetailerTypeList.as_view(), name='retailer-type-list'),
    url('shop-type-choice/', ShopTypeChoiceView.as_view(), name='shop-type-choice'),
    url('shop-disapproved', DisapproveShopSelectedShopView.as_view(), name='shop-disapproved'),
    url('shop-city', CityView.as_view(), name='shop-city'),
    url('shop-state', StateView.as_view(), name='shop-state'),
    url('shop-pincode', PinCodeView.as_view(), name='shop-pincode'),
    url('shop-address-type', AddressTypeChoiceView.as_view(), name='hop-address-type'),
    url('shop/', ShopCrudView.as_view(), name='shops'),

    url('download/shop-user-mapping-create-sample-csv', BulkCreateShopUserMappingSampleCSV.as_view(),
        name='download/shop-user-mapping-update-create-csv'),
    url('upload/bulk-shop-user-mapping-create', BulkCreateShopUserMappingView.as_view(),
        name='upload/bulk-shop-user-mapping-create'),

    url('download/shop-update-sample-csv', BulkUpdateShopSampleCSV.as_view(), name='download/shop-update-sample-csv'),
    url('upload/bulk-shop-update', BulkUpdateShopView.as_view(),
        name='upload/bulk-shop-update'),
    url('export-csv-beat-planning/', BeatPlanningExportAsCSVView.as_view(), name='export-csv-beat-planning'),
    url('download/beat-planning/sample', BeatPlanningSampleCSV.as_view(), name='download-beat-planning-sample'),
    url('upload/beat-planning', BeatPlanningView.as_view(), name='upload/beat-planning'),
    url('beat-planning/', BeatPlanningListView.as_view(), name='beat-planning'),
    url('beat-plan-employees/', BeatPlanningExecutivesListView.as_view(), name='beat-plan-employees'),
    url('seller-shops-list/', SellerShopFilterView.as_view(), name='seller-shops-list'),
    url('dispatch-centers-list/', DispatchCenterFilterView.as_view(), name='dispatch-centers-list'),
]

urlpatterns += router.urls
