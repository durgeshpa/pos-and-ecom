
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from sp_to_gram.models import OrderedProductMapping,OrderedProductReserved


# class CronToDeleteOrderedProductReserved(APIView):
#
#     permission_classes = (AllowAny,)
#
#     def get(self, request):
#         if OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now()).exists():
#             for ordered_reserve in OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now()):
#                 ordered_reserve.order_product_reserved.available_qty = int(ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
#                 ordered_reserve.order_product_reserved.save()
#
#                 # Saving Cart as pending
#                 ordered_reserve.cart.cart_status = 'pending'
#                 ordered_reserve.cart.save()
#
#                 # Deleted Cart
#                 print("%s id will deleted and added %s qty in available_qty of OrderedProductMapping %s id"%(ordered_reserve.id,ordered_reserve.order_product_reserved.available_qty,ordered_reserve.order_product_reserved.id))
#                 ordered_reserve.delete()
#         else:
#             print(OrderedProductReserved.objects.filter(order_reserve_end_time__gt=timezone.now()).query)
#             print("nothing found")

def cron_to_delete_ordered_product_reserved(request):
    if OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now()).exists():
        for ordered_reserve in OrderedProductReserved.objects.filter(order_reserve_end_time__lte=timezone.now()):
            ordered_reserve.order_product_reserved.available_qty = int(ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
            ordered_reserve.order_product_reserved.save()

            # Saving Cart as pending
            ordered_reserve.cart.cart_status = 'pending'
            ordered_reserve.cart.save()

            # Deleted Cart
            print("%s id will deleted and added %s qty in available_qty of OrderedProductMapping %s id"%(ordered_reserve.id,ordered_reserve.order_product_reserved.available_qty,ordered_reserve.order_product_reserved.id))
            ordered_reserve.delete()
    else:
        print(OrderedProductReserved.objects.filter(order_reserve_end_time__gt=timezone.now()).query)
        print("nothing found")