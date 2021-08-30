import logging
from datetime import timedelta, datetime

from decouple import config
from django.db import transaction
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework import status, mixins
from rest_framework.views import APIView
from rest_framework import permissions, authentication

from products.models import Product
from retailer_backend.messages import ERROR_MESSAGES, SUCCESS_MESSAGES
from wms.common_functions import InternalInventoryChange, \
    CommonWarehouseInventoryFunctions, CommonBinInventoryFunctions, InCommonFunctions, PutawayCommonFunctions, \
    get_expiry_date, get_manufacturing_date
from wms.models import BinInventory, Bin, InventoryType, PickupBinInventory, WarehouseInventory, InventoryState, Pickup, \
    BinInternalInventoryChange, In, Out, PutawayBinInventory
from wms.views import PicklistRefresh
from .serializers import AuditDetailSerializer
from ...cron import release_products_from_audit
from ...models import AuditDetail, AUDIT_DETAIL_STATUS_CHOICES, AUDIT_RUN_TYPE_CHOICES, AUDIT_DETAIL_STATE_CHOICES, \
    AuditRun, AUDIT_RUN_STATUS_CHOICES, AUDIT_LEVEL_CHOICES, AuditRunItem, AUDIT_STATUS_CHOICES, AuditCancelledPicklist, \
    AuditedBinRecord, AuditedProductRecord, AuditUpdatedPickup
