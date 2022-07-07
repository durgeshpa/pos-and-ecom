from django.conf.urls import url
from rest_framework import routers

from .views import (ProductsList, SearchProducts, CartCentral, CartCheckout, OrderCentral, OrderedItemCentralDashBoard,
                    ReservedOrder, OrderListCentral, OrderReturns, OrderReturnsCheckout, OrderReturnComplete,
                    CustomerCareApi, CustomerOrdersList, PaymentApi, DownloadInvoiceSP, ProductDetail, ReleaseBlocking,
                    OrderedProductViewSet, OrderedProductMappingView, DeliveryBoyTrips, RetailerShopsList, FeedbackData,
                    SellerOrderList, DeliveryShipmentDetails, ShipmentDetail, PickerDashboardViewSet, RescheduleReason,
                    ReturnReason, ShipmentDeliveryUpdate, ShipmentDeliveryBulkUpdate, DownloadCreditNoteDiscounted,
                    AutoSuggest, RefreshEs, RefreshEsRetailer, CartUserView, UserView, PosUserShopsList,
                    PosShopUsersList, RetailerList, PaymentDataView, CartStockCheckView, OrderCommunication,
                    OrderPaymentStatusChangeView, OrderStatusChoicesList, ShipmentView, EcomPaymentView,
                    EcomPaymentSuccessView, EcomPaymentFailureView, ShipmentProductView,
                    ProcessShipmentView, ShipmentStatusList, ShipmentQCView, ShipmentCityFilterView,
                    ShipmentPincodeFilterView, ShipmentShopFilterView, ShipmentProductRejectionReasonList,
                    PackagingTypeList, DispatchItemsView, DispatchItemsUpdateView, DispatchDashboardView,
                    DownloadShipmentInvoice, DispatchPackageRejectionReasonList, DeliverBoysList, NotAttemptReason,
                    DispatchTripsCrudView, ShipmentPackagingView, DispatchCenterShipmentView, TripSummaryView,
                    DispatchTripStatusChangeView, LoadVerifyPackageView, UnloadVerifyPackageView, LastMileTripCrudView,
                    LastMileTripShipmentsView, ShipmentCratesPackagingView, VerifyRescheduledShipmentPackagesView,
                    ShipmentCompleteVerifyView, DispatchCenterReturnOrderView, DispatchTripStatusList,
                    ShipmentCompleteVerifyView, VerifyReturnShipmentProductsView, DispatchPackageStatusList,
                    ShipmentCratesValidatedView, LastMileTripStatusChangeView, ShipmentDetailsByCrateView,
                    ReschedulingReasonsListView, ReturnReasonsListView, ShipmentNotAttemptReasonsListView,
                    CrateRemarkReasonsListView, LastMileTripStatusList, LoadVerifyCrateView, UnloadVerifyCrateView,
                    LoadInvoiceView, PackagesUnderTripView, MarkShipmentPackageVerifiedView,
                    ShipmentPackageProductsView, RemoveInvoiceFromTripView, DispatchCenterCrateView,
                    DispatchCenterShipmentPackageView, LoadLastMileInvoiceView, LastMileTripSummaryView,
                    LastMileLoadVerifyPackageView, RemoveLastMileInvoiceFromTripView,
                    VerifyNotAttemptShipmentPackagesView, VerifyBackwardTripItems, BackwardTripQCView,
                    VehicleDriverList, PosOrderUserSearchView, CurrentlyLoadingShipmentPackagesView,
                    ReturnOrderCompleteVerifyView, LastMileTripReturnOrderView, ReturnOrderProductView,
                    GenerateBarcodes, LastMileTripDeliveryReturnOrderView, VerifyReturnOrderProductsView,
                    LoadVerifyReturnOrderView, UnloadVerifyReturnOrderView,
                    BackWardTripReturnOrderQCView, MarkReturnOrderItemVerifiedView, ReturnRejection)

from retailer_backend.cron import sync_es_products_api
router = routers.DefaultRouter()
router.register(r'picker-dashboard', PickerDashboardViewSet)
router.register(r'ordered-product-mapping', OrderedProductMappingView)

