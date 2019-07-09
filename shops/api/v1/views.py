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
from retailer_to_sp.models import Order
from datetime import datetime, timedelta
from django.db.models import Sum,Q,Count

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
        employee_list = ShopUserMapping.objects.filter(manager=self.request.user)
        data = []
        days_diff = 7

        for employee in employee_list:
            today = datetime.now()
            last_day = today - timedelta(days=days_diff)
            orders = Order.objects.select_related('ordered_cart').filter(ordered_by=employee.employee, created_at__range=[last_day, today]).order_by('ordered_by')
            total_sku, total_invoice_amount, total_no_of_sku_pieces = 0, 0, 0
            dt = {
              'name': employee.employee.first_name,
              'data':[]
            }
            for order in orders:
                total_sku += int(order.ordered_cart.total_sku()) if order.ordered_cart.total_sku() else 0
                total_invoice_amount += round(float(order.ordered_amount()),2) if order.ordered_amount() else 0
                total_no_of_sku_pieces += round(float(order.ordered_cart.total_no_of_sku_pieces()),2) if order.ordered_cart.total_no_of_sku_pieces() else 0

            rt = {
                'ordered_sku_pieces' : total_no_of_sku_pieces,
                'ordered_amount': round(total_invoice_amount,2),
                'delivered_amount': round(total_invoice_amount,2),
                'store_added': employee.employee.shop_created_by.filter(created_at__range=[last_day, today]).count(),
                'avg_order_val': round(total_invoice_amount / int(days_diff),2) if total_invoice_amount >0 else 0,
                'avg_order_line_items': round(total_sku / int(days_diff),2) if total_sku >0 else 0,
                'unique_calls_made': '',
                'days': days_diff,
            }
            dt['data'].append(rt)
            data.append(dt)

        msg = {'is_success': True, 'message': [""],'response_data': None, 'data': data}
        return Response(msg,status=status.HTTP_200_OK)


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
        shop = serializer.save(created_by=self.request.user,shop_owner= get_user_model().objects.get(phone_number=self.request.data['shop_owner']),
                               shop_type=ShopType.objects.get(shop_type='r'))
        return shop

from datetime import datetime,timedelta
from django.db.models import Q,Sum,Count,F, FloatField
from retailer_to_sp.models import Order

class SellerShopOrder(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user)

    def list(self, request, *args, **kwargs):
        days_diff = 1 if self.request.query_params.get('day', None) is None else int(self.request.query_params.get('day'))
        employee_list = ShopUserMapping.objects.filter(manager=self.request.user).values('employee')
        shop_list = Shop.objects.filter(created_by__id__in=employee_list).values('shop_name','id').order_by('shop_name')

        data = []
        today = datetime.now()
        last_day = today - timedelta(days=days_diff)
        order_obj = Order.objects.filter(buyer_shop__created_by__id__in=employee_list,created_at__range=[today, last_day]).values('buyer_shop','buyer_shop__shop_name').\
            annotate(buyer_shop_count=Count('buyer_shop'))\
            .annotate(no_of_ordered_sku=Count('ordered_cart__rt_cart_list'))\
            .annotate(no_of_ordered_sku_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces'))\
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer')* F('ordered_cart__rt_cart_list__no_of_pieces'),
                                     output_field=FloatField()))\
            .order_by('buyer_shop')
        order_map = {i['buyer_shop']: (i['buyer_shop_count'], i['no_of_ordered_sku'], i['no_of_ordered_sku_pieces'],i['ordered_amount']) for i in order_obj}

        for shop in shop_list:
            dt = {
              'name': shop['shop_name'],
              'dt': []
            }
            rt = {
                'no_of_order': order_map[shop['id']][0] if order_map else 0,
                'no_of_ordered_sku': order_map[shop['id']][1] if order_map else 0,
                'no_of_ordered_sku_pieces': order_map[shop['id']][2] if order_map else 0,
                'ordered_amount': round(order_map[shop['id']][3],2) if order_map else 0,
                'calls_made': '',
            }
            dt['dt'].append(rt)
            data.append(dt)

        msg = {'is_success': True, 'message': [""],'response_data': data}
        return Response(msg,status=status.HTTP_200_OK)

from datetime import datetime,timedelta
from django.db.models import Q,Sum,Count,F, FloatField, Avg, DateTimeField
from retailer_to_sp.models import Order

class SellerShopProfile(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user)

    def list(self, request, *args, **kwargs):
        data = []
        employee_list = ShopUserMapping.objects.filter(manager=self.request.user).values('employee')
        shop_list = Shop.objects.filter(created_by__id__in=employee_list).values('shop_name','id').order_by('shop_name')
        order_obj = Order.objects.filter(buyer_shop__created_by__id__in=employee_list).order_by('buyer_shop').last()

        order_list = Order.objects.filter(buyer_shop__created_by__id__in=employee_list).values('buyer_shop','buyer_shop__shop_name').\
            annotate(buyer_shop_count=Count('buyer_shop'))\
            .annotate(no_of_ordered_sku=Avg('ordered_cart__rt_cart_list'))\
            .annotate(ordered_amount=Avg(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer')* F('ordered_cart__rt_cart_list__no_of_pieces'),
                                     output_field=FloatField()))\
            .order_by('buyer_shop')
        order_map = {i['buyer_shop']: (i['buyer_shop_count'], i['no_of_ordered_sku'], i['ordered_amount']) for i in order_list}

        for shop in shop_list:
            dt = {
              'name': shop['shop_name'],
              'dt': []
            }
            rt = {
                'last_order_date': order_obj.created_at.strftime('%d-%m-%Y %H:%M') if order_obj else 0,
                'last_order_value': order_obj.ordered_cart.subtotal if order_obj else 0,
                'avg_order_value': round(order_map[shop['id']][2], 2) if order_map else 0,
                'avg_ordered_sku': round(order_map[shop['id']][1], 0) if order_map else 0,
                'avg_time_between_order': '',
                'last_calls_made': '',
            }
            dt['dt'].append(rt)
            data.append(dt)

        msg = {'is_success': True, 'message': [""],'response_data': data}
        return Response(msg,status=status.HTTP_200_OK)
