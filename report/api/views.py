# -*- coding: utf-8 -*-
from re import U
import requests
import io

from django.http import FileResponse

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from common.data_wrapper_view import (DataWrapperListRetrieveViewSet,
                                      DataWrapperCreateUpdateViewSet,
                                      DataWrapperView)
from report.api.serializers import (AsyncReportListSerializer,
                                    AsyncReportRetrieveSerializer,
                                    AsyncReportModelSerializer)
from retailer_backend.utils import SmallOffsetPagination
from report.models import AsyncReportRequest

class AsyncReportListRetrieveView(DataWrapperListRetrieveViewSet):
    
    pagination_class = SmallOffsetPagination
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            user = self.request.query_params.get('user_id')
            if user:
                reports = AsyncReportRequest.objects.filter(user_id=user).order_by('-created_at')
            else:
                reports = AsyncReportRequest.objects.order_by('-created_at')
        else:
            reports = AsyncReportRequest.objects.filter(user=self.request.user).order_by('-created_at')
        
        report_name = self.request.query_params.get('report_name')
        report_type = self.request.query_params.get('report_type')
        if report_name:
            reports = reports.filter(report_name=report_name)
        if report_type:
            reports = reports.filter(report_type=report_type)
        return reports
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AsyncReportListSerializer
        if self.action == 'retrieve':
            return AsyncReportRetrieveSerializer
        return AsyncReportListSerializer


class AsyncReportFileView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def get(self, request, *args, **kwargs):
        try:
            report = AsyncReportRequest.objects.get(id=kwargs.get('id'))
            if report.report:
                with requests.Session() as s:
                    response = s.get(report.report.url)
                    response =  FileResponse(io.BytesIO(response.content), content_type='text/csv')
                    response['Content-Length'] = response['Content-Length']
                    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % report.rid
                    return response 
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        except AsyncReportRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class AsyncReportCreateUpdateView(DataWrapperCreateUpdateViewSet):
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = AsyncReportModelSerializer
    
    def get_queryset(self):
        return AsyncReportRequest.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
    