urlpatterns = [
    # SEARCH
    url('^search/(?P<product_name>.+)/$', ProductsList.as_view()),
    url('^GRN/search/$', SearchProducts.as_view()),
    # CART
    url('^cart/$', CartCentral.as_view(), name='add_to_cart'),
    url(r'^cart/(?P<pk>\d+)/$', CartCentral.as_view()),
    url(r'^cart/user/(?P<pk>\d+)/$', CartUserView.as_view()),
    url('^user/$', UserView.as_view()),
    
    # CART CHECKOUT
    url('^cart/checkout/$', CartCheckout.as_view()),
    url(r'^cart/checkout/(?P<pk>\d+)/$', CartCheckout.as_view()),
    # COMMIT TO ORDER
    url('^cart/check/stock_qty/$', CartStockCheckView.as_view(), name='ecom_cart_check'),
    url('^reserved-order/$', ReservedOrder.as_view(), name='reserved_order'),
    url('^payment-data/$', PaymentDataView.as_view(), name='ecom-payment-data'),
    # ORDER
    url('^order/$', OrderCentral.as_view()),
    url(r'^order/(?P<pk>\d+)/$', OrderCentral.as_view()),
    url(r'^order-communication/(?P<type>[-\w]+)/(?P<pk>\d+)/$', OrderCommunication.as_view()),
    url('^order-list/$', OrderListCentral.as_view(), name='order_list'),
    url('^order-dashboard/$', OrderedItemCentralDashBoard.as_view()),
    # RETURNS
    url('^return/$', OrderReturns.as_view()),
    url('^return/checkout/$', OrderReturnsCheckout.as_view()),
    url('^return/complete/$', OrderReturnComplete.as_view()),
    # Shops List
    url('^pos-user-shops/$', PosUserShopsList.as_view()),
    url('^retailer-shops/$', RetailerShopsList.as_view(), name='retailer_shops'),
    # Shop Users
    url('^pos-shop-users/$', PosShopUsersList.as_view()),
    # Products ES Refresh
    url('^refresh-es/$', RefreshEs.as_view()),
    url('^refresh-es-retailer/$', RefreshEsRetailer.as_view()),
    url('^cron-es/$', sync_es_products_api),
    # Shipment
    url(r'^ecom-shipment/', ShipmentView.as_view(), name='ecom-shipment'),
    # Payment
    url(r'^ecom-payment/', EcomPaymentView.as_view(), name='ecom-payment'),
    url(r'^ecom-payment-success/', EcomPaymentSuccessView.as_view(), name='ecom-payment-success'),
    url(r'^ecom-payment-failed/', EcomPaymentFailureView.as_view(), name='ecom-payment-failed'),
    # OTHERS
    url('^download-invoice/(?P<pk>\d+)/invoice/$', DownloadInvoiceSP.as_view(), name='download_invoice_sp'),
    url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
    url('^order-payment/$', PaymentApi.as_view(), name='order_payment'),
    url('^release-blocking/$', ReleaseBlocking.as_view(), name='release-blocking'),
    url('^product_detail/(?P<pk>\d+)/$', ProductDetail.as_view(), name='product_detail'),
    url('^trip-shipments/(?P<day>.+)/(?P<month>.+)/(?P<year>.+)/$', DeliveryBoyTrips.as_view(), name='trip-shipments'),
    url('^trip-shipment-details/(?P<trip>[-\w]+)/$', DeliveryShipmentDetails.as_view(), name='trip-shipment-details'),
    url('^shipment-detail/(?P<shipment>[-\w]+)/$', ShipmentDetail.as_view(), name='shipment-detail'),
    url('^shipment-delivery-update/(?P<shipment>[-\w]+)/$', ShipmentDeliveryUpdate.as_view(),
        name='shipment-delivry-update'),
    url('^shipment-bulk-update/(?P<shipment>[-\w]+)/$', ShipmentDeliveryBulkUpdate.as_view(),
        name='shipment-delivry-bulk-update'),
    url('^feedback/$', FeedbackData.as_view(), name='feed_back'),
    url('^feedback/(?P<ship_id>\d+)/list/$', FeedbackData.as_view(), name='feed_back_list'),
    url('^seller-order-list/$', SellerOrderList.as_view(), name='seller-order-list'),
    url('^retailer-list/$', RetailerList.as_view(), name='retailer-list'),
    url('^reschedule-reason/$', RescheduleReason.as_view(), name='reschedule-reason'),
    url('^not-attempt-reason/$', NotAttemptReason.as_view(), name='not-attempt-reason'),
    url('^return-reason/$', ReturnReason.as_view(), name='return-reason'),
    url('^discounted_credit_note/(?P<pk>\d+)/note/$',
        DownloadCreditNoteDiscounted.as_view(),
        name='discounted_credit_note'),
    url('^autosearch/suggest/$', AutoSuggest.as_view()),
    url(r'^ordered-product/$', OrderedProductViewSet.as_view()),
    url(r'^shipment-products/$', ShipmentProductView.as_view()),
    url(r'^return-order-products/$', ReturnOrderProductView.as_view()),
    url(r'^process-shipment/$', ProcessShipmentView.as_view()),
    url(r'^shipment-status-list/$', ShipmentStatusList.as_view()),
    url('shipments/', ShipmentQCView.as_view()),
    url('shipment-city-list/', ShipmentCityFilterView.as_view()),
    url('shipment-pincode-list/', ShipmentPincodeFilterView.as_view()),
    url('shipment-shop-list/', ShipmentShopFilterView.as_view()),
    url('rejection-reason/', ShipmentProductRejectionReasonList.as_view()),
    url('packaging-type/', PackagingTypeList.as_view()),
    url('dispatch-items/', DispatchItemsView.as_view()),
    url('dispatch-update/', DispatchItemsUpdateView.as_view()),
    url('dispatch-dashboard/', DispatchDashboardView.as_view()),
    url('shipment-invoice/', DownloadShipmentInvoice.as_view()),
    url('package-reject-reason/', DispatchPackageRejectionReasonList.as_view()),
    url('update-order-payment-status/', OrderPaymentStatusChangeView.as_view(), name='update_order_payment_status'),
    url(r'^order-status-choice/$', OrderStatusChoicesList.as_view()),
    url('delivery-boys-list/', DeliverBoysList.as_view(), name='delivery_boys_list'),
    url('vehicle-drivers-list/', VehicleDriverList.as_view(), name='vehicle_drivers_list'),
    url('dispatch-trips/', DispatchTripsCrudView.as_view(), name='dispatch_trips'),
    url('update-dispatch-trip-status/', DispatchTripStatusChangeView.as_view(), name='update_dispatch_trip_status'),
    url('shipment-packaging/', ShipmentPackagingView.as_view(), name='shipment_packaging'),
    url('shipment-details-by-crates/', ShipmentDetailsByCrateView.as_view(), name='shipment_details_by_crates'),
    url('shipment-crates-packaging/', ShipmentCratesPackagingView.as_view(), name='shipment_crates_packaging'),
    url('verify-rescheduled-shipment-packages/', VerifyRescheduledShipmentPackagesView.as_view(),
        name='verify_rescheduled_shipment_packages'),
    url('verify-not-attempt-shipment-packages/', VerifyNotAttemptShipmentPackagesView.as_view(),
        name='verify_not_attempt_shipment_packages'),
    url('verify-return-shipment-products/', VerifyReturnShipmentProductsView.as_view(),
        name='verify_return_shipment_products'),
    url('shipment-crates-validated/', ShipmentCratesValidatedView.as_view(), name='shipment_crates_validated'),
    url('shipment-complete-verification/', ShipmentCompleteVerifyView.as_view(), name='shipment_complete_verification'),
    url('return-order-complete-verification/', ReturnOrderCompleteVerifyView.as_view(), name='return_order_complete_verification'),
    url('trip-summary/', TripSummaryView.as_view(), name='trip_summary'),
    url('trip-invoices/', DispatchCenterShipmentView.as_view()),
    url('trip-crates/', DispatchCenterCrateView.as_view()),
    url('trip-shipment-packages/', DispatchCenterShipmentPackageView.as_view()),
    url('trip-return-orders/', DispatchCenterReturnOrderView.as_view()),
    url('trip-invoice-remove/', RemoveInvoiceFromTripView.as_view()),
    url('trip-load-empty-crate/', LoadVerifyCrateView.as_view()),
    url('trip-unload-empty-crate/', UnloadVerifyCrateView.as_view()),
    url('trip-load-shipment/', LoadVerifyPackageView.as_view()),
    url('trip-load-return/', LoadVerifyReturnOrderView.as_view()),
    url('trip-unload-return/', UnloadVerifyReturnOrderView.as_view()),
    url('trip-current-loading-shipment/', CurrentlyLoadingShipmentPackagesView.as_view()),
    url('trip-add-invoice/', LoadInvoiceView.as_view()),
    url('trip-unload-shipment/', UnloadVerifyPackageView.as_view()),
    url('last-mile-trips/', LastMileTripCrudView.as_view(), name='last_mile_trips'),
    url('last-mile-invoices/', LastMileTripShipmentsView.as_view(), name='last_mile_invoices'),
    url('last-mile-returns/', LastMileTripReturnOrderView.as_view(), name='last_mile_returns'),
    url('last-mile-summary/', LastMileTripSummaryView.as_view(), name='last_mile_summary'),
    url('trip-last-mile-add-invoice/', LoadLastMileInvoiceView.as_view()),
    url('trip-last-mile-invoice-remove/', RemoveLastMileInvoiceFromTripView.as_view()),
    url('trip-last-mile-load-package/', LastMileLoadVerifyPackageView.as_view()),
    url('update-last-mile-trip-status/', LastMileTripStatusChangeView.as_view(), name='update_last_mile_trip_status'),
    url('package-status-choice/', DispatchPackageStatusList.as_view()),
    url('rescheduling-reason-choice/', ReschedulingReasonsListView.as_view(), name='rescheduling_reason_choice'),
    url('return-reason-choice/', ReturnReasonsListView.as_view(), name='return_reason_choice'),
    url('not-attempt-reason-choice/', ShipmentNotAttemptReasonsListView.as_view(), name='not_attempt_reason_choice'),
    url('crate-remark-reason-choice/', CrateRemarkReasonsListView.as_view(), name='crate_remark_reason_choice'),
    url('trip-status-choice/', DispatchTripStatusList.as_view()),
    url('last-mile-status-choice/', LastMileTripStatusList.as_view()),
    url('packages-under-trip/', PackagesUnderTripView.as_view(), name='packages_under_trip'),
    url('mark-shipment-verified/', MarkShipmentPackageVerifiedView.as_view(), name='mark_shipment_verified'),
    url('shipment-package-products/', ShipmentPackageProductsView.as_view(), name='shipment_package_products'),
    url('bck-trip-verify-items/', VerifyBackwardTripItems.as_view()),
    url('bck-trip-qc-packages/', BackwardTripQCView.as_view()),
    url('pos-user-search/', PosOrderUserSearchView.as_view(), name='pos-user-search'),
    # API to Generate Barcodes
    url('generate-barcode/', GenerateBarcodes.as_view()),
    # API to details of return items of a shop for delivery APP
    url('last-mile-delivery-returns/', LastMileTripDeliveryReturnOrderView.as_view(), name='last_mile_delivery_returns'),
    # API to reject return items of a shop from delivery APP
    url('reject-returns/', ReturnRejection.as_view(), name='reject_returns'),

    # API to update  return in the trip
    url('verify-return-order-products/', VerifyReturnOrderProductsView.as_view(), name='verify_return_order_products'),
    url('bck-trip-return-items/', BackWardTripReturnOrderQCView.as_view(), name='bck_trip_return_items'),
    url('mark-return-order-item-verified/', MarkReturnOrderItemVerifiedView.as_view(), name='mark-return-order-item-verified')
]

urlpatterns += router.urls
