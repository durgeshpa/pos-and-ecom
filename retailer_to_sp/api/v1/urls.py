from django.conf.urls import include, url
from .views import (ProductsList, GramGRNProductsList,AddToCart,CartDetail,ReservedOrder,CreateOrder,OrderList,OrderDetail,DownloadInvoiceSP,
                    DownloadNote, CustomerCareApi, CustomerOrdersList,  PaymentApi, ProductDetail,ReleaseBlocking, DeliveryBoyTrips, DeliveryShipmentDetails, ShipmentDetail)
from rest_framework import routers

from .views import (ProductsList, GramGRNProductsList,AddToCart,CartDetail,
    ReservedOrder,CreateOrder,OrderList,OrderDetail,DownloadInvoiceSP,
    DownloadNote, CustomerCareApi, CustomerOrdersList,  PaymentApi,
    ProductDetail,ReleaseBlocking, OrderedProductViewSet, OrderedProductMappingView,
    CancelOrder, FeedbackData, DeliveryBoyTrips, StatusChangedAfterAmountCollected
)

router = routers.DefaultRouter()
router.register(r'ordered-product', OrderedProductViewSet)
router.register(r'ordered-product-mapping', OrderedProductMappingView)


urlpatterns = [
    url('^search/(?P<product_name>.+)/$', ProductsList.as_view()),
    url('^GRN/search/$', GramGRNProductsList.as_view()),
    #order Api
    url('^add-to-cart/$', AddToCart.as_view(), name='add_to_cart'),
    url('^cart-detail/$', CartDetail.as_view(), name='cart_detail'),
    url('^reserved-order/$', ReservedOrder.as_view(), name='reserved_order'),
    url('^create-order/$', CreateOrder.as_view(), name='reserved_order'),
    url('^order-list/$', OrderList.as_view(), name='order_list'),
    url('^order-detail/(?P<pk>\d+)/$', OrderDetail.as_view(), name='order_detail'),
    url('^download-invoice/(?P<pk>\d+)/invoice/$', DownloadInvoiceSP.as_view(), name='download_invoice_sp'),
    url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
    url('^order-payment/$', PaymentApi.as_view(), name='order_payment'),
    url('^release-blocking/$', ReleaseBlocking.as_view(), name='release-blocking'),
    url('^product_detail/(?P<pk>\d+)/$', ProductDetail.as_view(), name='product_detail'),
    url('^trip-shipments/(?P<day>.+)/(?P<month>.+)/(?P<year>.+)/$', DeliveryBoyTrips.as_view(), name='trip-shipments'),
    url('^trip-shipment-details/(?P<trip>[-\w]+)/$', DeliveryShipmentDetails.as_view(), name = 'trip-shipment-details'),
    url('^shipment-detail/(?P<shipment>[-\w]+)/$', ShipmentDetail.as_view(), name='shipment-detail'),
    url('^amount-collected/(?P<shipment>\d+)/$', StatusChangedAfterAmountCollected.as_view(), name='amount-collected'),

    #cron
    #url('^delete-ordered-product-reserved/$', CronToDeleteOrderedProductReserved.as_view(), name='delete_ordered_product_reserved'),
    url('^feedback/$', FeedbackData.as_view(), name='feed_back'),
    url('^feedback/(?P<ship_id>\d+)/list/$', FeedbackData.as_view(), name='feed_back_list'),
    url('^cancel-order/$', CancelOrder.as_view(), name='cancel_order', ),
]

urlpatterns += router.urls