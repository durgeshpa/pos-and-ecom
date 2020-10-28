import logging
from datetime import timedelta, datetime

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework import status, mixins
from rest_framework.views import APIView
from rest_framework import permissions, authentication


from retailer_backend.messages import ERROR_MESSAGES
from wms.common_functions import InternalInventoryChange, WareHouseInternalInventoryChange, \
    CommonWarehouseInventoryFunctions, CommonBinInventoryFunctions
from wms.models import BinInventory, Bin, InventoryType, PickupBinInventory, WarehouseInventory, InventoryState, Pickup
from wms.views import PicklistRefresh
from .serializers import AuditDetailSerializer
from ...models import AuditDetail, AUDIT_DETAIL_STATUS_CHOICES, AUDIT_TYPE_CHOICES, AUDIT_DETAIL_STATE_CHOICES, \
    AuditRun, AUDIT_RUN_STATUS_CHOICES, AUDIT_LEVEL_CHOICES, AuditRunItem, AUDIT_STATUS_CHOICES, AuditCancelledPicklist
from ...tasks import update_audit_status
from ...utils import is_audit_started
from ...views import BlockUnblockProduct
from rest_framework.permissions import BasePermission

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class IsAuditor(BasePermission):
    """
    Allows access only to the users from Warehouse-Auditor Group.
    """
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Warehouse-Auditor').exists()


