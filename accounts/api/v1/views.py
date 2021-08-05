import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import authentication, permissions, generics
from rest_framework.response import Response
from .serializers import (GroupSerializer, UserSerializer, UserDocumentSerializer, 
    AppVersionSerializer, DeliveryAppVersionSerializer)
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from accounts.models import UserDocument, AppVersion
from retailer_backend.utils import SmallOffsetPagination
from products.common_function import get_response, serializer_error
from accounts.services import group_search

User = get_user_model()

logger = logging.getLogger('accounts-api-v1')

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class UserDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get(self, request, format=None):
        user = UserSerializer(self.request.user)
        msg = {'is_success': True, 'message': None, 'response_data': user.data}
        return Response(msg, status=status.HTTP_200_OK)

    def put(self, request, format=None):
        user = self.request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True,
                    'message': ["User details updated!"],
                    'response_data': serializer.data}
            return Response(msg,
                            status=status.HTTP_200_OK)
        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)


class UserDocumentView(generics.ListCreateAPIView):
    serializer_class = UserDocumentSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        queryset = UserDocument.objects.filter(user=self.request.user)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=self.request.user)
            msg = {'is_success': True,
                    'message': ["Documents uploaded successfully"],
                    'response_data': None}
            return Response(msg,
                            status=status.HTTP_200_OK)
        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': ["%s objects found" % (queryset.count())],
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)


class CheckAppVersion(APIView):
    permission_classes = (AllowAny,)

    def get(self,*args, **kwargs):
        version = self.request.GET.get('app_version')
        msg = {'is_success': False, 'message': ['Please send version'], 'response_data': None}
        try:
            app_version = AppVersion.objects.get(app_version=version, app_type='retailer')
        except ObjectDoesNotExist:
            msg["message"] = ['App version not found']
            return Response(msg, status=status.HTTP_200_OK)

        app_version_serializer = AppVersionSerializer(app_version)
        return Response({"is_success": True, "message": [""], "response_data": app_version_serializer.data})


class CheckDeliveryAppVersion(APIView):
    permission_classes = (AllowAny,)

    def get(self,*args, **kwargs):
        version = self.request.GET.get('app_version')
        msg = {'is_success': False, 'message': ['Please send version'], 'response_data': None}
        try:
            app_version = AppVersion.objects.get(app_version=version, app_type='delivery')
        except ObjectDoesNotExist:
            msg["message"] = ['Delivery App version not found']
            return Response(msg, status=status.HTTP_200_OK)

        app_version_serializer = DeliveryAppVersionSerializer(app_version)
        return Response({"is_success": True, "message": [""], "response_data": app_version_serializer.data})


class GroupsListView(generics.ListAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (AllowAny,)

    # def list(self, request):
    #     queryset = self.get_queryset()
    #     group_serializer = self.get_serializer(queryset, many=True)
    #     return Response({"is_success": True, "message": [""], "response_data": group_serializer.data})

    def get(self, request):
        info_logger.info("Group GET api called.")
        """ GET Group List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = group_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no group found"
        return get_response(msg, serializer.data, True)
