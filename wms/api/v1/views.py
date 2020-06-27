from wms.models import Bin, Putaway, PutawayBinInventory, BinInventory, InventoryType, Pickup
from .serializers import BinSerializer, PutAwaySerializer, PickupSerializer, OrderSerializer
from wms.views import PickupInventoryManagement, update_putaway
from rest_framework.response import Response
from rest_framework import status
from shops.models import Shop
from retailer_to_sp.models import Order
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Sum
import datetime
import logging

logging.basicConfig(filename="newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='a')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class BinViewSet(APIView):
    """
    This class is used to get Bin Information and create Bin in database
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """

        :param request: Get request
        :return: Bin Data
        """
        ids = request.GET.get('id')

        if ids:
            try:
                bins = Bin.objects.get(id=ids)
            except ObjectDoesNotExist as e:
                logging.exception(e, exc_info=True)
                msg = {'is_success': False, 'message': "Bin id doesn't exist", 'data': None}
                return Response(msg, status=status.HTTP_404_NOT_FOUND)
            else:
                serializer = BinSerializer(bins)
                return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)
        else:
            bins = Bin.objects.all()
            serializer = BinSerializer(bins, many=True)
            logging.debug(serializer.data)

            return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)

    def post(self, request):
        """

        :param request: Post request
        :return: Bin Data
        """
        msg = {'is_success': False, 'message': 'Some Required field empty', 'data': None}
        warehouse = request.POST.get('warehouse')
        bin_id = request.POST.get('bin_id')
        bin_type = request.POST.get('bin_type')
        is_active = request.POST.get('is_active')
        if not is_active:
            return Response(msg, status=status.HTTP_204_NO_CONTENT)
        sh = Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type == 'sp':
            bin_data = Bin.objects.create(warehouse=sh, bin_id=bin_id, bin_type=bin_type, is_active=is_active)
            serializer = (BinSerializer(bin_data))
            msg = {'is_success': True, 'message': 'Bin data added successfully.', 'data': serializer.data}
            return Response(msg, status=status.HTTP_201_CREATED)
        msg = "Shop type must be sp"
        return Response(msg, status=status.HTTP_200_OK)


class PutAwayViewSet(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):

        batch_id = request.GET.get('batch_id')

        if batch_id:
            put_away = Putaway.objects.filter(batch_id=batch_id)
            if put_away.exists():
                serializer = PutAwaySerializer(put_away.last(), fields=('is_success', 'product_sku', 'batch_id', 'grned_quantity', 'put_away_quantity'))
                msg = {'is_success': True, 'message': 'Putaway details', 'data': serializer.data}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False, 'message': 'Put Away batch_id does not exist', 'data': None}
                return Response(msg, status=status.HTTP_404_NOT_FOUND)
        else:
            put_away = Putaway.objects.all()
            serializer = PutAwaySerializer(put_away, many=True, fields=('is_success', 'product_sku', 'batch_id', 'grned_quantity', 'put_away_quantity'))
            msg = {'is_success': True, 'message': 'Putaway details', 'data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        data, key ={}, 0
        lis_data = []
        msg = {'is_success': False, 'message': 'Some Required field empty', 'data': None}
        bin_id = self.request.data.get('bin_id')
        if not bin_id:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        try:
            warehouse = Bin.objects.filter(bin_id=bin_id).last().warehouse.id
        except Exception as e:
            logging.exception(e, exc_info=True)
            return Response({'is_success': False,
                             'message': 'Bin id does not exist.',
                             'data': None}, status=status.HTTP_400_BAD_REQUEST)
        put_away_quantity = self.request.data.get('put_away_quantity')
        if not put_away_quantity:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        negative_value = [i for i in put_away_quantity if i<0]
        if len(negative_value) > 0:
            return Response({'is_success': False,
                             'message': 'Put away quantity can not be negative.',
                             'data': None}, status=status.HTTP_400_BAD_REQUEST)
        batch_id = self.request.data.get('batch_id')
        if not batch_id:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        inventory_type = 'normal'

        if len(batch_id) != len(put_away_quantity):
            
            return Response({'is_success': False, 'message': 'The number of batches entered should be equal to number of qty entered', 'data': None}, status=status.HTTP_400_BAD_REQUEST)
        diction = {i[0]: i[1] for i in zip(batch_id, put_away_quantity)}
        for i, value in diction.items():
            key+=1
            put_away = Putaway.objects.filter(batch_id=i, warehouse=warehouse).order_by('created_at')
            ids = [i.id for i in put_away]
            updated_putaway_value = put_away.aggregate(total=Sum('putaway_quantity'))['total'] if put_away.aggregate(total=Sum('putaway_quantity'))['total'] else 0
            try:
                updated_putaway_value = put_away.aggregate(total=Sum('quantity'))['total'] if updated_putaway_value>put_away.aggregate(total=Sum('quantity'))['total'] else updated_putaway_value
                if updated_putaway_value + int(value)>put_away.aggregate(total=Sum('quantity'))['total']:
                    value = put_away.aggregate(total=Sum('quantity'))['total'] - updated_putaway_value
                if updated_putaway_value == put_away.aggregate(total=Sum('quantity'))['total']:
                    value = 0
                    msg = {'is_success':False, "message":"Complete, for batch_id {} Can't add more items".format(i), 'batch_id':i}
                    lis_data.append(msg)
                    continue
            except Exception as e:
                logging.exception(e, exc_info=True)
                return Response({'is_success': False,
                                 'message': 'Batch id does not exist.',
                                 'data': None}, status=status.HTTP_400_BAD_REQUEST)
            if put_away.aggregate(total=Sum('quantity'))['total'] < int(value):
                msg ={'is_success':False, 'message':'Put_away_quantity for batch_id {} should be equal to or less than quantity'.format(i), 'batch_id':i}
                lis_data.append(msg)
                continue


            bin_skus = PutawayBinInventory.objects.values_list('putaway__sku__product_sku', flat=True)
            sh = Shop.objects.filter(id=int(warehouse)).last()
            if sh.shop_type.shop_type == 'sp':
                bin_inventory = BinInventory.objects.filter(bin__bin_id=bin_id)
                if bin_inventory.exists():
                    if i in bin_inventory.values_list('batch_id', flat=True):
                        bin_inv = BinInventory.objects.create(warehouse=sh, sku=put_away.last().sku,bin=Bin.objects.filter(bin_id=bin_id).last(), batch_id=i,
                                                              inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(), quantity=value, in_stock='t')
                        PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(),bin=bin_inv,putaway_quantity=value)
                        while len(ids):
                            put_away_done = update_putaway(ids[0], i, warehouse, int(value))
                            value = put_away_done
                            ids.remove(ids[0])
                    else:
                        if i[:17] in bin_inventory.values_list('sku__product_sku', flat=True):
                            msg ={'is_success':False,'Putaway':'This product with sku {} and batch_id {} can not be placed in the bin'.format(i[:17], i),'batch_id':i}
                            lis_data.append(msg)
                            continue

                        else:
                            bin_inv = BinInventory.objects.create(warehouse=sh, sku=put_away.last().sku,
                                                                  bin=Bin.objects.filter(bin_id=bin_id).last(),
                                                                  batch_id=i,inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(), quantity=value, in_stock='t')
                            PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(), bin=bin_inv,
                                                               putaway_quantity=value)
                            while len(ids):
                                update_putaway(ids[0], i, warehouse, int(value))
                                ids.remove(ids[0])
                else:
                    bin_inv = BinInventory.objects.create(warehouse=sh, sku=put_away.last().sku, bin=Bin.objects.filter(bin_id=bin_id).last(),batch_id=i, inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(), quantity=value, in_stock='t')
                    PutawayBinInventory.objects.create(warehouse=sh,putaway=put_away.last(), bin=bin_inv,
                                                       putaway_quantity=value)
                    while len(ids):
                        update_putaway(ids[0], i, warehouse, int(value))
                        ids.remove(ids[0])

            serializer = (PutAwaySerializer(Putaway.objects.filter(batch_id=i, warehouse=warehouse).last(), fields=('is_success', 'product_sku', 'batch_id', 'grned_quantity', 'put_away_quantity')))
            msg = serializer.data
            lis_data.append(msg)
        if len(lis_data)==len(batch_id):
            data.update({'is_success': True, 'message': "quantity to be put away updated", 'data': lis_data})
            return Response(data, status=status.HTTP_200_OK)
        else:
            data.update({'is_success': True, 'message' : "quantity to be put away updated", 'data' : lis_data})
            return Response(data, status=status.HTTP_200_OK)


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
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class PickupList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        msg = {'is_success': False, 'message': 'Some Required field empty', 'data': None}
        if not request.GET.get('date'):
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        picker_boy = request.GET.get('picker_boy')
        if not picker_boy:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        try:
            date = datetime.datetime.strptime(request.GET.get('date'), "%Y-%m-%d")
        except Exception as e:
            logging.exception(e, exc_info=True)
            logging.info(e)
            msg = {'is_success': False, 'message': 'date format is not correct, It should be YYYY-mm-dd', 'data': None}
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        picker_boy = request.GET.get('picker_boy')
        orders = Order.objects.filter(Q(picker_order__picker_boy__phone_number=picker_boy),
                                      Q(picker_order__picking_status='picking_assigned'),
                                      Q(created_at__startswith=date.date()))

        if not orders:
            msg = {'is_success': False, 'message': 'No data found.', 'data': None}
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        else:
            serializer = OrderSerializer(orders, many=True)
            msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)


class BinIDList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        order_no = request.GET.get('order_no')
        if not order_no:
            msg = {'is_success': True, 'message': 'Order number field is empty.', 'data': None}
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        bin_objects = []
        pickup_orders = Order.objects.filter(order_no=order_no).last()
        if pickup_orders is None:
            msg = {'is_success': True, 'message': 'Order number does not exist.', 'data': None}
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        else:
            for i in pickup_orders.ordered_cart.rt_cart_list.all():
                for j in i.cart_product.rt_product_sku.filter(quantity__gt=0).order_by('-batch_id', '-quantity'):
                    bin_objects.append(j.bin.bin_id)

            bin_lists = Bin.objects.filter(bin_id__in=bin_objects)

            serializer = BinSerializer(bin_lists, many=True, fields=('id', 'bin_id'))
            msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)


pickup = PickupInventoryManagement()


class PickupDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        order_no = request.GET.get('order_no')
        if not order_no:
            msg = {'is_success': True, 'message': 'Order number field is empty.', 'data': None}
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        pickup_orders = Order.objects.filter(order_no=order_no).last()
        if pickup_orders is None:
            msg = {'is_success': True, 'message': 'Order number does not exist.', 'data': None}
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        sku_list = []
        for i in pickup_orders.ordered_cart.rt_cart_list.all():
            sku_list.append(i.cart_product.id)
        picking_details = Pickup.objects.filter(pickup_type_id=order_no, sku__id__in=sku_list)

        serializer = PickupSerializer(
            picking_details, many=True, fields=('id', 'batch_id_with_sku', 'product_mrp', 'quantity', 'sku_id'))
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        msg = {'is_success': False, 'message': 'Missing Required field', 'data': None}
        bin_id = request.data.get('bin_id')
        if not bin_id:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        order_no = request.data.get('order_no')
        if not order_no:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        pickup_quantity = request.data.get('pickup_quantity')
        if not pickup_quantity:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        negative_value = [i for i in pickup_quantity if i < 0]
        if len(negative_value) > 0:
            return Response({'is_success': False,
                             'message': 'Pickup quantity can not be negative.',
                             'data': None}, status=status.HTTP_400_BAD_REQUEST)

        sku_id = request.data.get('sku_id')
        if not sku_id:
            return Response(msg, status=status.HTTP_404_NOT_FOUND)
        pick_data = pickup.pickup_bin_inventory(bin_id, order_no, pickup_quantity, sku_id)
        if pick_data == 0:
            return Response({'is_success': False,
                             'message': 'Order number is not valid.',
                             'data': None}, status=status.HTTP_400_BAD_REQUEST)
        if pick_data == 1:
            return Response({'is_success': False,
                             'message': 'Bin/SKU id is not valid.',
                             'data': None}, status=status.HTTP_400_BAD_REQUEST)
        for i in [i['sku_id'] for i in pick_data]:
            if i in sku_id:
                sku_id.remove(i)
        picking_details = Pickup.objects.filter(pickup_type_id=order_no, sku__id__in=sku_id)
        bin_inv = BinInventory.objects.filter(bin__bin_id=bin_id, quantity__gt=0).order_by('-batch_id',
                                                                                           '-quantity').last()
        serializer = PickupSerializer(picking_details, many=True, fields=('id', 'batch_id_with_sku', 'product_mrp',
                                                                          'quantity', 'pickup_quantity', 'sku_id',
                                                                          'is_success'))
        msg = {'is_success': True, 'message': 'Pick up data saved successfully.',
               'data': serializer.data, 'pick_data': pick_data}
        msg['data'].extend(msg['pick_data'])
        del msg['pick_data']
        return Response(msg, status=status.HTTP_200_OK)