class AuditListView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsAuditor)

    def get(self, request):
        info_logger.info("Audit detail GET API called.")
        in_date = request.GET.get('date')
        if not in_date:
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['EMPTY'] % 'date',
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        try:
            date = datetime.strptime(in_date, "%Y-%m-%d")
        except Exception as e:
            error_logger.error(e)
            msg = {'is_success': False, 'message': 'date format is not correct, It should be YYYY-mm-dd format.',
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(auditor=request.user,
                                            audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                            state__in=[AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                                       AUDIT_DETAIL_STATE_CHOICES.INITIATED],
                                            status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE,
                                            created_at__date=date)
        count = audits.count()
        if count == 0:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        serializer = AuditDetailSerializer(audits, many=True)
        msg = {'is_success': True, 'message': 'OK', 'data': {'audit_count': count, 'audit_list':serializer.data}}
        return Response(msg, status=status.HTTP_200_OK)


class AuditStartView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsAuditor)

    def post(self, request):
        info_logger.info("Audit Start API called.")

        audit_no = request.POST.get('audit_no')

        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'Audit Number', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(id=audit_no, auditor=request.user,
                                            audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                            status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
        count = audits.count()
        if count == 0:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = audits.last()
        if audit.state != AUDIT_DETAIL_STATE_CHOICES.CREATED:
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['INVALID_AUDIT_STATE'] % AUDIT_DETAIL_STATE_CHOICES[AUDIT_DETAIL_STATE_CHOICES.CREATED],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if not self.can_start_audit(audit):
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['AUDIT_START_TIME_ERROR']
                       .format(self.audit_start_time(audit).strftime("%d/%m/%Y, %H:%M:%S")),
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        self.initiate_audit(audit)
        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def can_start_audit(self, audit):
        return (audit.created_at <= datetime.now() - timedelta(minutes=30))

    def audit_start_time(self, audit):
        return audit.created_at + timedelta(minutes=30)

    @transaction.atomic
    def initiate_audit(self, audit):
        AuditRun.objects.create(warehouse=audit.warehouse, audit=audit,
                                status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        audit.state = AUDIT_DETAIL_STATE_CHOICES.INITIATED
        audit.save()


class AuditEndView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsAuditor)

    def get(self, request):
        info_logger.info("AuditUpdateView GET API called.")

        audit_no = request.POST.get('audit_no')

        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(id=audit_no, auditor=request.user,
                                            audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                            status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
        count = audits.count()
        if count == 0:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = audits.last()
        if audit.state != AUDIT_DETAIL_STATE_CHOICES.INITIATED:
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['INVALID_AUDIT_STATE'] % AUDIT_DETAIL_STATE_CHOICES[AUDIT_DETAIL_STATE_CHOICES.ENDED],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)


        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': {'audit_detail' :serializer.data,
                                                             'can_audit_end' : self.can_end_audit(audit)}}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        info_logger.info("AuditUpdateView called.")

        audit_no = request.POST.get('audit_no')

        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(id=audit_no, auditor=request.user,
                                            audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                            status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
        count = audits.count()
        if count == 0:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = audits.last()
        if audit.state != AUDIT_DETAIL_STATE_CHOICES.INITIATED:
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['INVALID_AUDIT_STATE'] % AUDIT_DETAIL_STATE_CHOICES[AUDIT_DETAIL_STATE_CHOICES.INITIATED],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if not self.can_end_audit(audit):
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['FAILED_STATE_CHANGE'],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        is_ended = self.end_audit(audit)
        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': {'audit_detail': serializer.data,
                                                             'audit_ended': is_ended}}
        return Response(msg, status=status.HTTP_200_OK)

    def can_end_audit(self, audit):
        if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            return self.can_end_bin_audit(audit)
        elif audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            return self.can_end_product_audit(audit)

    def can_end_bin_audit(self, audit):
        expected_bin_count = audit.bin.count()
        audit_run = AuditRun.objects.filter(audit=audit)
        audited_bin_count = AuditRunItem.objects.filter(audit_run=audit_run).annotate(count=Count('bin_id', distinct=True))
        if expected_bin_count != audited_bin_count:
            return False
        return True

    def can_end_product_audit(self, audit):
        expected_sku_count = audit.sku.count()
        audited_skus = AuditRunItem.objects.filter(audit_run__audit=audit)\
                                                .annotate(count=Count('sku_id', distinct=True))
        if audited_skus.count() > 0:
            if expected_sku_count != audited_skus.last().count:
                return False
        return True

    @transaction.atomic
    def end_audit(self, audit):
        audit_run = AuditRun.objects.filter(warehouse=audit.warehouse, audit=audit,
                                            status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        if audit_run is None:
            return False
        audit_run.update(status=AUDIT_RUN_STATUS_CHOICES.COMPLETED, completed_at=timezone.now())
        audit.state = AUDIT_DETAIL_STATE_CHOICES.ENDED
        audit.save()
        update_audit_status.delay(audit.id)
        return True


class AuditBinList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsAuditor)

    def get(self, request):
        info_logger.info("AuditBinList GET API called.")
        audit_no = request.GET.get('audit_no')
        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = AuditDetail.objects.filter(id=audit_no).last()
        if audit is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if not is_audit_started(audit):
            msg = {'is_success': False, 'message': ERROR_MESSAGES['AUDIT_NOT_STARTED'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audit_sku = request.GET.get('sku')
        audit_bins = []
        audit_skus = []
        if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            audit_skus = audit.sku.all().values('product_sku', 'product_name')
            skus_audited = AuditRunItem.objects.filter(audit_run__audit=audit).values_list('sku__id', flat=True)
            for s in audit_skus:
                audit_done = False
                if s in skus_audited:
                    audit_done = True
                s['audit_done'] = audit_done
        elif audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            audit_bins = audit.bin.all().values('bin_id')
            bins_audited = AuditRunItem.objects.filter(audit_run__audit=audit).values_list('bin__bin_id', flat=True)
            for b in audit_bins:
                audit_done = False
                if b in bins_audited:
                    audit_done = True
                b['audit_done'] = audit_done


        data = {'bin_count': len(audit_bins), 'sku_count': len(audit_skus), 'sku_to_audit': audit_skus,
                'bins_to_audit': audit_bins}
        msg = {'is_success': True, 'message': 'OK', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)


class AuditBinsBySKUList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsAuditor)

    def get(self, request):
        info_logger.info("AuditBinList GET API called.")
        audit_no = request.GET.get('audit_no')
        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = AuditDetail.objects.filter(id=audit_no).last()
        if audit is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if not is_audit_started(audit):
            msg = {'is_success': False, 'message': ERROR_MESSAGES['AUDIT_NOT_STARTED'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audit_sku = request.GET.get('sku')
        if audit_sku is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'sku', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audit_bins = []

        bin_ids = BinInventory.objects.filter(sku=audit_sku).values_list('bin_id', flat=True)
        bins_to_audit = Bin.objects.filter(id__in=bin_ids).values('bin_id')
        bins_audited = AuditRunItem.objects.filter(audit_run__audit=audit).values_list('bin__bin_id', flat=True)
        for b in bins_to_audit:
            audit_done = False
            if b in bins_audited:
                audit_done = True
            b['audit_done'] = audit_done


        data = {'bin_count': len(bins_to_audit), 'sku': audit_sku,
                'sku_bins': bins_to_audit}
        msg = {'is_success': True, 'message': 'OK', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)


class AuditInventory(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsAuditor)

    def get(self, request):

        info_logger.info("AuditInventory GET API called.")
        audit_no = request.GET.get('audit_no')
        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = AuditDetail.objects.filter(id=audit_no).last()
        if audit is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit_run = AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS).last()
        if audit_run is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['AUDIT_NOT_STARTED'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        bin_id = request.GET.get('bin_id')
        if not bin_id:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'bin_id', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        bin = Bin.objects.filter(warehouse=audit.warehouse, bin_id=bin_id).last()
        if bin is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'bin', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        sku = request.GET.get('sku')
        if not sku:
            batch_id = request.GET.get('batch_id')
            if not batch_id:
                msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'batch_id', 'data': None}
                return Response(msg, status=status.HTTP_200_OK)
        else:
            batch_id = BinInventory.objects.filter(bin=bin, sku=sku).last().batch_id
        warehouse = audit.warehouse
        bin_inventory_dict = self.get_bin_inventory(warehouse, batch_id, bin)
        data = {'bin_id': bin_id, 'batch_id': batch_id,
                'inventory': bin_inventory_dict}
        msg = {'is_success': True, 'message': 'OK', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        info_logger.info("AuditInventory POST API called.")
        audit_no = request.data.get('audit_no')
        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = AuditDetail.objects.filter(id=audit_no).last()
        if audit is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit_run = AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS).last()
        if audit_run is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['AUDIT_NOT_STARTED'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        bin_id = request.data.get('bin_id')
        if not bin_id:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'bin_id', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        bin = Bin.objects.filter(warehouse=audit.warehouse, bin_id=bin_id).last()
        if bin is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'bin', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        batch_id = request.data.get('batch_id')
        if not batch_id:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'batch_id', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        old_inventory = request.data.get('system_inventory')
        if not old_inventory:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'system_inventory', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        physical_inventory = request.data.get('physical_inventory')
        if not physical_inventory:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'physical_inventory', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        warehouse = audit.warehouse
        sku = BinInventory.objects.filter(batch_id=batch_id, bin=bin).last().sku
        current_inventory = self.get_bin_inventory(warehouse, batch_id, bin)
        is_update_done = False
        is_inventory_changed = False
        for key, value in current_inventory.items():
            if value != old_inventory[key]:
                is_inventory_changed = True
                break
        if is_inventory_changed:
            data = {'is_update_done': is_update_done, 'is_inventory_changed': is_inventory_changed,
                    'bin_id': bin_id, 'batch_id': batch_id,
                    'inventory': current_inventory}
            msg = {'is_success': True, 'message': 'OK', 'data': data}
            return Response(msg, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                inventory_state = InventoryState.objects.filter(inventory_state='available').last()
                for inv_type, qty in physical_inventory.items():
                    inventory_type = InventoryType.objects.filter(inventory_type=inv_type).last()
                    if self.picklist_cancel_required(warehouse, batch_id, bin,
                                                     inventory_type, qty):
                        self.cancel_picklist(audit, warehouse, batch_id, bin)
                        current_inventory = self.get_bin_inventory(warehouse, batch_id, bin)
                    self.log_audit_data(warehouse, audit_run, batch_id, bin, sku, inventory_type, inventory_state,
                                        current_inventory[inv_type], qty)
                    self.update_inventory(audit_no, warehouse, batch_id, bin, sku, inventory_type, inventory_state,
                                          current_inventory[inv_type], qty)
                is_update_done = True
        except Exception as e:
            error_logger.error(e)
            info_logger.error('AuditInventory | Exception while updating inventory')

        if not is_update_done:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['SOME_ISSUE'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            remaining_products_to_audit = self.get_remaining_products_to_audit(audit, audit_run)
            if sku not in remaining_products_to_audit:
                BlockUnblockProduct.unblock_product_after_audit(audit, sku, warehouse)
        if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            remaining_bins_to_audit = self.get_remaining_bins_to_audit(audit, audit_run, sku)
            if len(remaining_bins_to_audit) == 0:
                BlockUnblockProduct.unblock_product_after_audit(audit, sku, warehouse)

        current_inventory = self.get_bin_inventory(warehouse, batch_id, bin)
        data = {'is_update_done': is_update_done, 'is_inventory_changed': is_inventory_changed,
                'bin_id': bin_id, 'batch_id': batch_id,
                'inventory': current_inventory}
        msg = {'is_success': True, 'message': 'OK', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)


    def update_inventory(self, audit_no, warehouse, batch_id, bin, sku, inventory_type, inventory_state,
                                            expected_qty, physical_qty):
        info_logger.info('AuditInventory | update_inventory | started ')
        if expected_qty == physical_qty:
            info_logger.info('AuditInventory | update_inventory | Quantity matched, updated not required')
            return
        # if inventory_type.inventory_type == 'normal':
        #     pickup_qty = self.get_pickup_blocked_quantity(warehouse, batch_id, bin)
        #     info_logger.info('AuditInventory | update_inventory | pickup blocked quantity-{}'.format(pickup_qty))
        #     if physical_qty >= pickup_qty:
        #         physical_qty = physical_qty - pickup_qty
        #     else:
        #         physical_qty = 0
        qty_diff = physical_qty-expected_qty
        tr_type = 'manual_audit_add'
        if qty_diff < 0:
            tr_type = 'manual_audit_deduct'

        CommonBinInventoryFunctions.update_or_create_bin_inventory(warehouse, bin, sku,
                                                                   batch_id, inventory_type, qty_diff, True)
        InternalInventoryChange.create_bin_internal_inventory_change(warehouse, sku, batch_id, bin,
                                                                     inventory_type,
                                                                     inventory_type, tr_type,
                                                                     audit_no, abs(qty_diff))

        # update warehouse inventory
        CommonWarehouseInventoryFunctions.create_warehouse_inventory(warehouse, sku, inventory_type, inventory_state,
                                                                     qty_diff, True)
        WareHouseInternalInventoryChange.create_warehouse_inventory_change(warehouse, sku,
                                                                           tr_type, audit_no,
                                                                           inventory_type, inventory_state,
                                                                           inventory_type, inventory_state,
                                                                           abs(qty_diff))
        info_logger.info('AuditInventory | update_inventory | completed')

    def log_audit_data(self, warehouse, audit_run, batch_id, bin, sku, inventory_type, inventory_state, expected_qty,
                       physical_qty):
        audit_status = AUDIT_STATUS_CHOICES.DIRTY
        if physical_qty == expected_qty:
            audit_status = AUDIT_STATUS_CHOICES.CLEAN
        AuditRunItem.objects.create(warehouse=warehouse,
                                    audit_run=audit_run,
                                    batch_id=batch_id,
                                    bin=bin,
                                    sku=sku,
                                    inventory_type=inventory_type,
                                    inventory_state=inventory_state,
                                    qty_expected=expected_qty,
                                    qty_calculated=physical_qty,
                                    status=audit_status)

    def get_bin_inventory(self, warehouse, batch_id, bin):
        normal_type = InventoryType.objects.filter(inventory_type='normal').last()
        damaged_type = InventoryType.objects.filter(inventory_type='damaged').last()
        expired_type = InventoryType.objects.filter(inventory_type='expired').last()
        inv_type_list = [normal_type, damaged_type, expired_type]
        bin_inventory = BinInventory.objects.filter(bin=bin, batch_id=batch_id,
                                                    inventory_type__in=inv_type_list) \
                                            .values('inventory_type__inventory_type', 'quantity')
        bin_inventory_dict = {g['inventory_type__inventory_type']: g['quantity'] for g in bin_inventory}
        self.initialize_inventory_dict(bin_inventory_dict, inv_type_list)
        pickup_qty = self.get_pickup_blocked_quantity(warehouse,batch_id, bin)
        info_logger.info('AuditInventory | get_bin_inventory | Bin Inventory {}, pickup blocked quantity-{}'
                         .format(bin_inventory_dict, pickup_qty))
        bin_inventory_dict['normal'] += pickup_qty
        return bin_inventory_dict

    def initialize_inventory_dict(self, bin_inventory_dict, inv_type_list):
        for i in inv_type_list:
            if bin_inventory_dict.get(i.inventory_type) is None:
                bin_inventory_dict[i.inventory_type] = 0

    def get_pickup_blocked_quantity(self, warehouse, batch_id, bin):
        pickup_qty = 0
        pickup_qs = PickupBinInventory.objects.filter(warehouse=warehouse, bin__bin_id=bin, batch_id=batch_id,
                                                      pickup__status__in=['pickup_creation', 'picking_assigned']) \
                                              .annotate(pickup_qty=Sum('quantity'))
        if pickup_qs.count() > 0:
            pickup_qty = pickup_qs.last().pickup_qty
        return pickup_qty


    def get_remaining_bins_to_audit(self, audit, audit_run, sku):
        bin_and_batches_to_audit = BinInventory.objects.filter(warehouse=audit.warehouse,
                                                               sku=sku)\
                                                       .values_list('bin_id', 'batch_id', 'sku_id')
        bin_batches_audited = AuditRunItem.objects.filter(audit_run=audit_run)\
                                                  .values_list('bin_id', 'batch_id', 'sku_id')

        remaining_bin_batches_to_audit = list(set(bin_and_batches_to_audit) - set(bin_batches_audited))
        info_logger.info('AuditInventory|get_remaining_bins_to_audit|remaining_bin_batches_to_audit-{}'
                         .format(remaining_bin_batches_to_audit))
        return remaining_bin_batches_to_audit

    def get_remaining_products_to_audit(self, audit, audit_run):
        all_bins_to_audit = audit.bin.all()
        bin_and_batches_to_audit = BinInventory.objects.filter(warehouse=audit.warehouse,
                                                               bin__in=all_bins_to_audit)\
                                                       .values_list('bin_id', 'batch_id', 'sku_id')

        bin_batches_audited = AuditRunItem.objects.filter(audit_run=audit_run)\
                                                  .values_list('bin_id', 'batch_id', 'sku_id')
        remaining_bin_batches_to_audit = list(set(bin_and_batches_to_audit) - set(bin_batches_audited))
        remaining_skus_to_audit = [item[2] for item in remaining_bin_batches_to_audit]
        info_logger.info('AuditInventory|get_remaining_products_to_audit|remaining_skus_to_audit-{}'
                         .format(remaining_skus_to_audit))
        return remaining_skus_to_audit

    def picklist_cancel_required(self, warehouse, batch_id, bin, inventory_type, physical_qty):
        if inventory_type.inventory_type != 'normal':
            return False

        pickup_qty = self.get_pickup_blocked_quantity(warehouse,batch_id, bin)
        if physical_qty - pickup_qty >= 0:
            return False
        return True

    def cancel_picklist(self, audit, warehouse, batch_id, bin):
        pickup_bin_qs = PickupBinInventory.objects.filter(warehouse=warehouse, batch_id=batch_id, bin__bin_id=bin,
                                                          pickup__status__in=['pickup_creation', 'picking_assigned'])
        orders_to_cancel_picklist = set()
        with transaction.atomic():
            for pb in pickup_bin_qs:
                orders_to_cancel_picklist.add(pb.pickup.pickup_type_id)
                acp = AuditCancelledPicklist.objects.get_or_create(audit=audit, order_no=pb.pickup.pickup_type_id)
                info_logger.info('AuditInventory|cancel_picklist| audit no {}, order no {}'
                                 .format(acp.audit.audit_no, pb.pickup.pickup_type_id))
        PicklistRefresh.cancel_picklist_by_order(orders_to_cancel_picklist)
        info_logger.info('AuditInventory|cancel_picklist|picklist cancelled')
