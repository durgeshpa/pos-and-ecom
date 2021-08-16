import json
import logging

from django.utils import timezone
from model_utils import Choices

from retailer_backend.messages import ERROR_MESSAGES
from wms.models import Bin, Putaway, PutawayBinInventory, BinInventory, InventoryType, Pickup, InventoryState, \
    PickupBinInventory, StockMovementCSVUpload, In
from products.models import Product
from .serializers import BinSerializer, PutAwaySerializer, PickupSerializer, OrderSerializer, \
    PickupBinInventorySerializer, RepackagingSerializer, BinInventorySerializer
from wms.views import PickupInventoryManagement, update_putaway
from rest_framework.response import Response
from rest_framework import status
from shops.models import Shop
from products.models import Repackaging
from retailer_to_sp.models import Order, PickerDashboard
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Sum
from django.db import transaction
from gram_to_brand.models import GRNOrderProductMapping
import datetime
from wms.common_functions import (CommonBinInventoryFunctions, PutawayCommonFunctions, CommonBinFunctions,
                                  CommonWarehouseInventoryFunctions as CWIF, CommonInventoryStateFunctions as CISF,
                                  CommonBinInventoryFunctions as CBIF, updating_tables_on_putaway,
                                  CommonWarehouseInventoryFunctions, InternalInventoryChange)

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class CheckBinID(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        msg = {'is_success': False, 'message': 'Missing Required field.', 'data': ""}
        bin_id = request.GET.get('bin_id')
        if not bin_id:
            return Response(msg, status=status.HTTP_200_OK)
        bins = CommonBinFunctions.get_filtered_bins(bin_id=bin_id, is_active=True)
        if bins.exists():
            msg = {'is_success': True, 'message': "Bin id exists.", 'data': ""}
            return Response(msg, status=status.HTTP_200_OK)
        else:
            msg = {'is_success': False, 'message': "Bin id is not activated.", 'data': ""}
            return Response(msg, status=status.HTTP_200_OK)


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
        info_logger.info("Bin View GET api called.")
        ids = request.GET.get('id')

        if ids:
            try:
                bins = CommonBinFunctions.get_filtered_bins(id=ids)
            except ObjectDoesNotExist as e:
                error_logger.error(e)
                msg = {'is_success': False, 'message': "Bin id doesn't exist.", 'data': None}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                serializer = BinSerializer(bins, many=True)
                return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)
        else:
            bins = CommonBinFunctions.get_filtered_bins()
            serializer = BinSerializer(bins, many=True)
            return Response({"data": serializer.data, "message": "OK"}, status=status.HTTP_200_OK)

    def post(self, request):
        """

        :param request: Post request
        :return: Bin Data
        """
        info_logger.info("Bin View POST api called.")
        msg = {'is_success': False, 'message': 'Some Required field empty.', 'data': None}
        warehouse = request.POST.get('warehouse')
        bin_id = request.POST.get('bin_id')
        bin_type = request.POST.get('bin_type')
        is_active = request.POST.get('is_active')
        if not is_active:
            return Response(msg, status=status.HTTP_204_NO_CONTENT)
        sh = Shop.objects.filter(id=int(warehouse)).last()
        if sh.shop_type.shop_type == 'sp':
            bin_data = CommonBinFunctions.create_bin(sh, bin_id, bin_type, is_active)
            serializer = (BinSerializer(bin_data))
            msg = {'is_success': True, 'message': 'Bin data added successfully.', 'data': serializer.data}
            return Response(msg, status=status.HTTP_201_CREATED)
        msg = "Shop type must be sp"
        return Response(msg, status=status.HTTP_200_OK)


