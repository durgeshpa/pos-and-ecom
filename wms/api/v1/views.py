import logging

from django.utils import timezone

from retailer_backend.messages import ERROR_MESSAGES
from retailer_backend.utils import SmallOffsetPagination
from wms.models import Bin, Putaway, PutawayBinInventory, BinInventory, InventoryType, Pickup, InventoryState, \
    PickupBinInventory, In, QCArea, Crate, PickupCrate
from products.models import Product
from .serializers import BinSerializer, PutAwaySerializer, PickupBinInventorySerializer, RepackagingSerializer, \
    BinInventorySerializer, OrderBinsSerializer
from wms.views import PickupInventoryManagement, update_putaway, auto_qc_area_assignment_to_order
from rest_framework.response import Response
from rest_framework import status
from shops.models import Shop
from products.models import Repackaging
from retailer_to_sp.models import Order, PickerDashboard, ShipmentPackaging
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Sum, Case, When, F
from django.db import transaction, models
from gram_to_brand.models import GRNOrderProductMapping
import datetime
from wms.common_functions import (CommonBinInventoryFunctions, PutawayCommonFunctions, CommonBinFunctions,
                                  updating_tables_on_putaway,
                                  CommonWarehouseInventoryFunctions, InternalInventoryChange,
                                  get_logged_user_wise_query_set_for_pickup_list)

from ..v2.serializers import PicklistSerializer
from ...common_validators import validate_pickup_crates_list, validate_pickup_request
from ...services import check_whc_manager_coordinator_supervisor_picker, pickup_search, check_picker

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

        return Response({'is_success': False,
                         'message': 'Deprecated.',
                         'data': None}, status=status.HTTP_200_OK)

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


