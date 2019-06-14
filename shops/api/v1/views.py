from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.response import Response
from .serializers import (RetailerTypeSerializer, ShopTypeSerializer,
        ShopSerializer, ShopPhotoSerializer, ShopDocumentSerializer, ShopUserMappingSerializer, SellerShopSerializer)
from shops.models import (RetailerType, ShopType, Shop, ShopPhoto, ShopDocument, ShopUserMapping)
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

class TeamListView(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': ["%s shops found" % (queryset.count())],
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)


class SellerShopView(generics.ListCreateAPIView):
    serializer_class = SellerShopSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Shop.objects.filter(shop_owner=user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': ["%s shops found" % (queryset.count())],
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if request.user.has_perm('shops.can_sales_person_add_shop'):
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

            return Response(msg,status=status.HTTP_200_OK)
        else:
            msg = {'is_success': False,
                   'message': "No permission to add shop",
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        shop = serializer.save(created_by=self.request.user,shop_owner= get_user_model().objects.get(phone_number=self.request.data['shop_owner']))
        return shop
