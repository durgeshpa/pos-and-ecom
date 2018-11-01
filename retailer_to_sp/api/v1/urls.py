from django.conf.urls import include, url
from .views import (ProductsList, GramGRNProductsList,AddToCart,CartDetail,ReservedOrder,CreateOrder,OrderList,OrderDetail,DownloadInvoice,
                    CronToDeleteOrderedProductReserved,DownloadNote)

urlpatterns = [
    url('^search/(?P<product_name>.+)/$', ProductsList.as_view()),
    url('^GRN/search/$', GramGRNProductsList.as_view()),
    #order Api
    url('^add-to-cart/$', AddToCart.as_view(), name='add_to_cart'),
    url('^cart-detail/$', CartDetail.as_view(), name='cart_detail'),
    url('^reserved-order/$', ReservedOrder.as_view(), name='reserved_order'),
    url('^create-order/(?P<cart_id>\d+)/$', CreateOrder.as_view(), name='reserved_order'),
    url('^order-list/$', OrderList.as_view(), name='order_list'),
    url('^order-detail/(?P<pk>\d+)/$', OrderDetail.as_view(), name='order_detail'),
    url('^download-invoice/(?P<pk>\d+)/invoice/$', DownloadInvoice.as_view(), name='download_invoice'),
    url('^download-note/(?P<pk>\d+)/note/$', DownloadNote.as_view(), name='download_note'),

    #cron
    url('^delete-ordered-product-reserved/$', CronToDeleteOrderedProductReserved.as_view(), name='delete_ordered_product_reserved'),
]