class PutAwayViewSet(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        info_logger.info("Put Away View GET api called.")
        batch_id = request.GET.get('batch_id')
        try:
            warehouse = request.user.shop_employee.all().last().shop_id

        except Exception as e:
            error_logger.error(e)
            return Response({'is_success': False,
                             'message': 'User is not mapped with associated Warehouse.',
                             'data': None}, status=status.HTTP_200_OK)

        # putaway_type = request.GET.get('type')
        # if putaway_type:
        #     putaway_type = int(putaway_type)
        # if putaway_type not in [1, 2]:
        #     msg = {'is_success': False, 'message': 'Please provide a valid type', 'data': None}
        #     return Response(msg, status=status.HTTP_200_OK)

        if batch_id:
            type_normal = InventoryType.objects.filter(inventory_type='normal').last()
            put_away = PutawayCommonFunctions.get_filtered_putaways(batch_id=batch_id, warehouse=warehouse,
                                                                    inventory_type=type_normal).order_by('created_at')
            if put_away.exists():
                put_away_last = put_away.last()
                put_away_serializer = PutAwaySerializer(put_away_last, fields=(
                    'is_success', 'product_sku', 'batch_id', 'product_name', 'inventory_type', 'putaway_quantity', 'max_putaway_qty'))
                data = put_away_serializer.data
                bin_inventory = BinInventory.objects.filter(warehouse=warehouse, sku=put_away_last.sku,
                                                            inventory_type__inventory_type='normal')
                if bin_inventory.exists():
                    bin_inventory_serializer = BinInventorySerializer(bin_inventory, many=True)
                    data['sku_bin_inventory'] = bin_inventory_serializer.data
                msg = {'is_success': True, 'message': 'OK', 'data': data}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False, 'message': 'Batch id does not exist.', 'data': None}
                return Response(msg, status=status.HTTP_200_OK)
        else:
            put_away = PutawayCommonFunctions.get_filtered_putaways()
            serializer = PutAwaySerializer(put_away, many=True, fields=(
                'is_success', 'product_sku', 'batch_id', 'product_name', 'putaway_quantity', 'max_putaway_qty'))
            msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
            return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        info_logger.info("Put Away View POST api called.")
        data, key = {}, 0
        lis_data = []
        try:
            warehouse = request.user.shop_employee.all().last().shop_id
        except Exception as e:
            error_logger.error(e)
            return Response({'is_success': False,
                             'message': 'User is not mapped with associated Warehouse.',
                             'data': None}, status=status.HTTP_200_OK)
        msg = {'is_success': False, 'message': 'Some Required field empty.', 'data': None}
        bin_id = self.request.data.get('bin_id')
        if not bin_id:
            return Response(msg, status=status.HTTP_200_OK)
        bin_obj = Bin.objects.filter(bin_id=bin_id, is_active=True)
        if not bin_obj:
            msg = {'is_success': False, 'message': "Bin id is not activated.", 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        bin_ware_obj = Bin.objects.filter(bin_id=bin_id, is_active=True, warehouse=warehouse)
        if not bin_ware_obj:
            msg = {'is_success': False, 'message': "Bin id is not associated with the user's warehouse.", 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        put_away_quantity = self.request.data.get('put_away_quantity')
        if not put_away_quantity:
            return Response(msg, status=status.HTTP_200_OK)
        negative_value = [i for i in put_away_quantity if i <= 0]
        if len(negative_value) > 0:
            return Response({'is_success': False,
                             'message': 'quantity can not be zero and negative.',
                             'data': None}, status=status.HTTP_200_OK)
        batch_id = self.request.data.get('batch_id')
        if not batch_id:
            return Response(msg, status=status.HTTP_200_OK)
        inventory_type = 'normal'
        type_normal = InventoryType.objects.filter(inventory_type=inventory_type).last()
        if len(batch_id) != len(put_away_quantity):
            return Response({'is_success': False,
                             'message': 'The number of batches entered should be equal to number of qty entered.',
                             'data': None}, status=status.HTTP_200_OK)
        diction = {i[0]: i[1] for i in zip(batch_id, put_away_quantity)}
        for i, value in diction.items():
            key += 1
            val = value
            put_away_rep = PutawayCommonFunctions.get_filtered_putaways(batch_id=i, warehouse=warehouse,
                                                                        putaway_type='REPACKAGING',
                                                                        inventory_type=type_normal)
            if put_away_rep.count() > 0:
                msg = {'is_success': False, "message": "Putaway for batch_id {} is for repackaging.".format(i),
                       'batch_id': i}
                lis_data.append(msg)
                continue
            put_away = PutawayCommonFunctions.get_filtered_putaways(batch_id=i, warehouse=warehouse,
                                                                    putaway_type='GRN',
                                                                    inventory_type=type_normal).order_by('created_at')
            ids = [i.id for i in put_away]
            updated_putaway_value = put_away.aggregate(total=Sum('putaway_quantity'))['total'] if \
                put_away.aggregate(total=Sum('putaway_quantity'))['total'] else 0
            try:
                updated_putaway_value = put_away.aggregate(total=Sum('quantity'))['total'] if updated_putaway_value > \
                                                                                              put_away.aggregate(
                                                                                                  total=Sum(
                                                                                                      'quantity'))[
                                                                                                  'total'] else updated_putaway_value
                if updated_putaway_value + int(value) > put_away.aggregate(total=Sum('quantity'))['total']:
                    msg = {'is_success': False, "message": "Put away quantity is exceeded for batch_id {} Can't "
                                                           "add more items".format(i),
                           'batch_id': i}
                    lis_data.append(msg)
                    continue
                if updated_putaway_value + int(value) <= put_away.aggregate(total=Sum('quantity'))['total']:
                    value = val
                if updated_putaway_value == put_away.aggregate(total=Sum('quantity'))['total']:
                    value = 0
                    msg = {'is_success': False, "message": "Complete, for batch_id {} Can't add more items".format(i),
                           'batch_id': i}
                    lis_data.append(msg)
                    continue
            except Exception as e:
                error_logger.error(e)
                return Response({'is_success': False,
                                 'message': 'Batch id does not exist.',
                                 'data': None}, status=status.HTTP_200_OK)
            if put_away.aggregate(total=Sum('quantity'))['total'] < int(value):
                msg = {'is_success': False,
                       'message': 'Put_away_quantity for batch_id {} should be equal to or less than quantity.'.format(
                           i), 'batch_id': i}
                lis_data.append(msg)
                continue

            bin_skus = PutawayBinInventory.objects.values_list('putaway__sku__product_sku', flat=True)
            sh = Shop.objects.filter(id=int(warehouse)).last()
            state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
            if sh.shop_type.shop_type == 'sp':
                # Get the Bin Inventory for concerned SKU and Bin excluding the current batch id
                # if BinInventory exists, check if total inventory is zero, this includes items yet to be picked
                # if inventory is more than zero, putaway won't be allowed, else putaway will be done
                product = Product.objects.filter(product_sku=i[:17]).last()
                discounted_product = product.discounted_sku
                if not discounted_product:
                    bin_inventory = CommonBinInventoryFunctions.get_filtered_bin_inventory(sku=i[:17], bin__bin_id=bin_id)\
                                                               .exclude(batch_id=i)
                else:

                    bin_inventory = CommonBinInventoryFunctions.get_filtered_bin_inventory(
                                                                        sku__id__in=[product.id, discounted_product.id],
                                                                        bin__bin_id=bin_id)\
                                                               .exclude(batch_id=i)
                with transaction.atomic():
                    if bin_inventory.exists():
                        qs = bin_inventory.filter(inventory_type=type_normal)\
                                          .aggregate(available=Sum('quantity'), to_be_picked=Sum('to_be_picked_qty'))
                        total = qs['available'] + qs['to_be_picked']
                        if total > 0:
                            msg = {'is_success': False,
                                   'message': 'This product with sku {} and batch_id {} can not be placed in the bin'
                                              .format(i[:17], i), 'batch_id': i}
                            lis_data.append(msg)
                            continue

                    pu = PutawayCommonFunctions.get_filtered_putaways(id=ids[0], batch_id=i, warehouse=warehouse)
                    put_away_status = False
                    while len(ids):
                        put_away_done = update_putaway(ids[0], i, warehouse, int(value), request.user)
                        value = put_away_done
                        put_away_status = True
                        ids.remove(ids[0])
                    sku = put_away.last().sku
                    weight = sku.weight_value * val if sku.repackaging_type == 'packing_material' else 0
                    updating_tables_on_putaway(sh, bin_id, put_away, i, type_normal, state_total_available, 't', val,
                                               put_away_status, pu, weight)

            serializer = (PutAwaySerializer(Putaway.objects.filter(batch_id=i, warehouse=warehouse).last(),
                                            fields=('is_success', 'product_sku', 'inventory_type', 'batch_id',
                                                    'max_putaway_qty', 'putaway_quantity', 'product_name')))
            msg = serializer.data
            lis_data.append(msg)
        if len(lis_data) == len(batch_id):
            data.update({'is_success': True, 'message': "quantity has been updated in put away.", 'data': lis_data})
            return Response(data, status=status.HTTP_200_OK)
        else:
            data.update({'is_success': True, 'message': "quantity has been updated in put away.", 'data': lis_data})
            return Response(data, status=status.HTTP_200_OK)


class PutAwayProduct(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """

        :param request:
        :return:
        """
        info_logger.info("Put Away Product GET api called.")
        put_away = Putaway.objects.all()
        serializer = PutAwaySerializer(put_away, many=True, fields=('id', 'batch_id', 'sku', 'product_sku'))
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class PickupList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        info_logger.info("Pick up list GET api called.")
        msg = {'is_success': False, 'message': 'Some Required field empty.', 'data': None}
        if not request.GET.get('date'):
            return Response(msg, status=status.HTTP_200_OK)
        picker_boy = request.GET.get('picker_boy')
        if not picker_boy:
            return Response(msg, status=status.HTTP_200_OK)
        try:
            date = datetime.datetime.strptime(request.GET.get('date'), "%Y-%m-%d")
        except Exception as e:
            error_logger.error(e)
            msg = {'is_success': False, 'message': 'date format is not correct, It should be YYYY-mm-dd format.',
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        picker_boy = request.GET.get('picker_boy')

        # repackaging OR order
        pickuptype = request.GET.get('type')
        if pickuptype:
            pickuptype = int(pickuptype)
        if pickuptype not in [1, 2]:
            msg = {'is_success': False, 'message': 'Please provide a valid type', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        data_found = 0
        if pickuptype == 1:
            orders = Order.objects.filter(Q(picker_order__picker_boy__phone_number=picker_boy),
                                          Q(picker_order__picking_status__in=['picking_assigned', 'picking_complete']),
                                          Q(order_status__in=['PICKING_ASSIGNED', 'picking_complete']),
                                          Q(
                                              picker_order__picker_assigned_date__startswith=date.date())
                                          ).order_by(
                'created_at')
            if orders:
                data_found = 1
                serializer = OrderSerializer(orders, many=True)
                picking_complete = Order.objects.filter(Q(picker_order__picker_boy__phone_number=picker_boy),
                                                        Q(picker_order__picking_status__in=['picking_complete']),
                                                        Q(order_status__in=['picking_complete']),
                                                        Q(
                                                            picker_order__picker_assigned_date__startswith=date.date())).order_by(
                    'created_at').count()
                picking_assigned = orders.count()
        elif pickuptype == 2:
            repacks = Repackaging.objects.filter(Q(picker_repacks__picker_boy__phone_number=picker_boy),
                                          Q(picker_repacks__picking_status__in=['picking_assigned', 'picking_complete']),
                                          Q(picker_repacks__picker_assigned_date__startswith=date.date())).order_by(
                'created_at')
            if repacks:
                data_found = 1
                serializer = RepackagingSerializer(repacks, many=True)
                picking_complete = Repackaging.objects.filter(Q(picker_repacks__picker_boy__phone_number=picker_boy),
                                                        Q(picker_repacks__picking_status__in=['picking_complete']),
                                                        Q(picker_repacks__picker_assigned_date__startswith=date.date())
                                                              ).order_by('created_at').count()
                picking_assigned = repacks.count()

        if data_found:
            msg = {'is_success': True, 'message': 'OK', 'data': serializer.data, 'picking_complete': picking_complete,
                   'picking_assigned': picking_assigned}
            return Response(msg, status=status.HTTP_200_OK)
        else:
            picking_complete = 0
            picking_assigned = 0
            msg = {'is_success': False, 'message': 'No data found.', 'data': None, 'picking_complete': picking_complete,
                   'picking_assigned':picking_assigned}
            return Response(msg, status=status.HTTP_200_OK)


class PickupRemarksList(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        pickup_remarks = []
        for p in dict(PickupBinInventory.PICKUP_REMARKS_CHOICES):
            pickup_remarks.append({'key': 'Select Remark' if p == 0 else PickupBinInventory.PICKUP_REMARKS_CHOICES[p],
                                   'value': p})
        msg = {'is_success': True, 'message': 'OK', 'data': {'pickup_remarks': pickup_remarks}}
        return Response(msg, status=status.HTTP_200_OK)


class BinIDList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        info_logger.info("Bin ID List GET API called.")
        order_no = request.GET.get('order_no')
        if not order_no:
            msg = {'is_success': True, 'message': 'Order number field is empty.', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        pickup_orders = Order.objects.filter(order_no=order_no).last()
        if pickup_orders is None:
            pickup_orders = Repackaging.objects.filter(repackaging_no=order_no).last()

        if pickup_orders is None:
            msg = {'is_success': True, 'message': 'Order/Repackaging number does not exist.', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if isinstance(pickup_orders, Order):
            pd_qs = PickerDashboard.objects.filter(order=pickup_orders)
        else:
            pd_qs = PickerDashboard.objects.filter(repackaging=pickup_orders)
        if not pd_qs.exists():
            msg = {'is_success': False, 'message': ERROR_MESSAGES['PICKER_DASHBOARD_ENTRY_MISSING'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        pickup_assigned_date = pd_qs.last().picker_assigned_date
        pick_list = []
        pickup_bin_obj = PickupBinInventory.objects.filter(pickup__pickup_type_id=order_no) \
                                                   .exclude(pickup__status='picking_cancelled')
        if not pickup_bin_obj.exists():
            msg = {'is_success': False, 'message': ERROR_MESSAGES['PICKUP_NOT_FOUND'], 'data': {}}

        for pick_up in pickup_bin_obj:
            if pick_up.bin.bin in pick_list:
                continue
            pick_list.append(pick_up.bin.bin)
        serializer = BinSerializer(pick_list, many=True, fields=('id', 'bin_id'))
        msg = {'is_success': True, 'message': 'OK',
               'data': {'bins': serializer.data, 'pickup_created_at': pickup_assigned_date,
                        'current_time': datetime.datetime.now()}}
        return Response(msg, status=status.HTTP_200_OK)

pickup = PickupInventoryManagement()


class PickupDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        info_logger.info("Pick up detail GET API called.")
        order_no = request.GET.get('order_no')
        if not order_no:
            msg = {'is_success': True, 'message': 'Order number field is empty.', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        try:
            warehouse = request.user.shop_employee.all().last().shop_id

        except Exception as e:
            error_logger.error(e)
            return Response({'is_success': False,
                             'message': 'User is not mapped with associated Warehouse.',
                             'data': None}, status=status.HTTP_200_OK)

        bin_id = request.GET.get('bin_id')
        if not bin:
            msg = {'is_success': True, 'message': 'Bin id is not empty.', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        bin_obj = Bin.objects.filter(bin_id=bin_id, is_active=True)
        if not bin_obj:
            msg = {'is_success': False, 'message': "Bin id is not activated", 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        bin_ware_obj = Bin.objects.filter(bin_id=bin_id, is_active=True,
                                          warehouse=warehouse)
        if not bin_ware_obj:
            msg = {'is_success': False, 'message': "Bin id is not associated with the user's warehouse.", 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        picking_details = PickupBinInventory.objects.filter(pickup__pickup_type_id=order_no, bin__bin__bin_id=bin_id)\
                                                    .exclude(pickup__status='picking_cancelled')

        if not picking_details.exists():
            msg = {'is_success': False, 'message': ERROR_MESSAGES['PICK_BIN_DETAILS_NOT_FOUND'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        order = Order.objects.filter(order_no=order_no).last()
        pd_qs = PickerDashboard.objects.filter(order=order)
        if not pd_qs.exists():
            msg = {'is_success': False, 'message': ERROR_MESSAGES['PICKER_DASHBOARD_ENTRY_MISSING'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        pickup_assigned_date = pd_qs.last().picker_assigned_date
        serializer = PickupBinInventorySerializer(picking_details, many=True)
        msg = {'is_success': True, 'message': 'OK',
               'data': {'picking_details': serializer.data, 'pickup_created_at': pickup_assigned_date,
                        'current_time': datetime.datetime.now()}}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        info_logger.info("Pick up detail POST API called.")
        msg = {'is_success': False, 'message': 'Missing Required field.', 'data': None}
        try:
            warehouse = request.user.shop_employee.all().last().shop_id

        except Exception as e:
            error_logger.error(e)
            return Response({'is_success': False,
                             'message': 'User is not mapped with associated Warehouse.',
                             'data': None}, status=status.HTTP_200_OK)
        bin_id = request.data.get('bin_id')
        if not bin_id:
            return Response(msg, status=status.HTTP_200_OK)
        bin_obj = Bin.objects.filter(bin_id=bin_id, is_active=True)
        if not bin_obj:
            msg = {'is_success': False, 'message': "Bin id is not activated.", 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        bin_ware_obj = Bin.objects.filter(bin_id=bin_id, is_active=True,
                                          warehouse=warehouse)
        if not bin_ware_obj:
            msg = {'is_success': False, 'message': "Bin id is not associated with the user's warehouse.", 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        order_no = request.data.get('order_no')
        if not order_no:
            return Response(msg, status=status.HTTP_200_OK)
        pickup_quantity = request.data.get('pickup_quantity')
        if not pickup_quantity:
            return Response(msg, status=status.HTTP_200_OK)
        negative_value = [i for i in pickup_quantity if i < 0]
        if len(negative_value) > 0:
            return Response({'is_success': False,
                             'message': 'Pickup quantity can not be negative.',
                             'data': None}, status=status.HTTP_200_OK)
        total_to_be_picked_qty = request.data.get('total_to_be_picked_qty')
        if not total_to_be_picked_qty:
            return Response(msg, status=status.HTTP_200_OK)

        sku_id = request.data.get('sku_id')
        if not sku_id:
            return Response(msg, status=status.HTTP_200_OK)
        if len(sku_id) != len(pickup_quantity):
            return Response({'is_success': False,
                             'message': 'The number of sku ids entered should be equal to number of pickup qty entered.',
                             'data': None}, status=status.HTTP_200_OK)
        diction = {i[1]: {'pickup_quantity': i[0], 'total_to_be_picked_qty' : i[2]}
                   for i in zip(pickup_quantity, sku_id, total_to_be_picked_qty)}
        remarks = request.data.get('remarks')
        remarks_dict = {}
        if remarks is not None:
            if len(sku_id) != len(remarks):
                return Response({'is_success': False,
                                 'message': 'The number of remarks entered should be equal to number of sku ids entered.',
                                 'data': None}, status=status.HTTP_200_OK)
            for r in remarks:
                if r not in PickupBinInventory.PICKUP_REMARKS_CHOICES:
                    return Response({'is_success': False,
                                     'message': 'Remarks not valid.',
                                     'data': None}, status=status.HTTP_200_OK)

            remarks_dict = {i[1]: i[0] for i in zip(remarks, sku_id)}
        data_list = []
        state_picked = InventoryState.objects.filter(inventory_state='picked').last()
        state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()
        state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
        tr_type = "picked"
        with transaction.atomic():
            for j, i in diction.items():
                picking_details = PickupBinInventory.objects.filter(pickup__pickup_type_id=order_no,
                                                                    bin__bin__bin_id=bin_id, pickup__sku__id=j)\
                                                            .exclude(pickup__status='picking_cancelled')
                if picking_details.count() == 0:
                    return Response({'is_success': False,
                                     'message': 'Picking details not found, please check the details entered.',
                                     'data': None}, status=status.HTTP_200_OK)

                if picking_details.exists():
                    pickup_quantity = i['pickup_quantity']
                    total_to_be_picked = i['total_to_be_picked_qty']
                    info_logger.info("PickupDetail|POST|Pickup Started for SKU-{}, Qty-{}, Bin-{}"
                                     .format(j, pickup_quantity, bin_id))
                    if total_to_be_picked != picking_details.last().quantity :
                        return Response({'is_success': False,
                                         'message': "To be Picked qty has changed, please revise your input for "
                                                    "Picked qty",
                                         'data': None}, status=status.HTTP_200_OK)
                    tr_id = picking_details.last().pickup.id
                    pick_qty = picking_details.last().pickup_quantity
                    info_logger.info("PickupDetail|POST|SKU-{}, Picked qty-{}"
                                     .format(j, pick_qty))
                    if pick_qty is None:
                        pick_qty = 0
                    qty = picking_details.last().quantity
                    if pick_qty + pickup_quantity > qty:
                        if qty - pick_qty == 0:
                            data_list.append({'is_success': False, 'message': "You can't add more Pick up quantity."})
                        else:
                            data_list.append({'is_success': False,
                                              'message': "Can add only {} more items".format(abs(qty - pick_qty))})
                        continue
                    else:
                        remarks_text = ''
                        if remarks_dict.get(j) is not None:
                            remarks_text = PickupBinInventory.PICKUP_REMARKS_CHOICES[remarks_dict.get(j)]

                        bin_inv_id = picking_details.last().bin_id
                        bin_inv_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(id=bin_inv_id).last()
                        warehouse = bin_inv_obj.warehouse
                        sku = bin_inv_obj.sku
                        inventory_type = bin_inv_obj.inventory_type
                        if not bin_inv_obj:
                            data_list.append({'is_success': False,
                                              'message': ERROR_MESSAGES['SOME_ISSUE']})
                            info_logger.info('PickupDetail|POST API| Bin Inventory Object not found, Bin Inv ID-{}'
                                             .format(bin_inv_id))
                            continue
                        CommonBinInventoryFunctions.deduct_to_be_picked_from_bin(pickup_quantity, bin_inv_obj)

                        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                            warehouse, sku, inventory_type, state_to_be_picked, -1*pickup_quantity, tr_type, tr_id )

                        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                            warehouse, sku, inventory_type, state_total_available, -1 * pickup_quantity, tr_type, tr_id)

                        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                            warehouse, sku, inventory_type, state_picked, pickup_quantity, tr_type, tr_id)

                        picking_details.update(pickup_quantity=pickup_quantity + pick_qty, last_picked_at=timezone.now(),
                                               remarks=remarks_text)
                        pick_object = PickupBinInventory.objects.filter(pickup__pickup_type_id=order_no,
                                                                        pickup__sku__id=j)\
                                                                .exclude(pickup__status='picking_cancelled')
                        sum_total = sum([0 if i.pickup_quantity is None else i.pickup_quantity for i in pick_object])
                        Pickup.objects.filter(pickup_type_id=order_no, sku__id=j)\
                                      .exclude(status='picking_cancelled')\
                                      .update(pickup_quantity=sum_total)

                        info_logger.info("PickupDetail|POST|Picking Done for SKU-{}, Total Qty Picked-{}"
                                         .format(j, sum_total))
                        serializer = PickupBinInventorySerializer(picking_details.last())
                        data_list.append(serializer.data)
        msg = {'is_success': True, 'message': 'Pick up data saved successfully.',
               'data': data_list}
        return Response(msg, status=status.HTTP_200_OK)


class PickupComplete(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request):
        order_no = request.data.get('order_no')
        if not order_no:
            msg = {'is_success': True, 'message': 'Order number field is empty.', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        is_repackaging = 0

        order_qs = Order.objects.filter(order_no=order_no)
        order_obj = order_qs.last()

        if order_obj:
            pd_obj = PickerDashboard.objects.filter(order_id=order_obj).exclude(picking_status='picking_cancelled')
        else:
            is_repackaging = 1
            rep_qs = Repackaging.objects.filter(repackaging_no=order_no)
            rep_obj = rep_qs.last()
            pd_obj = PickerDashboard.objects.filter(repackaging_id=rep_obj).exclude(picking_status='picking_cancelled')

        if pd_obj.count() > 1:
            msg = {'is_success': True, 'message': 'Multiple picklists exist for this order', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        pick_obj = Pickup.objects.filter(pickup_type_id=order_no).exclude(status='picking_cancelled')

        if pick_obj.exists():
            for pickup in pick_obj:
                pickup_bin_list = PickupBinInventory.objects.filter(pickup=pickup)
                for pickup_bin in pickup_bin_list:
                    if pickup_bin.pickup_quantity is None:
                        return Response({'is_success': False,
                                         'message': "Pickup Incomplete for some products-e.g BIN:{},SKU:{}"
                                        .format(pickup_bin.bin.bin.bin_id,
                                                pickup_bin.pickup.sku.product_sku)})

            else:
                with transaction.atomic():
                    inventory_type = pickup.inventory_type
                    state_to_be_picked = InventoryState.objects.filter(inventory_state="to_be_picked").last()
                    tr_type = "pickup_complete"
                    for pickup in pick_obj:
                        info_logger.info("PickupComplete : Starting to complete pickup for order - {}, sku - {}"
                                         .format(pickup.pickup_type_id, pickup.sku))
                        pickup_bin_list = PickupBinInventory.objects.filter(pickup=pickup)
                        for pickup_bin in pickup_bin_list:
                            if pickup_bin.pickup_quantity is None:
                                pickup_bin.pickup_quantity = 0
                            reverse_quantity = pickup_bin.quantity - pickup_bin.pickup_quantity
                            bin_inv_id = pickup_bin.bin_id
                            bin_inv_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(id=bin_inv_id).last()
                            if not bin_inv_obj:
                                info_logger.info('PickupComplete|POST API| Bin Inventory Object not found, '
                                                 'Bin Inv ID-{}'.format(bin_inv_id))
                                continue
                            CommonBinInventoryFunctions.deduct_to_be_picked_from_bin(reverse_quantity, bin_inv_obj)
                            info_logger.info("PickupComplete : reverse quantity for SKU {} - {}"
                                             .format(pickup.sku, reverse_quantity))

                            # Entry in warehouse Table

                            if is_repackaging == 1:
                                state_repackaging = InventoryState.objects.filter(inventory_state='repackaging').last()
                                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                    pickup_bin.warehouse, pickup_bin.pickup.sku, inventory_type, state_repackaging,
                                    pickup_bin.quantity * -1, tr_type, pickup.pk)

                            if reverse_quantity != 0:
                                # Entry in bin table
                                CommonBinInventoryFunctions.update_or_create_bin_inventory(pickup_bin.warehouse,
                                                                                           pickup_bin.bin.bin,
                                                                                           pickup_bin.pickup.sku
                                                                                           , pickup_bin.batch_id,
                                                                                           inventory_type,
                                                                                           reverse_quantity, True)
                                InternalInventoryChange.create_bin_internal_inventory_change(pickup_bin.warehouse,
                                                                                             pickup_bin.pickup.sku,
                                                                                             pickup_bin.batch_id,
                                                                                             pickup_bin.bin.bin,
                                                                                             inventory_type, inventory_type,
                                                                                             tr_type,
                                                                                             pickup.pk,
                                                                                             reverse_quantity)
                                # Entry in warehouse table
                                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                    pickup_bin.warehouse, pickup_bin.pickup.sku, inventory_type, state_to_be_picked,
                                    -1*reverse_quantity, tr_type, pickup.pk)

                        info_logger.info("PickupComplete : Pickup completed for order - {}, sku - {}"
                                         .format(pickup.pickup_type_id, pickup.sku))

                    if is_repackaging == 1:
                        rep_qs.update(source_picking_status='picking_complete')
                    else:
                        order_qs.update(order_status='picking_complete')

                    pd_obj.update(picking_status='picking_complete', completed_at=timezone.now())
                    pick_obj.update(status='picking_complete', completed_at=timezone.now())

                return Response({'is_success': True,
                                 'message': "Pickup complete for all the items"})

        msg = {'is_success': True, 'message': ' Does not exist.', 'data': None}
        return Response(msg, status=status.HTTP_404_NOT_FOUND)


class DecodeBarcode(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def post(self, request):
        barcode_list = request.data.get('barcode_list')
        if not barcode_list:
            msg = {'is_success': False, 'message': 'Barcode list field is empty.', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        barcode_list = list(barcode_list.split(","))
        if not isinstance(barcode_list, list):
            msg = {'is_success': False, 'message': 'Format of barcode list is wrong.', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        data = []
        for barcode in barcode_list:
            barcode_length = len(barcode)
            if barcode_length != 13:
                barcode_data = {'type': None, 'id': None, 'barcode': barcode}
                data_item = {'is_success': False, 'message': 'Barcode length must be 13 characters',
                             'data': barcode_data}
                data.append(data_item)
                continue;
            type_identifier = barcode[0]
            if type_identifier == '1':
                id = barcode[1:12].lstrip('0')
                if id is not None:
                    id = int(id)
                else:
                    id = 0
                bin = Bin.objects.filter(pk=id).last()
                if bin is None:
                    barcode_data = {'type': None, 'id': None, 'barcode': barcode}
                    data_item = {'is_success': False, 'message': 'Bin Id not found', 'data': barcode_data}
                    data.append(data_item)
                else:
                    bin_id = bin.bin_id
                    barcode_data = {'type': 'bin', 'id': bin_id, 'barcode': barcode}
                    data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                    data.append(data_item)

            elif type_identifier == '2':
                id = barcode[0:12]
                grn_product = GRNOrderProductMapping.objects.filter(barcode_id=id, batch_id__isnull=False).last()

                if grn_product is None:
                    batch_id = id[6:]
                    product_id = id[1:6].lstrip("0")
                    product_batch_ids = In.objects.filter(sku=Product.objects.filter(id=product_id).last()).values('batch_id').distinct()
                    if product_batch_ids:
                        for batch_ids in product_batch_ids:
                            if batch_ids['batch_id'][-6:] == batch_id:
                                barcode_data = {'type': 'batch', 'id': batch_ids['batch_id'], 'barcode': barcode}
                                data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                                data.append(data_item)
                    else:
                        barcode_data = {'type': None, 'id': None, 'barcode': barcode}
                        data_item = {'is_success': False, 'message': 'Batch Id not found', 'data': barcode_data}
                        data.append(data_item)
                else:
                    batch_id = grn_product.batch_id
                    barcode_data = {'type': 'batch', 'id': batch_id, 'barcode': barcode}
                    data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                    data.append(data_item)
            else:
                barcode_data = {'type': '', 'id': '', 'barcode': barcode}
                data_item = {'is_success': False, 'message': 'Barcode type not supported', 'data': barcode_data}
                data.append(data_item)
        msg = {'is_success': True, 'message': '', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)

