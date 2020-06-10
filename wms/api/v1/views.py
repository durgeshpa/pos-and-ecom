from wms.models import Bin, Putaway, PutawayBinInventory, BinInventory, InventoryType, Out, Pickup, PickupBinInventory
from rest_framework import viewsets
from .serializers import BinSerializer, PutAwaySerializer, OutSerializer, PickupSerializer, OrderSerializer, BinInventorySerializer
from wms.views import pickup_bin_inventory
from rest_framework.response import Response
from rest_framework import status
from shops.models import Shop
from retailer_to_sp.models import Order, PickerDashboard
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import datetime
import json
import random


class BinViewSet(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        ids = self.request.GET.get('id')
        if ids:
            try:
                bins = Bin.objects.get(id=ids)
            except ObjectDoesNotExist:
                msg = {'is_success': False, 'message': ['Does Not Exist'], 'response_data': None}
                return Response(msg, status=status.HTTP_404_NOT_FOUND)
            else:
                serializer = BinSerializer(bins)
                return Response({"bin": serializer.data})
        else:
            bins = Bin.objects.all()
            serializer = BinSerializer(bins, many=True)
            return Response({"bin": serializer.data})

    def post(self, request):
        msg = {'is_success': False, 'message': ['Some Required field empty'], 'response_data': None}
        warehouse = self.request.POST.get('warehouse')
        bin_id = self.request.POST.get('bin_id')
        bin_type = self.request.POST.get('bin_type')
        is_active = self.request.POST.get('is_active')
        if not is_active:
            return Response(msg, status=status.HTTP_204_NO_CONTENT)
        sh = Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type == 'sp':
            bin_data = Bin.objects.create(warehouse=sh, bin_id=bin_id, bin_type=bin_type, is_active=is_active)
            serializer = (BinSerializer(bin_data))
            msg = {'is_success': True, 'message': ['Data added to bin'], 'response_data': serializer.data}
            return Response(msg, status=status.HTTP_201_CREATED)
        msg = ["Shop type must be sp"]
        return Response(msg, status=status.HTTP_200_OK)


class PutAwayViewSet(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        ids = self.request.GET.get('id')
        if ids:
            try:
                put_away = Putaway.objects.get(id=ids)
            except ObjectDoesNotExist:
                msg = {'is_success': False, 'message': ['Does Not Exist'], 'response_data': None}
                return Response(msg, status=status.HTTP_404_NOT_FOUND)
            else:
                serializer = PutAwaySerializer(put_away)
                return Response({"put_away": serializer.data})
        else:
            put_away = Putaway.objects.all()
            serializer = PutAwaySerializer(put_away, many=True)
            return Response({"put_away": serializer.data})

    def post(self, request):
        msg = {'is_success': False, 'message': ['Some Required field empty'], 'response_data': None}
        warehouse = self.request.POST.get('warehouse')
        if not warehouse:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        put_away_quantity = self.request.POST.get('put_away_quantity')
        if not put_away_quantity:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
            batch_id = self.request.POST.get('batch_id')
        if not batch_id:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        bin_id = self.request.POST.get('bin_id')
        if not bin_id:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        inventory_type = self.request.POST.get('inventory_type')
        if not inventory_type:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)

        put_away = Putaway.objects.filter(batch_id=batch_id, warehouse=warehouse)
        if put_away.last().quantity < int(put_away_quantity):
            return Response({'is_success': False, 'message': ['Put_away_quantity should be equal to or'
                                                              ' less than quantity'], 'response_data': None},
                            status=status.HTTP_200_OK)
        bin_skus = PutawayBinInventory.objects.values_list('putaway__sku__product_sku', flat=True)
        sh = Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type == 'sp':
            put_away.update(putaway_quantity=put_away_quantity)
            bin_inventory = BinInventory.objects.filter(bin__bin_id=bin_id)
            if bin_inventory.exists():
                if batch_id in bin_inventory.values_list('batch_id', flat=True):
                    bin_inv = BinInventory.objects.create(warehouse=sh, sku=put_away.last().sku,bin=Bin.objects.filter(bin_id=bin_id).last(), batch_id=batch_id,
                                                          inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(), quantity=put_away_quantity, in_stock='t')
                    PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(),bin=bin_inv,putaway_quantity=put_away_quantity)
                else:
                    if batch_id[:17] in bin_inventory.values_list('sku__product_sku', flat=True):
                        return Response({'is_success': False, 'message': ['This product can not be placed in the bin'], 'response_data': None}, status=status.HTTP_200_OK)
                    else:
                        bin_inv = BinInventory.objects.create(warehouse=sh, sku=put_away.last().sku,
                                                              bin=Bin.objects.filter(bin_id=bin_id).last(),
                                                              batch_id=batch_id,inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(), quantity=put_away_quantity, in_stock='t')
                        PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(), bin=bin_inv,
                                                           putaway_quantity=put_away_quantity)
            else:
                bin_inv = BinInventory.objects.create(warehouse=sh, sku=put_away.last().sku, bin=Bin.objects.filter(bin_id=bin_id).last(),batch_id=batch_id, inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(), quantity=put_away_quantity, in_stock='t')
                PutawayBinInventory.objects.create(warehouse=sh,putaway=put_away.last(), bin=bin_inv,
                                                   putaway_quantity=put_away_quantity)

            serializer = (PutAwaySerializer(Putaway.objects.filter(batch_id=batch_id, warehouse=warehouse).last()))
        msg = {'is_success': True, 'message': ['quantity to be put away updated'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class PutAwayProduct(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """

        :param request:
        :return:
        """
        put_away = Putaway.objects.all()
        serializer = PutAwaySerializer(put_away, many=True, fields=('id', 'batch_id', 'sku', 'product_sku'))
        return Response({"put_away": serializer.data})


class PickupList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        date = ''.join(self.request.GET.get('date')).split('-0')
        date = [int(i) for i in date]
        picker_boy = self.request.GET.get('picker_boy')
        orders = Order.objects.filter(Q(picker_order__picker_boy__first_name=picker_boy),
                                      Q(picker_order__picking_status='picking_assigned'),
                                      Q(created_at__startswith=datetime.date(date[0], date[1], date[2])))

        serializer = OrderSerializer(orders, many=True)
        return Response({'orders': serializer.data})


class BinIDList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        order_no = self.request.POST.get('order_no')
        bin_objects=[]
        quantity=[]
        pickup_orders = Order.objects.filter(order_no=order_no).last()
        for i in pickup_orders.ordered_cart.rt_cart_list.all():
            for j in i.cart_product.rt_product_sku.filter(quantity__gt=0).order_by('-batch_id', '-quantity'):
                bin_objects.append(j.bin.bin_id)

        bin_lists = Bin.objects.filter(bin_id__in=bin_objects)

        serializer = BinSerializer(bin_lists, many=True,fields=('id', 'bin_id'))
        return Response({'Bins_list': serializer.data})


# class PickupDetail(APIView):
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def post(self, request):
#         bin_id = self.request.POST.get('bin_id')
#         order_no = self.request.POST.get('order_no')
#         picking = Pickup.objects.filter(pickup_type_id=order_no,sku__rt_product_sku__bin__bin_id=bin_id)
#         picking_details = picking.last()
#         pickup_quantity = int(self.request.POST.get('pickup_quantity'))
#         if pickup_quantity > picking_details.quantity:
#             msg = {'is_success': False, 'message': ['Picked_quantity cannot be greater than to be picked quantity'], 'response_data': None}
#             return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
#         else:
#             picking.update(pickup_quantity=pickup_quantity)
#         get_batch = picking_details.sku.rt_product_sku.filter(quantity__gt=0).order_by('-batch_id', '-quantity').last()
#         batch_id = get_batch.batch_id if get_batch else None
#         id = get_batch.id if get_batch else 0
#         bin = get_batch if get_batch else None
#         bin_inventory = BinInventory.objects.filter(batch_id=batch_id, id=id)
#         quantity = bin_inventory.last().quantity
#         if quantity-pickup_quantity >=0:
#             bin_inventory.update(quantity=(quantity - pickup_quantity))
#
#         else:
#             bin_inventory.update(quantity=0)
#
#         PickupBinInventory.objects.create(warehouse=picking_details.warehouse,pickup=picking_details,batch_id=batch_id, bin=bin, pickup_quantity=pickup_quantity)
#
#
#         serializer = PickupSerializer(picking_details,fields=('id','batch_id_with_sku','quantity', 'pickup_quantity'))
#         return Response({'picking_details' : serializer.data})

class PickupDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        bin_id = self.request.POST.get('bin_id')
        order_no = self.request.POST.get('order_no')
        pickup_quantity = int(self.request.POST.get('pickup_quantity'))
        pickup_bin_inventory(bin_id, order_no, pickup_quantity)
        picking_details = Pickup.objects.filter(pickup_type_id=order_no)
        bin_inv = BinInventory.objects.filter(bin__bin_id=bin_id, quantity__gt=0).order_by('-batch_id', '-quantity').last()
        batch_id=bin_inv.batch_id if bin_inv else None
        for i in picking_details:
            PickupBinInventory.objects.create(warehouse=i.warehouse,pickup=i,batch_id=batch_id, bin=bin_inv, pickup_quantity=pickup_quantity)

        serializer = PickupSerializer(picking_details, many=True,fields=('id','batch_id_with_sku','quantity', 'pickup_quantity'))
        return Response({'picking_details' : serializer.data})















