from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.response import Response
from .serializers import (RetailerTypeSerializer, ShopTypeSerializer,
        ShopSerializer, ShopPhotoSerializer, ShopDocumentSerializer, ShopTimingSerializer)
from shops.models import (RetailerType, ShopType, Shop, ShopPhoto, ShopDocument, ShopTiming)
from rest_framework import generics
from addresses.models import City, Area, Address
from rest_framework import status
from django.contrib.auth import get_user_model
from retailer_backend.messages import SUCCESS_MESSAGES, VALIDATION_ERROR_MESSAGES
from rest_framework.parsers import FormParser, MultiPartParser

User =  get_user_model()

class RetailerTypeView(generics.ListAPIView):
    queryset = RetailerType.objects.all()
    serializer_class = RetailerTypeSerializer
    permission_classes = (permissions.AllowAny,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': None,
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

class ShopTypeView(generics.ListAPIView):
    queryset = ShopType.objects.all()
    serializer_class = ShopTypeSerializer
    permission_classes = (permissions.AllowAny,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': None,
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

class ShopPhotoView(generics.ListCreateAPIView):
    serializer_class = ShopPhotoSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        user_shops = Shop.objects.filter(shop_owner=self.request.user)
        queryset = ShopPhoto.objects.filter(shop_name__in=user_shops)
        shop_id = self.request.query_params.get('shop_id', None)
        if shop_id is not None:
            queryset = queryset.filter(shop_name=shop_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True,
                    'message': ["Images uploaded successfully"],
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

class ShopDocumentView(generics.ListCreateAPIView):
    serializer_class = ShopDocumentSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user_shops = Shop.objects.filter(shop_owner=self.request.user)
        queryset = ShopDocument.objects.filter(shop_name__in=user_shops)
        shop_id = self.request.query_params.get('shop_id', None)
        if shop_id is not None:
            queryset = queryset.filter(shop_name=shop_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True,
                    'message': ["Images uploaded successfully"],
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

class ShopView(generics.ListCreateAPIView):
    serializer_class = ShopSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Shop.objects.filter(shop_owner=user)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': ["%s shops found" % (queryset.count())],
                'response_data': serializer.data }
        return Response(msg,
                        status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = self.perform_create(serializer)
        msg = {'is_success': True,
                'message': [SUCCESS_MESSAGES['USER_SHOP_ADDED']],
                'response_data': [{
                                    "id": shop.pk,
                                    "shop_id": shop.pk,
                                    "shop_name": shop.shop_name,
                                    }]}
        return Response(msg,
                        status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        shop = serializer.save(shop_owner=self.request.user)
        return shop

class ShopTimingView(generics.ListCreateAPIView):
    serializer_class = ShopTimingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        shop_id = self.kwargs.get('shop_id')
        return ShopTiming.objects.filter(shop_id=shop_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': ["shop timing data"],
                'response_data': serializer.data }
        return Response(msg,status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.is_valid():
            self.perform_create(serializer)
            msg = {'is_success': True, 'message': '', 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message':['shop, open_timing or closing_timing Required'], 'response_data': None}
        return Response(msg,status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        timing, created = ShopTiming.objects.update_or_create(shop_id=self.request.data['shop'],
                                                                defaults={
                                                                    'open_timing' : self.request.data['open_timing'],
                                                                    'closing_timing' : self.request.data['closing_timing'],
                                                                     'break_start_time': self.request.data['break_start_time'],
                                                                     'break_end_time': self.request.data['break_end_time'],
                                                                     'off_day': self.request.data['off_day'],
                                                                 })