from ...tasks import update_audit_status, generate_pick_list, create_audit_tickets
from ...utils import is_audit_started, is_diff_batch_in_this_bin, get_product_image, get_audit_start_time
from ...views import BlockUnblockProduct, create_pick_list_by_audit, create_audit_tickets_by_audit, \
    update_audit_status_by_audit
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
                                            audit_run_type=AUDIT_RUN_TYPE_CHOICES.MANUAL,
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
    try:
        audit_start_time_buffer_mins = int(config('AUDIT_START_BUFFER_MINS'))
    except:
        audit_start_time_buffer_mins = 15

    def post(self, request):
        info_logger.info("Audit Start API called.")

        audit_no = request.data.get('audit_no')

        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(audit_no=audit_no, auditor=request.user,
                                            audit_run_type=AUDIT_RUN_TYPE_CHOICES.MANUAL,
                                            status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
        count = audits.count()
        if count == 0:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = audits.last()
        if audit.state != AUDIT_DETAIL_STATE_CHOICES.CREATED:
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['AUDIT_STARTED'],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if not self.can_start_audit(audit):
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['AUDIT_START_TIME_ERROR']
                       .format(self.audit_start_time_buffer_mins,
                               self.audit_start_time(audit).strftime("%d/%m/%Y, %H:%M:%S")),
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        self.initiate_audit(audit)
        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def can_start_audit(self, audit):
        return (audit.created_at <= datetime.now() - timedelta(minutes=self.audit_start_time_buffer_mins))

    def audit_start_time(self, audit):
        return audit.created_at + timedelta(minutes=self.audit_start_time_buffer_mins)

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
        info_logger.info("AuditEndView GET API called.")

        audit_no = request.GET.get('audit_no')

        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(audit_no=audit_no, auditor=request.user,
                                            audit_run_type=AUDIT_RUN_TYPE_CHOICES.MANUAL,
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
        try:
            can_audit_end = self.can_end_audit(audit)
        except Exception as e:
            can_audit_end = False
            error_logger.error(e)
            info_logger.error("AuditEndView|Exception in can_end_audit")
        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': {'audit_detail': serializer.data,
                                                             'can_audit_end': can_audit_end}}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        info_logger.info("AuditEndView POST API called.")

        audit_no = request.data.get('audit_no')

        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(audit_no=audit_no, auditor=request.user,
                                            audit_run_type=AUDIT_RUN_TYPE_CHOICES.MANUAL,
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
        audit_run = AuditRun.objects.filter(audit=audit).last()
        sku = request.data.get('sku')
        bin_id = request.data.get('bin_id')

        if sku is None and bin_id is None:
            if not self.can_end_audit(audit):
                error_msg = ERROR_MESSAGES['FAILED_STATE_CHANGE']
                if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
                    error_msg = ERROR_MESSAGES['AUDIT_END_FAILED'].format('SKUs')
                elif audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
                    error_msg = ERROR_MESSAGES['AUDIT_END_FAILED'].format('BINs')
                msg = {'is_success': False,
                       'message': error_msg,
                       'data': None}
                return Response(msg, status=status.HTTP_200_OK)

        end_audit_for_skus = []
        end_audit_for_bins = []

        if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            audit_skus = audit.sku.all().values_list('product_sku', flat=True)
            if sku:
                if sku not in audit_skus:
                    msg = {'is_success': False,
                           'message': ERROR_MESSAGES['AUDIT_SKU_NOT_IN_SCOPE'],
                           'data': None}
                    return Response(msg, status=status.HTTP_200_OK)
                end_audit_for_skus.append(sku)
            else:
                end_audit_for_skus.extend(audit_skus)

        if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            audit_bins = audit.bin.all().values_list('bin_id', flat=True)
            if bin_id:
                if bin_id not in audit_bins:
                    msg = {'is_success': False,
                           'message': ERROR_MESSAGES['AUDIT_BIN_NOT_IN_SCOPE'],
                           'data': None}
                    return Response(msg, status=status.HTTP_200_OK)
                end_audit_for_bins.append(bin_id)
            else:
                end_audit_for_bins.extend(audit_bins)

        try:
            if len(end_audit_for_bins) > 0:
                for b in end_audit_for_bins:
                    self.end_audit_for_bin(audit, audit_run, b)
                    info_logger.info('AuditEndView|Audit {}, ended for bin-{}'.format(audit_no, b))
            elif len(end_audit_for_skus) > 0:
                for s in end_audit_for_skus:
                    self.end_audit_for_sku(audit, audit_run, s)
                    info_logger.info('AuditEndView|Audit {}, ended for sku-{}'.format(audit_no, s))
            if sku:
                msg = {'is_success': True,
                       'message': SUCCESS_MESSAGES['AUDIT_ENDED_SKU'].format(sku),
                       'data': None}
                return Response(msg, status=status.HTTP_200_OK)
            elif bin_id:
                msg = {'is_success': True,
                       'message': SUCCESS_MESSAGES['AUDIT_ENDED_BIN'].format(bin_id),
                       'data': None}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                self.end_audit(audit)
                info_logger.info('AuditEndView|Audit {}, ended '.format(audit_no))
                serializer = AuditDetailSerializer(audit)
                msg = {'is_success': True, 'message': 'OK', 'data': {'audit_detail': serializer.data}}
                return Response(msg, status=status.HTTP_200_OK)
        except Exception as e:
            error_logger.error(e)
            info_logger.info('AuditEndView|Exception while ending Audit {}' .format(audit_no))
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['SOME_ISSUE'],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        # if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
        #     sku = request.data.get('sku')
        #     if sku:
        #         audit_skus = audit.sku.all().values_list('product_sku', flat=True)
        #         if sku in audit_skus:
        #             try:
        #                 self.end_audit_for_sku(audit, audit_run, sku)
        #             except Exception as e:
        #                 error_logger.error(e)
        #                 info_logger.info('AuditEndView|Exception while ending audit for Audit {}, sku-{}'
        #                                  .format(audit_no, sku))
        #                 msg = {'is_success': False,
        #                        'message': ERROR_MESSAGES['SOME_ISSUE'],
        #                        'data': None}
        #                 return Response(msg, status=status.HTTP_200_OK)
        #             info_logger.info('AuditEndView|Audit {}, ended for sku-{}'.format(audit_no, sku))
        #             msg = {'is_success': True,
        #                    'message': SUCCESS_MESSAGES['AUDIT_ENDED_SKU'].format(sku),
        #                    'data': None}
        #             return Response(msg, status=status.HTTP_200_OK)
        #
        #         msg = {'is_success': False,
        #                'message': ERROR_MESSAGES['AUDIT_SKU_NOT_IN_SCOPE'],
        #                'data': None}
        #         return Response(msg, status=status.HTTP_200_OK)
        #
        # if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
        #     bin_id = request.data.get('bin_id')
        #     if bin_id:
        #         audit_bins = audit.bin.all().values_list('bin_id', flat=True)
        #         if bin_id in audit_bins:
        #             try:
        #                 self.end_audit_for_bin(audit, audit_run, bin_id)
        #             except Exception as e:
        #                 error_logger.error(e)
        #                 info_logger.info('AuditEndView|Exception while ending audit for Audit {}, bin-{}'.format(audit_no, bin_id))
        #                 msg = {'is_success': False,
        #                        'message': ERROR_MESSAGES['SOME_ISSUE'],
        #                        'data': None}
        #                 return Response(msg, status=status.HTTP_200_OK)
        #             info_logger.info('AuditEndView|Audit {}, ended for bin-{}'.format(audit_no, bin_id))
        #             msg = {'is_success': True,
        #                    'message': SUCCESS_MESSAGES['AUDIT_ENDED_BIN'].format(bin_id),
        #                    'data': None}
        #             return Response(msg, status=status.HTTP_200_OK)
        #
        #         msg = {'is_success': False,
        #                'message': ERROR_MESSAGES['AUDIT_BIN_NOT_IN_SCOPE'],
        #                'data': None}
        #         return Response(msg, status=status.HTTP_200_OK)

        # try:
        #     if not self.can_end_audit(audit):
        #         msg = {'is_success': False,
        #                'message': ERROR_MESSAGES['FAILED_STATE_CHANGE'],
        #                'data': None}
        #         return Response(msg, status=status.HTTP_200_OK)
        #
        #     self.end_audit(audit)
        # except Exception as e:
        #     error_logger.error(e)
        #     info_logger.error('AuditEndView|Exception in ending the audit-{}'.format(audit_no))
        #     msg = {'is_success': False,
        #            'message': ERROR_MESSAGES['SOME_ISSUE'],
        #            'data': None}
        #     return Response(msg, status=status.HTTP_200_OK)


    def can_end_audit(self, audit):
        if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            return self.can_end_bin_audit(audit)
        elif audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            return self.can_end_product_audit(audit)

    def can_end_bin_audit(self, audit):
        expected_bin_count = audit.bin.count()
        # audited_bin_count = AuditRunItem.objects.filter(audit_run__audit=audit).values('bin_id').distinct().count()
        audited_bin_count = AuditedBinRecord.objects.filter(audit=audit).values('bin_id').distinct().count()
        if expected_bin_count != audited_bin_count:
            return False
        return True

    def can_end_product_audit(self, audit):
        expected_sku_count = audit.sku.count()
        # audited_sku_count = AuditRunItem.objects.filter(audit_run__audit=audit).values('sku_id').distinct().count()
        audited_sku_count = AuditedProductRecord.objects.filter(audit=audit).values('sku_id').distinct().count()
        if expected_sku_count != audited_sku_count:
            return False
        return True

    @transaction.atomic
    def end_audit(self, audit):
        audit_run_qs = AuditRun.objects.filter(warehouse=audit.warehouse, audit=audit,
                                               status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        audit_run_qs.update(status=AUDIT_RUN_STATUS_CHOICES.COMPLETED, completed_at=timezone.now())
        audit.state = AUDIT_DETAIL_STATE_CHOICES.ENDED
        audit.save()
        update_audit_status_by_audit(audit.id)
        create_audit_tickets.delay(audit.id)
        # generate_pick_list.delay(audit.id)
        return True

    def end_audit_for_bin(self, audit, audit_run, bin_id):
        bin = Bin.objects.filter(bin_id=bin_id).last()
        if AuditedBinRecord.objects.filter(audit=audit, bin=bin).exists():
            info_logger.info('Audit {} for bin {}, already ended'.format(audit.id, bin_id))
            return
        info_logger.info('End audit {} for bin {}'.format(audit.id, bin_id))
        inventory_state = InventoryState.objects.filter(inventory_state='total_available').last()
        normal_type = InventoryType.objects.filter(inventory_type='normal').last()
        damaged_type = InventoryType.objects.filter(inventory_type='damaged').last()
        expired_type = InventoryType.objects.filter(inventory_type='expired').last()
        inv_type_list = [normal_type, damaged_type, expired_type]
        batches_audited = AuditRunItem.objects.filter(audit_run=audit_run, bin__bin_id=bin_id)\
                                              .values_list('batch_id', flat=True)
        bi_qs = BinInventory.objects.filter(warehouse=audit.warehouse, bin__bin_id=bin_id,
                                            inventory_type__in=inv_type_list,
                                            sku__product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL)
        for bi in bi_qs:
            if bi.batch_id in batches_audited:
                continue
            AuditInventory.log_audit_data(audit_run.warehouse, audit_run, bi.batch_id, bi.bin, bi.sku,
                                          bi.inventory_type, inventory_state, bi.quantity, 0)

            AuditInventory.update_inventory(audit.id, audit.warehouse, bi.batch_id, bi.bin, bi.sku,
                                            bi.inventory_type, inventory_state, bi.quantity, 0)

            BlockUnblockProduct.release_product_from_audit(audit, audit_run, bi.sku, audit.warehouse)
        AuditedBinRecord.objects.create(audit=audit, bin=bin)
        info_logger.info('End audit {} for bin {}'.format(audit.id, bin_id))

    def end_audit_for_sku(self, audit, audit_run, sku):
        if AuditedProductRecord.objects.filter(audit=audit, sku=sku).exists():
            info_logger.info('Audit {} for sku {}, already ended'.format(audit.id, sku))
            return
        info_logger.info('End audit {} for sku {}'.format(audit.id, sku))
        inventory_state = InventoryState.objects.filter(inventory_state='total_available').last()
        normal_type = InventoryType.objects.filter(inventory_type='normal').last()
        damaged_type = InventoryType.objects.filter(inventory_type='damaged').last()
        expired_type = InventoryType.objects.filter(inventory_type='expired').last()
        inv_type_list = [normal_type, damaged_type, expired_type]
        bins_audited = AuditRunItem.objects.filter(audit_run=audit_run, sku=sku)\
                                           .values_list('bin_id', flat=True)
        bi_qs = BinInventory.objects.filter(warehouse=audit.warehouse, sku_id=sku,
                                            inventory_type__in=inv_type_list,
                                            sku__product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL)
        for bi in bi_qs:
            if bi.bin_id in bins_audited:
                continue
            AuditInventory.log_audit_data(audit_run.warehouse, audit_run, bi.batch_id, bi.bin, bi.sku,
                                          bi.inventory_type, inventory_state, bi.quantity, 0)

            AuditInventory.update_inventory(audit.id, audit.warehouse, bi.batch_id, bi.bin, bi.sku,
                                            bi.inventory_type, inventory_state, bi.quantity, 0)
        product = Product.objects.filter(product_sku=sku).last()
        BlockUnblockProduct.release_product_from_audit(audit, audit_run, product, audit.warehouse)
        AuditedProductRecord.objects.create(audit=audit, sku_id=sku)
        info_logger.info('End audit {} for sku {}'.format(audit.id, sku))


class AuditBinList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsAuditor)

    def get(self, request):
        info_logger.info("AuditBinList GET API called.")
        audit_no = request.GET.get('audit_no')
        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = AuditDetail.objects.filter(audit_no=audit_no).last()
        if audit is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if not is_audit_started(audit):
            msg = {'is_success': False, 'message': ERROR_MESSAGES['AUDIT_NOT_STARTED'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audit_bins = []
        audit_skus = []
        if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            audit_skus = audit.sku.all().values('id', 'product_sku', 'product_name')
            # skus_audited = AuditRunItem.objects.filter(audit_run__audit=audit).values_list('sku__id', flat=True)
            skus_audited = AuditedProductRecord.objects.filter(audit=audit).values_list('sku__id', flat=True)
            for s in audit_skus:
                audit_done = False
                if s['id'] in skus_audited:
                    audit_done = True
                del s['id']
                s['audit_done'] = audit_done
        elif audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            audit_bins = audit.bin.all().values('bin_id')
            # bins_audited = AuditRunItem.objects.filter(audit_run__audit=audit).values_list('bin__bin_id', flat=True)
            bins_audited = AuditedBinRecord.objects.filter(audit=audit).values_list('bin__bin_id', flat=True)
            for b in audit_bins:
                audit_done = False
                if b['bin_id'] in bins_audited:
                    audit_done = True
                b['audit_done'] = audit_done
        audit_started_at = get_audit_start_time(audit)
        data = {'audit_no': audit_no, 'started_at': audit_started_at, 'current_time': timezone.now(),
                'bin_count': len(audit_bins), 'sku_count': len(audit_skus), 'sku_to_audit': audit_skus,
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
        audit = AuditDetail.objects.filter(audit_no=audit_no).last()
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
        product = Product.objects.filter(product_sku=audit_sku).last()
        if not product:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['SOME_ISSUE'] % 'sku', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        product_image = get_product_image(product)
        bin_ids = BinInventory.objects.filter(Q(quantity__gt=0) | Q(to_be_picked_qty__gt=0),
                                              sku__product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL,
                                              warehouse=audit.warehouse, sku=audit_sku).values_list('bin_id', flat=True)
        bins_to_audit = Bin.objects.filter(id__in=bin_ids).values('bin_id')
        bins_audited = AuditRunItem.objects.filter(audit_run__audit=audit, sku=audit_sku)\
                                           .values_list('bin__bin_id', flat=True)
        for b in bins_to_audit:
            audit_done = False
            if b['bin_id'] in bins_audited:
                audit_done = True
            b['audit_done'] = audit_done


        audit_started_at = get_audit_start_time(audit)
        data = {'audit_no': audit_no, 'started_at': audit_started_at, 'current_time': timezone.now(),
                'bin_count': len(bins_to_audit), 'sku': audit_sku, 'product_name': product.product_name,
                'product_mrp': product.product_mrp, 'product_image': product_image,
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
        audit = AuditDetail.objects.filter(audit_no=audit_no).last()
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
        product = self.get_sku_from_batch(batch_id)
        product_image = get_product_image(product)
        data = {'bin_id': bin_id, 'batch_id': batch_id, 'product_sku': product.product_sku,
                'product_name': product.product_name, 'product_mrp': product.product_mrp,
                'product_image': product_image, 'inventory': bin_inventory_dict}
        msg = {'is_success': True, 'message': 'OK', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request):
        info_logger.info("AuditInventory POST API called.")
        audit_no = request.data.get('audit_no')
        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = AuditDetail.objects.filter(audit_no=audit_no).last()
        if audit is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit_run = AuditRun.objects.filter(audit=audit, status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS).last()
        if audit_run is None:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['AUDIT_NOT_STARTED'], 'data': None}
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
        retry = request.data.get('retry')
        warehouse = audit.warehouse
        sku = self.get_sku_from_batch(batch_id)
        if not sku:
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['SOME_ISSUE'],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        expiry_date_string = get_expiry_date(batch_id)
        expiry_date = datetime.strptime(expiry_date_string, "%d/%m/%Y")

        if expiry_date > datetime.today():
            if physical_inventory['expired'] > 0:
                msg = {'is_success': False, 'message': ERROR_MESSAGES['EXPIRED_NON_ZERO'], 'data': None}
                return Response(msg, status=status.HTTP_200_OK)

        if expiry_date <= datetime.today():
            if (physical_inventory['normal']+physical_inventory['damaged']) > 0:
                msg = {'is_success': False, 'message': ERROR_MESSAGES['NORMAL_NON_ZERO'], 'data': None}
                return Response(msg, status=status.HTTP_200_OK)

        current_inventory = self.get_bin_inventory(warehouse, batch_id, bin)
        is_inventory_changed = False
        is_update_done = False
        for key, value in current_inventory.items():
            if value != old_inventory[key]:
                is_inventory_changed = True
                break
        if not retry:
            if is_inventory_changed:
                data = {'is_inventory_changed': is_inventory_changed,
                        'is_update_done': is_update_done,
                        'bin_id': bin_id, 'batch_id': batch_id,
                        'inventory': current_inventory}
                msg = {'is_success': True, 'message': 'OK', 'data': data}
                return Response(msg, status=status.HTTP_200_OK)

        for key, value in physical_inventory.items():
            if value > 0:
                if is_diff_batch_in_this_bin(warehouse, batch_id, bin, sku):
                    msg = {'is_success': False, 'message': ERROR_MESSAGES['DIFF_BATCH_ONE_BIN'], 'data': None}
                    return Response(msg, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                inventory_state = InventoryState.objects.filter(inventory_state='total_available').last()
                for inv_type, qty in physical_inventory.items():
                    inventory_type = InventoryType.objects.filter(inventory_type=inv_type).last()
                    if self.picklist_cancel_required(warehouse, batch_id, bin,
                                                     inventory_type, qty):
                        # self.cancel_picklist(audit, warehouse, batch_id, bin)
                        self.refresh_pickup_data(audit, warehouse, batch_id, bin, qty)
                        current_inventory = self.get_bin_inventory(warehouse, batch_id, bin)
                    elif qty > current_inventory[inv_type]:
                        add_on_qty = qty - current_inventory[inv_type]
                        self.refresh_pickup_data_on_qty_up(audit, warehouse, batch_id, bin, sku, add_on_qty,
                                                           inventory_type)
                        current_inventory = self.get_bin_inventory(warehouse, batch_id, bin)

                    self.log_audit_data(warehouse, audit_run, batch_id, bin, sku, inventory_type, inventory_state,
                                        current_inventory[inv_type], qty)
                    self.update_inventory(audit_no, warehouse, batch_id, bin, sku, inventory_type, inventory_state,
                                          current_inventory[inv_type], qty)
                BlockUnblockProduct.release_product_from_audit(audit, audit_run, sku, warehouse)
        except Exception as e:
            error_logger.error(e)
            info_logger.error('AuditInventory | Exception while updating inventory, bin_id-{}, batch_id-{}'
                              .format(bin_id, batch_id))
            msg = {'is_success': False, 'message': ERROR_MESSAGES['SOME_ISSUE'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        is_update_done = True
        current_inventory = self.get_bin_inventory(warehouse, batch_id, bin)
        data = {'is_inventory_changed': is_inventory_changed,
                'is_update_done': is_update_done,
                'bin_id': bin_id, 'batch_id': batch_id,
                'inventory': current_inventory}
        msg = {'is_success': True, 'message': 'OK', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def get_sku_from_batch(self, batch_id):
        sku = None
        # bin_inventory = BinInventory.objects.filter(batch_id=batch_id).last()
        # if bin_inventory:
        #     sku = bin_inventory.sku
        # else:
        #     in_entry = In.objects.filter(batch_id=batch_id).last()
        #     if in_entry:
        #         sku = in_entry.sku
        if not sku:
            sku_id = batch_id[:-6]
            sku = Product.objects.filter(product_sku=sku_id).last()
        return sku

    @staticmethod
    def update_inventory(audit_no, warehouse, batch_id, bin, sku, inventory_type, inventory_state,
                         expected_qty, physical_qty):
        info_logger.info('AuditInventory | update_inventory | started ')
        initial_inventory_type = InventoryType.objects.filter(inventory_type='new').last()
        if expected_qty == physical_qty:
            info_logger.info('AuditInventory | update_inventory | Quantity matched, updated not required')
            return
        qty_diff = physical_qty-expected_qty
        tr_type = 'manual_audit_add'
        if qty_diff < 0:
            tr_type = 'manual_audit_deduct'

        bin_inventory_object = CommonBinInventoryFunctions.update_or_create_bin_inventory(warehouse, bin, sku, batch_id,
                                                                                          inventory_type, qty_diff,
                                                                                          True)
        BinInternalInventoryChange.objects.create(warehouse=warehouse, sku=sku,
                                                  batch_id=batch_id,
                                                  final_bin=bin,
                                                  initial_inventory_type=initial_inventory_type,
                                                  final_inventory_type=inventory_type,
                                                  transaction_type=tr_type,
                                                  transaction_id=audit_no,
                                                  quantity=abs(qty_diff))

        ware_house_inventory_obj = WarehouseInventory.objects.filter(warehouse=warehouse, sku=sku,
                                                                     inventory_state=inventory_state,
                                                                     inventory_type=inventory_type,
                                                                     in_stock=True).last()
        if ware_house_inventory_obj:
            if ware_house_inventory_obj.quantity+qty_diff < 0:
                qty_diff = -1*ware_house_inventory_obj.quantity
        # update warehouse inventory
        if qty_diff != 0:
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(warehouse, sku,
                                                                                              inventory_type,
                                                                                              inventory_state,
                                                                                              qty_diff, tr_type,
                                                                                              audit_no)
        AuditInventory.create_in_out_entry(warehouse, sku, batch_id, bin_inventory_object, tr_type, audit_no,
                                           inventory_type, abs(qty_diff))
        info_logger.info('AuditInventory | update_inventory | completed')

    @staticmethod
    def log_audit_data(warehouse, audit_run, batch_id, bin, sku, inventory_type, inventory_state, expected_qty,
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
        bin_inventory = BinInventory.objects.filter(warehouse=warehouse, bin=bin, batch_id=batch_id,
                                                    sku__product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL,
                                                    inventory_type__in=inv_type_list) \
                                            .values('inventory_type__inventory_type', 'quantity', 'to_be_picked_qty')
        bin_inventory_dict = {g['inventory_type__inventory_type']: g['quantity']+g['to_be_picked_qty'] for g in bin_inventory}
        self.initialize_inventory_dict(bin_inventory_dict, inv_type_list)
        # pickup_qty = self.get_pickup_blocked_quantity(warehouse,batch_id, bin)
        # info_logger.info('AuditInventory | get_bin_inventory | Bin Inventory {}, pickup blocked quantity-{}'
        #                  .format(bin_inventory_dict, pickup_qty))
        # bin_inventory_dict['normal'] += pickup_qty
        return bin_inventory_dict

    def initialize_inventory_dict(self, bin_inventory_dict, inv_type_list):
        for i in inv_type_list:
            if bin_inventory_dict.get(i.inventory_type) is None:
                bin_inventory_dict[i.inventory_type] = 0

    def get_pickup_blocked_quantity(self, warehouse, batch_id, bin, inventory_type):
        bin_inv_qs = BinInventory.objects.filter(warehouse=warehouse, bin_id=bin, batch_id=batch_id,
                                                 inventory_type=inventory_type,
                                                 sku__product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL)
        if not bin_inv_qs.exists():
            return 0
        return bin_inv_qs.last().to_be_picked_qty

    def picklist_cancel_required(self, warehouse, batch_id, bin, inventory_type, physical_qty):
        pickup_qty = self.get_pickup_blocked_quantity(warehouse,batch_id, bin, inventory_type)
        if physical_qty - pickup_qty >= 0:
            return False
        return True

    def cancel_picklist(self, audit, warehouse, batch_id, bin):
        pickup_bin_qs = PickupBinInventory.objects.filter(warehouse=warehouse, batch_id=batch_id, bin__bin_id=bin,
                                                          pickup__status__in=['pickup_creation', 'picking_assigned'])
        with transaction.atomic():
            for pb in pickup_bin_qs:
                order_no = pb.pickup.pickup_type_id
                acp, i = AuditCancelledPicklist.objects.get_or_create(audit=audit, order_no=order_no)
                info_logger.info('AuditInventory|cancel_picklist| audit no {}, order no {}'
                                 .format(acp.audit.id,order_no))
                PicklistRefresh.cancel_picklist_by_order(order_no)

        info_logger.info('AuditInventory|cancel_picklist|picklist cancelled')


    def refresh_pickup_data(self, audit, warehouse, batch_id, bin, physical_qty):
        """
        For any given batch and bin, refresh the picklist based on available stock for this particular batch and bin
        """
        state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()
        state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
        pickup_bin_qs = PickupBinInventory.objects.select_for_update()\
                                                  .filter(warehouse=warehouse, batch_id=batch_id,
                                                          bin__bin_id=bin,
                                                          pickup__status__in=['pickup_creation',
                                                                              'picking_assigned']).order_by('id')

        with transaction.atomic():
            for pb in pickup_bin_qs:
                order_no = pb.pickup.pickup_type_id
                AuditUpdatedPickup.objects.create(audit=audit, order_no=order_no, batch_id=batch_id, bin=bin)
                info_logger.info('AuditInventory|refresh_pickup_data| audit no {}, batch id {}, bin id'
                                 .format(audit.id,batch_id, bin))
                picked_qty = pb.pickup_quantity if pb.pickup_quantity else 0
                if pb.quantity - picked_qty > physical_qty:
                    qty_diff = pb.quantity - (picked_qty + physical_qty)
                    pb.quantity = picked_qty + physical_qty
                    pb.save()
                    # update to be picked quantity in Bin as well as warehouse
                    CommonWarehouseInventoryFunctions\
                        .create_warehouse_inventory_with_transaction_log(warehouse, pb.pickup.sku,
                                                                         pb.pickup.inventory_type,
                                                                         state_to_be_picked,
                                                                         -1 * qty_diff, 'manual_audit_deduct',
                                                                         audit.audit_no)
                    CommonWarehouseInventoryFunctions \
                        .create_warehouse_inventory_with_transaction_log(warehouse, pb.pickup.sku,
                                                                         pb.pickup.inventory_type,
                                                                         state_total_available,
                                                                         -1 * qty_diff, 'manual_audit_deduct',
                                                                         audit.audit_no)
                    CommonBinInventoryFunctions.deduct_to_be_picked_from_bin(qty_diff, pb.bin)
                if physical_qty > 0:
                    physical_qty = physical_qty - (pb.quantity - picked_qty)

        info_logger.info('AuditInventory|cancel_picklist|picklist cancelled')


    @classmethod
    def create_in_out_entry(cls, warehouse, sku, batch_id, bin, tr_type, tr_type_id, inventory_type, qty):
        """
        This function creates entry in IN or OUT model based on tr_type (the transaction type)
        """
        if tr_type == 'manual_audit_deduct':
            Out.objects.create(warehouse=warehouse, out_type=tr_type, out_type_id=tr_type_id, sku=sku,
                               batch_id=batch_id, inventory_type=inventory_type, quantity=qty)
            info_logger.info('AuditInventory | update_inventory | OUT entry done ')
        elif tr_type == 'manual_audit_add':
            manufacturing_date = get_manufacturing_date(batch_id)
            InCommonFunctions.create_only_in(warehouse, tr_type, tr_type_id, sku, batch_id, qty, inventory_type,
                                             sku.weight_value, manufacturing_date)
            putaway_object = PutawayCommonFunctions.create_putaway(warehouse, tr_type, tr_type_id, sku, batch_id,
                                                                   qty, qty, inventory_type)
            PutawayBinInventory.objects.create(warehouse=warehouse, sku=sku, batch_id=batch_id, bin=bin,
                                               putaway_type=tr_type, putaway=putaway_object, putaway_status=True,
                                               putaway_quantity=qty)
            info_logger.info('AuditInventory | update_inventory | IN entry done ')

    @transaction.atomic
    def refresh_pickup_data_on_qty_up(self, audit, warehouse, batch_id, bin, sku, qty_added, inventory_type):

        info_logger.info('AuditInventory | refresh_pickup_data_on_qty_up | started ')
        state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()
        state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()

        # Get all the pickup entries where picklist quantity is less than ordered quantity
        pickup_bin_qs = PickupBinInventory.objects.filter(warehouse=warehouse, pickup__sku=sku,
                                                          pickup__inventory_type=inventory_type,
                                                          pickup__status__in=['pickup_creation', 'picking_assigned'])\
                                                  .values('pickup_id', 'pickup__inventory_type_id', 'pickup__quantity')\
                                                  .annotate(pickup_bin_inventory_qty=Sum('quantity'))\
                                                  .filter(~Q(pickup__quantity=F('pickup_bin_inventory_qty')))\
                                                  .order_by('pickup__id')
        for pickup_bin_entry in pickup_bin_qs:
            pickup_id = pickup_bin_entry['pickup_id']
            inventory_type = pickup_bin_entry['pickup__inventory_type_id']
            qty_diff = pickup_bin_entry['pickup__quantity'] - pickup_bin_entry['pickup_bin_inventory_qty']

            info_logger.info('AuditInventory | refresh_pickup_data_on_qty_up | pickup_id {}, qty_diff {} '
                             .format(pickup_id, qty_diff))
            # For a particular picklist get the entry for current batch and bin id if exists
            pick_bin_inventory = PickupBinInventory.objects.filter(pickup_id=pickup_id, batch_id=batch_id,
                                                                   bin__bin_id=bin).last()
            if pick_bin_inventory is None:
                bin_inv_obj, created = BinInventory.objects.get_or_create(warehouse=warehouse, bin=bin, sku=sku,
                                                                          batch_id=batch_id,
                                                                          inventory_type_id=inventory_type,
                                                                          defaults={'quantity': 0, 'in_stock':True},)
                pick_bin_inventory = PickupBinInventory(warehouse=warehouse, pickup_id=pickup_id, batch_id=batch_id,
                                                        quantity=0, bin=bin_inv_obj)
            # Check if pickup is already done for this batch bin combination
            if pick_bin_inventory.pickup_quantity and pick_bin_inventory.remarks:
                continue
            if qty_diff <= qty_added:
                addon_qty = qty_diff
                qty_added = qty_added - qty_diff
            else:
                addon_qty= qty_added
                qty_added = 0
            pick_bin_inventory.quantity = pick_bin_inventory.quantity + addon_qty
            pick_bin_inventory.save()

            CommonWarehouseInventoryFunctions \
                .create_warehouse_inventory_with_transaction_log(warehouse, sku,
                                                                 pick_bin_inventory.pickup.inventory_type,
                                                                 state_to_be_picked, addon_qty, 'manual_audit_add',
                                                                 audit.audit_no)
            CommonWarehouseInventoryFunctions \
                .create_warehouse_inventory_with_transaction_log(warehouse, sku,
                                                                 pick_bin_inventory.pickup.inventory_type,
                                                                 state_total_available, addon_qty, 'manual_audit_add',
                                                                 audit.audit_no)
            CommonBinInventoryFunctions.add_to_be_picked_to_bin(addon_qty, pick_bin_inventory.bin)

            if qty_added == 0:
                break

        info_logger.info('AuditInventory | refresh_pickup_data_on_qty_up | ended ')







