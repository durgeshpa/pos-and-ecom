import logging
from datetime import timedelta, timezone, datetime

from django.db import transaction
from django.db.models import Count
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework import status, mixins
from rest_framework.views import APIView
from rest_framework import permissions, authentication

# Logger
from rest_framework.viewsets import GenericViewSet

from retailer_backend import settings
from retailer_backend.messages import ERROR_MESSAGES
from wms.models import BinInventory, Bin, InventoryType
from .serializers import AuditDetailSerializer
from ...models import AuditDetail, AUDIT_DETAIL_STATUS_CHOICES, AUDIT_TYPE_CHOICES, AUDIT_DETAIL_STATE_CHOICES, \
    AuditRun, AUDIT_RUN_STATUS_CHOICES, AUDIT_LEVEL_CHOICES, AuditRunItem
from ...tasks import update_audit_status

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class AuditListView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        info_logger.info("Audit detail GET API called.")

        # warehouse = request.GET.get('warehouse')
        # if not warehouse:
        #     msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'warehouse', 'data': None}
        #     return Response(msg, status=status.HTTP_200_OK)

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
    permission_classes = (permissions.IsAuthenticated,)

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
        if self.can_start_audit(audit):
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['INVALID_STATE_TRANSITION'] % AUDIT_DETAIL_STATE_CHOICES[AUDIT_DETAIL_STATE_CHOICES.INITIATED],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        self.initiate_audit(audit)
        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def can_start_audit(self, audit):
        return (audit.created_at > datetime.now() - timedelta(minutes=30))

    @transaction.atomic
    def initiate_audit(self, audit):
        AuditRun.objects.create(warehouse=audit.warehouse, audit=audit,
                                status=AUDIT_RUN_STATUS_CHOICES.IN_PROGRESS)
        audit.state = AUDIT_DETAIL_STATE_CHOICES.INITIATED
        audit.save()


class AuditEndView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

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
                   'message': ERROR_MESSAGES['INVALID_AUDIT_STATE'] % AUDIT_DETAIL_STATE_CHOICES[AUDIT_DETAIL_STATE_CHOICES.ENDED],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        if self.can_audit_end(audit):
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['INVALID_AUDIT_STATE'] % AUDIT_DETAIL_STATE_CHOICES[AUDIT_DETAIL_STATE_CHOICES.ENDED],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        is_ended = self.end_audit(audit)
        if not is_ended:
            msg = {'is_success': False,
                   'message': ERROR_MESSAGES['FAILED_STATE_CHANGE'],
                   'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def can_end_audit(self, audit):
        if audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
            return self.can_end_bin_audit(audit)
        elif audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
            return self.can_end_product_audit(audit)

    def can_end_bin_audit(self, audit):
        expected_bin_count = len(audit.bin)
        audit_run = AuditRun.objects.filter(audit=audit)
        audited_bin_count = AuditRunItem.objects.filter(audit_run=audit_run).annotate(count=Count('bin_id', distinct=True))
        if expected_bin_count != audited_bin_count:
            return False
        return True

    def can_end_product_audit(self, audit):
        expected_bin_count = BinInventory.objects.filter(sku_id=audit.sku)\
                                                 .annotate(count=Count('bin_id', distinct=True))
        audit_run = AuditRun.objects.filter(audit=audit)
        audited_bin_count = AuditRunItem.objects.filter(audit_run=audit_run)\
                                                .annotate(count=Count('bin_id', distinct=True))
        if expected_bin_count != audited_bin_count:
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


class AuditBinList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        info_logger.info("AuditBinList GET API called.")
        audit_no = request.GET.get('audit_no')
        if not audit_no:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        audit = AuditDetail.objects.filter(id=audit_no).last()
        if audit is None:
            msg = {'is_success': True, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        else:
            bins_to_audit = []
            if audit.audit_level == AUDIT_LEVEL_CHOICES.PRODUCT:
                if audit.sku is not None:
                    bin_ids = BinInventory.objects.filter(sku=audit.sku).values_list('bin_id', flat=True)
                    bins_to_audit = Bin.objects.filter(id__in=bin_ids).values_list('bin_id', flat=True)
            elif audit.audit_level == AUDIT_LEVEL_CHOICES.BIN:
                bins_to_audit = audit.bin.all().values_list('bin_id', flat=True)
            data = {'bin_count': len(bins_to_audit), 'sku_to_audit': audit.sku.__str__() if audit.sku else None,
                    'bins_to_audit': bins_to_audit}
            msg = {'is_success': True, 'message': 'OK', 'data': data}
            return Response(msg, status=status.HTTP_200_OK)


class AuditInventory(APIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):

        info_logger.info("AuditInventory GET API called.")
        # audit_no = request.GET.get('audit_no')
        # if not audit_no:
        #     msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'audit_no', 'data': None}
        #     return Response(msg, status=status.HTTP_200_OK)
        # audit = AuditDetail.objects.filter(id=audit_no).last()
        # if audit is None:
        #     msg = {'is_success': True, 'message': ERROR_MESSAGES['NO_RECORD'] % 'audit', 'data': None}
        #     return Response(msg, status=status.HTTP_200_OK)
        bin_id = request.GET.get('bin_id')
        if not bin_id:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'bin_id', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        bin = Bin.objects.filter(bin_id=bin_id).last()
        if bin is None:
            msg = {'is_success': True, 'message': ERROR_MESSAGES['NO_RECORD'] % 'bin', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        batch_id = request.GET.get('batch_id')
        if not batch_id:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'batch_id', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        bin_inventory = BinInventory.objects.filter(bin=bin, batch_id=batch_id)\
                                            .values('inventory_type__inventory_type', 'quantity')
        bin_inventory_dict =  {g['inventory_type__inventory_type']: g['quantity'] for g in bin_inventory}
        data = {'bin_id': bin_id, 'batch_id': batch_id,
                'inventory': bin_inventory_dict}
        msg = {'is_success': True, 'message': 'OK', 'data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self):
        pass