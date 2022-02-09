# -*- coding: utf-8 -*-
import requests
import io

from django.http import FileResponse

from rest_framework.views import APIView
from rest_framework import status, mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from common.data_wrapper_view import (DataWrapperListRetrieveViewSet,
                                      DataWrapperCreateUpdateViewSet,
                                      DataWrapperView)
from report.api.serializers import (ReportChoiceMetaSerializer, 
                                    ReportListSerializer,
                                    ReportRetrieveSerializer,
                                    ReportModelSerializer)
from retailer_backend.utils import SmallOffsetPagination
from report.models import ReportChoice, ReportRequest
from pos.common_functions import api_response

class ReportChoiceListView(DataWrapperListRetrieveViewSet):
    
    pagination_class = None
    authentication_class = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = ReportChoiceMetaSerializer
    
    def get_queryset(self):
        name = self.request.query_params.get('name')
        if name:
            choices = ReportChoice.objects.filter(name__icontains=name, 
                                                  is_active=True)
        else:
            choices = ReportChoice.objects.filter(is_active=True)
        return choices


class ReportListRetrieveView(DataWrapperListRetrieveViewSet):
    
    pagination_class = SmallOffsetPagination
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            user = self.request.query_params.get('user_id')
            if user:
                reports = ReportRequest.objects.filter(user_id=user).order_by('-created_at')
            else:
                reports = ReportRequest.objects.order_by('-created_at')
        else:
            reports = ReportRequest.objects.filter(user=self.request.user).order_by('-created_at')
        
        report_model = self.request.query_params.get('report_model')
        report_type = self.request.query_params.get('report_type')
        report_name = self.request.query_params.get('report_name')
        if report_name:
            reports = reports.filter(report_choice__name__icontains=report_name)
        if report_model:
            reports = reports.filter(report_choice__target_model=report_model)
        if report_type:
            reports = reports.filter(report_type=report_type)
        return reports
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        if self.action == 'retrieve':
            return ReportRetrieveSerializer
        return ReportListSerializer


class ReportFileView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def get(self, request, *args, **kwargs):
        try:
            report = ReportRequest.objects.get(id=kwargs.get('id'))
            if report.report:
                with requests.Session() as s:
                    response = s.get(report.report.url)
                    response =  FileResponse(io.BytesIO(response.content), content_type='text/csv')
                    response['Content-Length'] = response['Content-Length']
                    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % report.rid
                    return response 
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        except ReportRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class DownloadPrivateFileAws(APIView):
    
    def get(self, request):
        file_url = request.query_params.get('file')
        content_type = request.query_params.get('content_type')
        errors = {}
        if not file_url:
            errors['file'] = 'file url is required should be provided as params in request with key | file |'
        if not content_type:
            errors['content_type'] = 'content type is required should be provided as params in request with key | content_type |'
        if not errors:
            with requests.Session() as s:
                response = s.get(file_url)
                if response.status_code != 200:
                    errors['file'] = "download failed"
                    return Response({"message": [""], "response_data": errors, "is_success": False}, 
                            status=status.HTTP_400_BAD_REQUEST)
                response = FileResponse(io.BytesIO(response.content), content_type=content_type)
                response['Content-Length'] = response['Content-Length']
                file_name = file_url.split('/')
                response['Content-Disposition'] = 'attachment; filename="%s"' % file_name[-1]
                return response
        else:
            return Response({"message": [""], "response_data": errors, "is_success": False}, 
                            status=status.HTTP_400_BAD_REQUEST)


class ReportCreateUpdateView(mixins.CreateModelMixin, 
                            mixins.UpdateModelMixin, 
                            viewsets.GenericViewSet):
    
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = ReportModelSerializer
    
    def get_queryset(self):
        return ReportRequest.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            return api_response("Report successfully queued", 
                                data=serializer.data, 
                                status_code=status.HTTP_201_CREATED,
                                success=True)
        else:
            errors = [serializer.errors[error][0] for error in serializer.errors]
            errors = "\n".join(errors)
            return api_response(errors)