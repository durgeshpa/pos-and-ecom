from django.conf.urls import url
from rest_framework import routers

from .views import (ProductsList, SearchProducts, CartCentral, CartCheckout, OrderCentral, OrderedItemCentralDashBoard,
                    ReservedOrder, OrderListCentral, OrderReturns, OrderReturnsCheckout, OrderReturnComplete,
                    CustomerCareApi, CustomerOrdersList, PaymentApi, DownloadInvoiceSP, ProductDetail, ReleaseBlocking,
                    OrderedProductViewSet, OrderedProductMappingView, DeliveryBoyTrips, RetailerShopsList, FeedbackData,
                    SellerOrderList, DeliveryShipmentDetails, ShipmentDetail, PickerDashboardViewSet, RescheduleReason,
                    ReturnReason, ShipmentDeliveryUpdate, ShipmentDeliveryBulkUpdate, DownloadCreditNoteDiscounted,
                    AutoSuggest, RefreshEs, RefreshEsRetailer, UserView
                    )

router = routers.DefaultRouter()
router.register(r'picker-dashboard', PickerDashboardViewSet)
router.register(r'ordered-product-mapping', OrderedProductMappingView)

urlpatterns = [
    # SEARCH
    url('^search/(?P<product_name>.+)/$', ProductsList.as_view()),
    url('^GRN/search/$', SearchProducts.as_view()),
    # CART
    url('^cart/$', CartCentral.as_view(), name='add_to_cart'),
    url('^user/$', UserView.as_view()),
    # CART CHECKOUT
    url('^cart/checkout/$', CartCheckout.as_view()),
    # ORDER
    url('^reserved-order/$', ReservedOrder.as_view(), name='reserved_order'),
    url('^order/$', OrderCentral.as_view()),
    url('^order/(?P<pk>\d+)/$', OrderCentral.as_view()),
    url('^order-list/$', OrderListCentral.as_view(), name='order_list'),
    url('^order-dashboard/$', OrderedItemCentralDashBoard.as_view()),
    # RETURNS
    url('^return/$', OrderReturns.as_view()),
    url('^return/checkout/$', OrderReturnsCheckout.as_view()),
    url('^return/complete/$', OrderReturnComplete.as_view()),
    # Products ES Refresh
    url('^refresh-es/$', RefreshEs.as_view()),
    url('^refresh-es-retailer/$', RefreshEsRetailer.as_view()),
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
    url('^retailer-shops/$', RetailerShopsList.as_view(), name='retailer_shops'),
    url('^seller-order-list/$', SellerOrderList.as_view(), name='seller-order-list'),
    url('^reschedule-reason/$', RescheduleReason.as_view(), name='reschedule-reason'),
    url('^return-reason/$', ReturnReason.as_view(), name='return-reason'),
    url('^discounted_credit_note/(?P<pk>\d+)/note/$',
        DownloadCreditNoteDiscounted.as_view(),
        name='discounted_credit_note'),
    url('^autosearch/suggest/$', AutoSuggest.as_view()),
    url(r'^ordered-product/$', OrderedProductViewSet.as_view())
]

urlpatterns += router.urls
