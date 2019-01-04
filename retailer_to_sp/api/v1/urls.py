from django.conf.urls import include, url
from .views import (ProductsList, GramGRNProductsList,AddToCart,CartDetail,ReservedOrder,CreateOrder,OrderList,OrderDetail,DownloadInvoice,
                    DownloadNote, CustomerCareApi, CustomerOrdersList,  PaymentApi, ProductDetail)

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
    url('^download-invoice/(?P<pk>\d+)/invoice/$', DownloadInvoice.as_view(), name='download_invoice'),
    url('^download-note/(?P<pk>\d+)/note/$', DownloadNote.as_view(), name='download_note'),
    url('^customer-care-form/$', CustomerCareApi.as_view(), name='customer_care_form'),
    url('^user-orders/$', CustomerOrdersList.as_view(), name='user_orders'),
    #url('^order-payment-cod/$', PaymentCodApi.as_view(), name='order_payment_cod'),
    url('^order-payment/$', PaymentApi.as_view(), name='order_payment'),
    url('^product_detail/(?P<pk>\d+)/$', ProductDetail.as_view(), name='product_detail'),
    #cron
    #url('^delete-ordered-product-reserved/$', CronToDeleteOrderedProductReserved.as_view(), name='delete_ordered_product_reserved'),
]
