
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from sp_to_gram.models import OrderedProductMapping,OrderedProductReserved
from gram_to_brand.models import OrderedProductReserved as GramOrderedProductReserved
from django.db.models import Sum,Q
from shops.models import Shop
from services.models import ShopStock
from datetime import datetime

class CronToDeleteOrderedProductReserved(APIView):

    permission_classes = (AllowAny,)

    def get(self, request):
        if OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved').exists():
            for ordered_reserve in OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved'):
                ordered_reserve.order_product_reserved.available_qty = int(ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
                ordered_reserve.order_product_reserved.save()

                # Saving Cart as pending
                ordered_reserve.cart.cart_status = 'pending'
                ordered_reserve.cart.save()

                # Deleted Cart
                ordered_reserve.reserve_status = 'free'
                ordered_reserve.save()

        if GramOrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved').exists():
            for ordered_reserve in GramOrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved'):
                ordered_reserve.order_product_reserved.available_qty = int(ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
                ordered_reserve.order_product_reserved.save()

                # Saving Cart as pending
                ordered_reserve.cart.cart_status = 'pending'
                ordered_reserve.cart.save()

                # Deleted Cart
                ordered_reserve.reserve_status = 'free'
                ordered_reserve.save()
        return Response()

def cron_to_delete_ordered_product_reserved(request):
    if OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved').exists():
        for ordered_reserve in OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved'):
            ordered_reserve.order_product_reserved.available_qty = int(ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
            ordered_reserve.order_product_reserved.save()

            # Saving Cart as pending
            ordered_reserve.cart.cart_status = 'pending'
            ordered_reserve.cart.save()

            # Deleted Cart
            #ordered_reserve.delete()
            ordered_reserve.reserve_status = 'free'
            ordered_reserve.save()

    if GramOrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved').exists():
        for ordered_reserve in GramOrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now(),reserve_status='reserved'):
            ordered_reserve.order_product_reserved.available_qty = int(
                ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
            ordered_reserve.order_product_reserved.save()

            # Saving Cart as pending
            ordered_reserve.cart.cart_status = 'pending'
            ordered_reserve.cart.save()

            # Deleted Cart

            ordered_reserve.reserve_status = 'free'
            ordered_reserve.save()

class DailyStock(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        for shop_obj in Shop.objects.filter(shop_type__shop_type='sp'):
            sp_grn_product = OrderedProductMapping.get_shop_stock(shop_obj)
            product_sum = sp_grn_product.values('product', 'product__product_name', 'product__product_gf_code','product__product_sku').annotate(
                product_qty_sum=Sum('available_qty')).annotate(damaged_qty_sum=Sum('damaged_qty'))

            for product_dt in product_sum:
                ShopStock.objects.using('gfanalytics').create(product_id=product_dt['product'], available_qty=product_dt['product_qty_sum'],
                damage_qty=product_dt['damaged_qty_sum'], shop_id=shop_obj.id, created_at=datetime.now())