class PickupListOld(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_whc_manager_coordinator_supervisor_picker
    def get(self, request):
        info_logger.info("PickupList api called.")
        """ GET Pickup List API"""

        pickuptype = request.GET.get('type')
        if not pickuptype:
            return Response({'is_success': True, 'message': "'type' | This is mandatory.", 'data': None},
                            status=status.HTTP_200_OK)
        if pickuptype:
            pickuptype = int(pickuptype)
        if pickuptype not in [1, 2]:
            return Response({'is_success': True, 'message': "'type' | Please provide a valid type.", 'data': None},
                            status=status.HTTP_200_OK)

        if pickuptype == 1:
            self.serializer_class = PicklistSerializer
            self.queryset = PickerDashboard.objects.exclude(order__isnull=True)

        if pickuptype == 2:
            self.serializer_class = RepackagingSerializer
            self.queryset = Repackaging.objects.all()

        self.queryset = get_logged_user_wise_query_set_for_pickup_list(self.request.user, pickuptype, self.queryset)
        self.queryset = self.filter_pickup_list_data(pickuptype)

        # picking_complete count
        if pickuptype == 1:
            picking_complete = self.queryset.filter(picking_status='picking_complete').count()
            self.queryset = self.queryset.filter(
                Q(picking_status__in=['picking_assigned', 'picking_complete', 'moved_to_qc'])).order_by('-created_at')

        if pickuptype == 2:
            picking_complete = self.queryset.filter(Q(picker_repacks__picking_status__in=['picking_complete'])).count()
            self.queryset = self.queryset.filter(
                Q(picker_repacks__picking_status__in=['picking_assigned', 'picking_complete'])).order_by('-created_at')

        # picking_assigned count
        picking_assigned = self.queryset.count()

        data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(data, many=True)
        msg = "OK" if self.queryset else "No data found."
        resp_data = {'is_success': True, 'message': msg,
                     'data': serializer.data,
                     'picking_complete': picking_complete,
                     'picking_assigned': picking_assigned}
        return Response(resp_data, status=status.HTTP_200_OK)

    def filter_pickup_list_data(self, pickup_type):
        picker_boy = self.request.GET.get('picker_boy')
        selected_date = self.request.GET.get('date')
        zone = self.request.GET.get('zone')
        picking_status = self.request.GET.get('picking_status')

        '''Filters using picker_boy, selected_date'''
        if pickup_type == 1:
            if picker_boy:
                self.queryset = self.queryset.filter(picker_boy__phone_number=picker_boy)

            if zone:
                self.queryset = self.queryset.filter(zone__id=zone)

            if picking_status:
                self.queryset = self.queryset.filter(picking_status__id=picking_status)

            if selected_date:
                try:
                    date = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
                    self.queryset = self.queryset.filter(picker_assigned_date__startswith=date.date())
                except Exception as e:
                    error_logger.error(e)

        if pickup_type == 2:
            if picker_boy:
                self.queryset = self.queryset.filter(picker_repacks__picker_boy__phone_number=picker_boy)

            if zone:
                self.queryset = self.queryset.filter(picker_repacks__zone__id=zone)

            if picking_status:
                self.queryset = self.queryset.filter(picker_repacks__picking_status__id=picking_status)

            if selected_date:
                try:
                    date = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
                    self.queryset = self.queryset.filter(picker_repacks__picker_assigned_date__startswith=date.date())
                except Exception as e:
                    error_logger.error(e)

        return self.queryset


class PickupList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_whc_manager_coordinator_supervisor_picker
    def get(self, request):
        info_logger.info("PickupList api called.")
        """ GET Pickup List API"""
        validate_request = validate_pickup_request(request)
        if "error" in validate_request:
            return Response({'is_success': True, 'message': validate_request['error'], 'data': None},
                            status=status.HTTP_200_OK)

        self.serializer_class = PicklistSerializer
        self.queryset = PickerDashboard.objects.filter(
            Q(order__isnull=False, order__order_status__in=[Order.PICKUP_CREATED, Order.PICKING_ASSIGNED,
                                                            Order.PICKING_PARTIAL_COMPLETE, Order.PICKING_COMPLETE,
                                                            Order.PARTIAL_MOVED_TO_QC, Order.MOVED_TO_QC],
             order__rt_order_order_product__isnull=True) |
            Q(repackaging__isnull=False),
            picking_status__in=['picking_assigned', 'picking_complete', 'moved_to_qc']).\
            annotate(token_id=Case(
                                    When(order=None,
                                         then=F('repackaging')),
                                    default=F('order'),
                                    output_field=models.CharField(),
                                )).\
            order_by('order__created_at', 'repackaging__created_at')
        self.queryset = get_logged_user_wise_query_set_for_pickup_list(self.request.user, 1, self.queryset)

        validate_request = validate_pickup_request(request)
        if "error" in validate_request:
            return Response({'is_success': True, 'message': validate_request['error'], 'data': None},
                            status=status.HTTP_200_OK)

        self.queryset = self.filter_pickup_list_data()

        # picking_complete count
        picking_complete = self.queryset.filter(picking_status='picking_complete').order_by().distinct('token_id').count()

        # picking_assigned count
        picking_assigned = self.queryset.filter(picking_status='picking_assigned').order_by().distinct('token_id').count()

        data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(data, many=True)
        msg = "OK" if self.queryset else "No data found."
        resp_data = {'is_success': True, 'message': msg,
                     'data': serializer.data,
                     'picking_complete': picking_complete,
                     'picking_assigned': picking_assigned}
        return Response(resp_data, status=status.HTTP_200_OK)

    def filter_pickup_list_data(self):
        # warehouse = self.request.user.shop_employee.last().shop
        search_text = self.request.GET.get('search_text')
        picker_boy = self.request.GET.get('picker_boy')
        selected_date = self.request.GET.get('date')
        data_days = self.request.GET.get('data_days')
        zone = self.request.GET.get('zone')
        picking_status = self.request.GET.get('picking_status')
        data_days = self.request.GET.get('data_days')
        pickup_type = self.request.GET.get('type')

        # '''filter by user warehouse'''
        # self.queryset = self.queryset.filter(zone__warehouse=warehouse)
        '''filter by pickup type'''
        if pickup_type:
            pickup_type = int(pickup_type)
            if pickup_type == 1:
                self.queryset = self.queryset.filter(order__isnull=False)
            elif pickup_type == 2:
                self.queryset = self.queryset.filter(repackaging__isnull=False)

        '''search using order number & repackaging number'''
        if search_text:
            self.queryset = pickup_search(self.queryset, search_text)

        '''Filters using picker_boy, selected_date, picking_status'''
        if picker_boy:
            self.queryset = self.queryset.filter(picker_boy=picker_boy)

        if zone:
            self.queryset = self.queryset.filter(zone__id=zone)

        if picking_status:
            self.queryset = self.queryset.filter(picking_status__iexact=picking_status)


        if selected_date:
            if data_days:
                end_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
                start_date = end_date - datetime.timedelta(days=int(data_days))
                end_date = end_date +datetime.timedelta(days=1)
                self.queryset = self.queryset.filter(
                    created_at__gte=start_date.date(), created_at__lt=end_date.date())
            else:
                selected_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
                self.queryset = self.queryset.filter(created_at__date=selected_date)

        return self.queryset


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

    @check_picker
    def get(self, request):
        info_logger.info("Bin ID List GET API called.")
        zone = request.GET.get('zone')
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
        pd_qs = get_logged_user_wise_query_set_for_pickup_list(self.request.user, 1, pd_qs)

        if not pd_qs.exists():
            msg = {'is_success': False, 'message': ERROR_MESSAGES['PICKER_DASHBOARD_ENTRY_MISSING'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        pickup_assigned_date = pd_qs.last().picker_assigned_date
        zones = pd_qs.values_list('zone', flat=True)
        pickup_bin_obj = PickupBinInventory.objects.filter(pickup__pickup_type_id=order_no,
                                                           pickup__zone__in=zones, quantity__gt=0) \
                                                   .exclude(pickup__status='picking_cancelled')\
                                                   .prefetch_related('bin__bin')\
                                                   .order_by('bin__bin__bin_id')
        pickup_bin_obj = self.filter_bins_data(pickup_bin_obj)
        bins_added = {}
        for pick_up in pickup_bin_obj:
            if bins_added.get(pick_up.bin.bin.id) is not None and \
                    bins_added[pick_up.bin.bin.id]["pickup_status"] != 'picking_complete':
                continue

            if pick_up.pickup_quantity is not None and pick_up.pickup_quantity < pick_up.quantity:
                pickup_status = 'picking_partial'
            elif pick_up.pickup_quantity == pick_up.quantity:
                pickup_status = 'picking_complete'
            else:
                pickup_status = 'picking_pending'

            bins_added[pick_up.bin.bin.id] = {"id": pick_up.bin.bin.id, "bin_id": pick_up.bin.bin.bin_id,
                                              "pickup_status": pickup_status}
        pick_list = bins_added.values()
        serializer = OrderBinsSerializer(pick_list, many=True)
        msg = {'is_success': True, 'message': 'OK',
               'data': {'bins': serializer.data, 'pickup_created_at': pickup_assigned_date,
                        'current_time': datetime.datetime.now()}}
        return Response(msg, status=status.HTTP_200_OK)

    def filter_bins_data(self, queryset):
        warehouse = self.request.user.shop_employee.last().shop
        zone = self.request.GET.get('zone')

        '''filter by user warehouse'''
        queryset = queryset.filter(warehouse=warehouse)

        if zone:
            queryset = queryset.filter(pickup__zone__id=zone)

        return queryset

pickup = PickupInventoryManagement()


class PickupDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_picker
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

        picking_details = PickupBinInventory.objects.filter(pickup__pickup_type_id=order_no, bin__bin__bin_id=bin_id,
                                                            pickup__zone__picker_users=request.user, quantity__gt=0)\
                                                    .exclude(pickup__status='picking_cancelled')

        if not picking_details.exists():
            msg = {'is_success': False, 'message': ERROR_MESSAGES['PICK_BIN_DETAILS_NOT_FOUND'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        order = Order.objects.filter(order_no=order_no).last()
        pd_qs = PickerDashboard.objects.filter(order=order, zone__picker_users=request.user)
        if not pd_qs.exists():
            msg = {'is_success': False, 'message': ERROR_MESSAGES['PICKER_DASHBOARD_ENTRY_MISSING'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        pickup_assigned_date = pd_qs.last().picker_assigned_date
        serializer = PickupBinInventorySerializer(picking_details, many=True)
        msg = {'is_success': True, 'message': 'OK',
               'data': {'picking_details': serializer.data, 'pickup_created_at': pickup_assigned_date,
                        'current_time': datetime.datetime.now()}}
        return Response(msg, status=status.HTTP_200_OK)

    @check_picker
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

        pickup_crates = request.data.get('pickup_crates')
        if not pickup_crates:
            return Response(msg, status=status.HTTP_200_OK)
        if len(pickup_crates) != len(sku_id):
            return Response({'is_success': False,
                             'message': 'The number of pickup_crates entered should be equal to number of sku ids entered.',
                             'data': None}, status=status.HTTP_200_OK)
        picker_dash_obj = PickerDashboard.objects.filter(order__order_no=order_no, picker_boy=request.user).last()
        if not picker_dash_obj:
            picker_dash_obj = PickerDashboard.objects.filter(
                repackaging__repackaging_no=order_no, picker_boy=request.user).last()
        for cnt, crate_obj in enumerate(pickup_crates):
            if not crate_obj:
                return Response(msg, status=status.HTTP_200_OK)
            if not isinstance(crate_obj, dict):
                return {"error": "Key 'pickup_crates' can be of object type only."}
            validated_data = validate_pickup_crates_list(crate_obj, pickup_quantity[cnt], warehouse,
                                                         picker_dash_obj.zone, order_no)
            if 'error' in validated_data:
                msg['message'] = validated_data['error']
                return Response(msg, status=status.HTTP_200_OK)

        diction = {i[1]: {'pickup_quantity': i[0], 'total_to_be_picked_qty': i[2], 'pickup_crates': i[3]}
                   for i in zip(pickup_quantity, sku_id, total_to_be_picked_qty, pickup_crates)}
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
                                                                    pickup__zone__picker_users=request.user,
                                                                    bin__bin__bin_id=bin_id, pickup__sku__id=j,
                                                                    quantity__gt=0)\
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
                    if pick_qty is not None:
                        return Response({'is_success': False, 'message': "Multiple pickups are not allowed",
                                         'data': None}, status=status.HTTP_200_OK)
                    else:
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
                        is_crate_applicable = False
                        if i['pickup_crates']['is_crate_applicable'] is True:
                            is_crate_applicable = True
                            for crate_obj in i['pickup_crates']['crates']:
                                crate_instance = Crate.objects.get(crate_id=crate_obj['crate_id'])
                                PickupCrate.objects.create(
                                    pickup=picking_details.last().pickup, quantity=int(crate_obj['quantity']),
                                    crate=crate_instance, created_by=request.user, updated_by=request.user)
                        pick_object = PickupBinInventory.objects.filter(
                            pickup__pickup_type_id=order_no, pickup__zone__picker_users=request.user,
                            pickup__sku__id=j).exclude(pickup__status='picking_cancelled')
                        sum_total = sum([0 if i.pickup_quantity is None else i.pickup_quantity for i in pick_object])
                        Pickup.objects.filter(pickup_type_id=order_no, sku__id=j, zone__picker_users=request.user)\
                                      .exclude(status='picking_cancelled')\
                                      .update(pickup_quantity=sum_total, is_crate_applicable=is_crate_applicable)

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

        with transaction.atomic():

            if order_obj:
                pd_obj = PickerDashboard.objects.select_for_update().filter(
                    order_id=order_obj, zone__picker_users=request.user)
            else:
                is_repackaging = 1
                rep_qs = Repackaging.objects.filter(repackaging_no=order_no)
                rep_obj = rep_qs.last()
                pd_obj = PickerDashboard.objects.select_for_update().filter(
                    repackaging_id=rep_obj, zone__picker_users=request.user)

            if pd_obj.filter(picking_status='picking_complete').exists():
                return Response({'is_success': True, 'message': "Pickup completed for the selected items"})

            pick_obj = Pickup.objects.select_for_update(). \
                filter(pickup_type_id=order_no, zone__picker_users=request.user). \
                exclude(status__in=['picking_complete', 'picking_cancelled'])

            if pick_obj.exists():
                for pickup in pick_obj:
                    pickup_bin_list = PickupBinInventory.objects.filter(pickup=pickup, quantity__gt=0)
                    for pickup_bin in pickup_bin_list:
                        if pickup_bin.pickup_quantity is None:
                            return Response({'is_success': False,
                                             'message': "Pickup Incomplete for some products-e.g BIN:{},SKU:{}"
                                            .format(pickup_bin.bin.bin.bin_id,
                                                    pickup_bin.pickup.sku.product_sku)})

                else:
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

                    pd_obj.update(picking_status='picking_complete', completed_at=timezone.now())
                    pick_obj.update(status='picking_complete', completed_at=timezone.now())

                    if is_repackaging == 1:
                        pd_queryset = PickerDashboard.objects.filter(repackaging_id=rep_obj)
                        if not pd_queryset.filter(picking_status='moved_to_qc').exists():
                            if pd_queryset. \
                                    exclude(picking_status__in=['picking_complete', 'picking_cancelled']).exists():
                                rep_qs.update(source_picking_status='picking_partial_complete')
                                info_logger.info("PickupComplete | " + str(rep_obj.repackaging_no) +
                                                 " | picking_partial_complete.")
                                return Response({'is_success': True, 'message': "Pickup complete for the selected items"})
                            else:
                                rep_qs.update(source_picking_status='picking_complete')
                                info_logger.info("PickupComplete | " + str(rep_obj.repackaging_no) +
                                                 " | picking_complete.")
                                return Response({'is_success': True, 'message': "Pickup complete for all the items"})
                    else:
                        order_no = order_obj.order_no
                        pd_queryset = PickerDashboard.objects.filter(order_id=order_obj)
                        if not pd_queryset.filter(picking_status='moved_to_qc').exists():
                            info_logger.info("PickupComplete | " + str(order_obj.order_no) +
                                             " | No picklist exist in moved_to_qc.")
                            if PickerDashboard.objects.filter(order_id=order_obj). \
                                    exclude(picking_status__in=['picking_complete', 'picking_cancelled']).exists():
                                order_qs.update(order_status=Order.PICKING_PARTIAL_COMPLETE)
                                info_logger.info("PickupComplete | " + str(order_obj.order_no) +
                                                 " | PICKING_PARTIAL_COMPLETE.")
                                auto_qc_area_assignment_to_order(order_no)
                                return Response({'is_success': True, 'message': "Pickup complete for the selected items"})
                            else:
                                order_qs.update(order_status=Order.PICKING_COMPLETE)
                                info_logger.info("PickupComplete | " + str(order_obj.order_no) +
                                                 " | PICKING_COMPLETE.")
                                auto_qc_area_assignment_to_order(order_no)
                                return Response({'is_success': True, 'message': "Pickup complete for all the items"})

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
            if barcode_length == 8:
                barcode_data = {'type': 'EAN', 'id': barcode, 'barcode': barcode}
                data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                data.append(data_item)
                continue
            elif barcode_length < 13:
                barcode = barcode.zfill(13)
            elif barcode_length != 13:
                barcode_data = {'type': None, 'id': None, 'barcode': barcode}
                data_item = {'is_success': False, 'message': 'Barcode length must be 13 characters',
                             'data': barcode_data}
                data.append(data_item)
                continue
            type_identifier = barcode[0:2]
            if type_identifier[0] == '1':
                id = barcode[1:12].lstrip('0')
                if id is not None:
                    id = int(id)
                else:
                    id = 0
                bin = Bin.objects.filter(pk=id).last()
                if bin is None:
                    barcode_data = {'type': 'EAN', 'id': barcode, 'barcode': barcode}
                    data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                    data.append(data_item)
                else:
                    bin_id = bin.bin_id
                    barcode_data = {'type': 'bin', 'id': bin_id, 'barcode': barcode}
                    data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                    data.append(data_item)

            elif type_identifier[0] == '2':
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
            elif type_identifier == '30':
                id = barcode[2:12].lstrip('0')
                if id is not None:
                    id = int(id)
                else:
                    id = 0
                area = QCArea.objects.filter(pk=id).last()
                if area is None:
                    barcode_data = {'type': None, 'id': None, 'barcode': barcode}
                    data_item = {'is_success': False, 'message': 'QC Area not found', 'data': barcode_data}
                    data.append(data_item)
                else:
                    area_id = area.area_id
                    barcode_data = {'type': 'qc area', 'id': area_id, 'barcode': barcode}
                    data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                    data.append(data_item)
            elif type_identifier == '04':
                id = barcode[2:12].lstrip('0')
                if id is not None:
                    id = int(id)
                else:
                    id = 0
                crate = Crate.objects.filter(pk=id).last()
                if crate is None:
                    barcode_data = {'type': None, 'id': None, 'barcode': barcode}
                    data_item = {'is_success': False, 'message': 'QC Area not found', 'data': barcode_data}
                    data.append(data_item)
                else:
                    crate_id = crate.crate_id
                    barcode_data = {'type': 'crate', 'id': crate_id, 'barcode': barcode}
                    data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                    data.append(data_item)
            elif type_identifier == '05':
                id = barcode[2:12].lstrip('0')
                if id is not None:
                    id = int(id)
                else:
                    id = 0
                packaging = ShipmentPackaging.objects.filter(pk=id).last()
                if packaging is None:
                    barcode_data = {'type': None, 'id': None, 'barcode': barcode}
                    data_item = {'is_success': False, 'message': 'Packaging not found', 'data': barcode_data}
                    data.append(data_item)
                else:
                    barcode_data = {'type': 'packaging', 'id': packaging.pk, 'barcode': barcode}
                    data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                    data.append(data_item)
            else:
                barcode_data = {'type': 'EAN', 'id': barcode, 'barcode': barcode}
                data_item = {'is_success': True, 'message': '', 'data': barcode_data}
                data.append(data_item)
        msg = {'is_success': True, 'message': '', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)

