import logging
from datetime import timedelta, timezone, datetime

from django.db import transaction
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework import status, mixins
from rest_framework.views import APIView
from rest_framework import permissions, authentication

# Logger
from rest_framework.viewsets import GenericViewSet

from retailer_backend import settings
from retailer_backend.messages import ERROR_MESSAGES
from .serializers import AuditDetailSerializer
from ...models import AuditDetail, AUDIT_DETAIL_STATUS_CHOICES, AUDIT_TYPE_CHOICES, AUDIT_DETAIL_STATE_CHOICES, \
    AuditRun, AUDIT_RUN_STATUS_CHOICES

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class AuditListView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        info_logger.info("Audit detail GET API called.")

        warehouse = request.GET.get('warehouse')
        auditor = request.GET.get('auditor')

        if not warehouse:
            msg = {'is_success': False, 'message': ERROR_MESSAGES['EMPTY'] % 'warehouse', 'data': None}
            return Response(msg, status=status.HTTP_200_OK)

        audits = AuditDetail.objects.filter(warehouse=warehouse, auditor=request.user,
                                            audit_type=AUDIT_TYPE_CHOICES.MANUAL,
                                            state__in=[AUDIT_DETAIL_STATE_CHOICES.CREATED,
                                                       AUDIT_DETAIL_STATE_CHOICES.INITIATED],
                                            status=AUDIT_DETAIL_STATUS_CHOICES.ACTIVE)
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
        info_logger.info("AuditUpdateView called.")

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
                   'message': ERROR_MESSAGES['INVALID_STATE_TRANSITION'],
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
        self.end_audit(audit)
        serializer = AuditDetailSerializer(audit)
        msg = {'is_success': True, 'message': 'OK', 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def can_end_audit(self, instance):
        pass

    @transaction.atomic
    def end_audit(self, instance):
        pass
