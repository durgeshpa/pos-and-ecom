from django.utils import timezone
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

import sp_to_gram
from sp_to_gram.models import OrderedProductMapping, OrderedProductReserved
from retailer_to_sp.api.v1.views import refresh_cron_es
from gram_to_brand.models import OrderedProductReserved as GramOrderedProductReserved
from django.db.models import Sum, Q, Case, CharField, Value, When, F
from shops.models import Shop, ShopType
from gram_to_brand.models import Cart
from services.models import ShopStock
from retailer_to_sp.models import Order
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)
cron_logger = logging.getLogger('cron_log')


class CronToDeleteOrderedProductReserved(APIView):
    permission_classes = (AllowAny,)
#   # used in API not cron job
    def get(self, request):
        reserved_orders = OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),
                                                                reserve_status='reserved')
        if reserved_orders.count():
            reserved_orders.update(reserve_status='clearing')
            reserved_orders = OrderedProductReserved.objects.filter(reserve_status='clearing')
            for ro in reserved_orders:
                ro.order_product_reserved.available_qty = int(ro.order_product_reserved.available_qty) + int(
                    ro.reserved_qty)
                ro.order_product_reserved.save()
                ro.cart.cart_status = 'pending'
                ro.cart.save()
                ro.reserve_status = 'free'
                ro.save()
        return Response()


def delete_ordered_reserved_products():
    reserved_orders = OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),
                                                            reserve_status='reserved')
    if reserved_orders.count():
        reserved_orders.update(reserve_status='clearing')
        reserved_orders = OrderedProductReserved.objects.filter(reserve_status='clearing')
        for ro in reserved_orders:
            ro.order_product_reserved.available_qty = int(ro.order_product_reserved.available_qty) + int(
                ro.reserved_qty)
            ro.order_product_reserved.save()
            ro.cart.cart_status = 'pending'
            ro.cart.save()
            ro.reserve_status = 'free'
            ro.save()


# def cron_to_delete_ordered_product_reserved(request):
#     if OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),
#                                              reserve_status='reserved').exists():
#         for ordered_reserve in OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),
#                                                                      reserve_status='reserved'):
#             ordered_reserve.order_product_reserved.available_qty = int(
#                 ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
#             ordered_reserve.order_product_reserved.save()
#
#             # Saving Cart as pending
#             ordered_reserve.cart.cart_status = 'pending'
#             ordered_reserve.cart.save()
#
#             # Deleted Cart
#             # ordered_reserve.delete()
#             ordered_reserve.reserve_status = 'free'
#             ordered_reserve.save()
#
#     if GramOrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),
#                                                  reserve_status='reserved').exists():
#         for ordered_reserve in GramOrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),
#                                                                          reserve_status='reserved'):
#             ordered_reserve.order_product_reserved.available_qty = int(
#                 ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
#             ordered_reserve.order_product_reserved.save()
#
#             # Saving Cart as pending
#             ordered_reserve.cart.cart_status = 'pending'
#             ordered_reserve.cart.save()
#
#             # Deleted Cart
#
#             ordered_reserve.reserve_status = 'free'
#             ordered_reserve.save()


class DailyStock(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        for shop_obj in Shop.objects.filter(shop_type__shop_type='sp', shop_name__icontains='GFDN'):
            sp_grn_product = OrderedProductMapping.get_shop_stock(shop_obj)
            product_sum = sp_grn_product.values('product', 'product__product_name', 'product__product_gf_code',
                                                'product__product_sku').annotate(
                product_qty_sum=Sum('available_qty')).annotate(damaged_qty_sum=Sum('damaged_qty'))
            daily_stock_dt = []
            for product_dt in product_sum:
                daily_stock_dt.append(
                    ShopStock(product_id=product_dt['product'], available_qty=product_dt['product_qty_sum'],
                              damage_qty=product_dt['damaged_qty_sum'], shop_id=shop_obj.id, created_at=datetime.now()))
        for shop_obj in Shop.objects.filter(shop_type__shop_type='sp', shop_name__icontains='ADDISTRO'):
            sp_grn_product = OrderedProductMapping.get_shop_stock(shop_obj)
            product_sum = sp_grn_product.values('product', 'product__product_name', 'product__product_gf_code',
                                                    'product__product_sku').annotate(
                product_qty_sum=Sum('available_qty')).annotate(damaged_qty_sum=Sum('damaged_qty'))
            daily_stock_dt = []
            for product_dt in product_sum:
                daily_stock_dt.append(
                    ShopStock(product_id=product_dt['product'], available_qty=product_dt['product_qty_sum'],
                              damage_qty=product_dt['damaged_qty_sum'], shop_id=shop_obj.id,
                              created_at=datetime.now()))


def discounted_order_cancellation():
    orders = Order.objects.filter(
        ~Q(order_status='CANCELLED'),
        created_at__lt=(datetime.now() - timedelta(hours=24)),
        ordered_cart__cart_type='DISCOUNTED',
        ordered_cart__approval_status=False)
    if orders.exists():
        for order in orders:
            order.order_status = 'CANCELLED'
            order.save()


def po_status_change_exceeds_validity_date():
    queryset = Cart.objects.filter(
        Q(po_status=Cart.OPEN) | Q(po_status=Cart.FINANCE_APPROVED) |
        Q(po_status=Cart.APPROVAL_AWAITED) | Q(po_status=Cart.PARTIAL_DELIVERED),
        po_validity_date__lt=timezone.now())
    if queryset.exists():
        queryset.update(po_status=Case(
            When((Q(po_status=Cart.OPEN) | Q(po_status=Cart.APPROVAL_AWAITED) |
                  Q(po_status=Cart.FINANCE_APPROVED)),
                 then=Value(Cart.CLOSE)),
            When(po_status=Cart.PARTIAL_DELIVERED,
                 then=Value(Cart.PARTIAL_DELIVERED_CLOSE)),
            default=F('po_status')))

def sync_es_products():
    sp_shop_type = ShopType.objects.all().filter(shop_type="sp").last()
    shop_list = Shop.objects.filter(shop_type=sp_shop_type).all()
    for shop in shop_list:
        logger.info("sync shop: %s", shop)
        cron_logger.info('sync_es_products started for Shop {} '.format(shop))
        sp_to_gram.tasks.upload_shop_stock(shop.pk)
        cron_logger.info('sync_es_products ended for Shop {} '.format(shop))
        logger.info("sleep 10")
        time.sleep(10)
