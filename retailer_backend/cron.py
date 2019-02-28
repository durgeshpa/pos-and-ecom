
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from sp_to_gram.models import OrderedProductMapping,OrderedProductReserved
from gram_to_brand.models import OrderedProductReserved as GramOrderedProductReserved


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