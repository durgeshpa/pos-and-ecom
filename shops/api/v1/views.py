from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.response import Response
from .serializers import (RetailerTypeSerializer, ShopTypeSerializer,
    ShopSerializer, ShopPhotoSerializer, ShopDocumentSerializer, ShopUserMappingSerializer, SellerShopSerializer,
    AppVersionSerializer, ShopUserMappingUserSerializer
)
from shops.models import (RetailerType, ShopType, Shop, ShopPhoto, ShopDocument, ShopUserMapping, SalesAppVersion)
from rest_framework import generics
from addresses.models import City, Area, Address
from rest_framework import status
from django.contrib.auth import get_user_model
from retailer_backend.messages import SUCCESS_MESSAGES, VALIDATION_ERROR_MESSAGES
from rest_framework.parsers import FormParser, MultiPartParser
from retailer_to_sp.models import OrderedProduct
from retailer_to_sp.views import update_order_status

from datetime import datetime,timedelta, date
from django.db.models import Q,Sum,Count,F, FloatField, Avg
from retailer_to_sp.models import Order
from django.contrib.auth.models import Group
User =  get_user_model()
from addresses.api.v1.serializers import AddressSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist
from retailer_to_sp.models import OrderedProduct
from retailer_to_sp.views import update_order_status

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
        return ShopUserMapping.objects.filter(manager=self.request.user,status=True).order_by('employee').distinct('employee')

    def get_shops(self):
        return ShopUserMapping.objects.filter(manager=self.request.user,status=True).values('shop').order_by('shop').distinct('shop')

    def list(self, request, *args, **kwargs):
        days_diff = 1 if self.request.query_params.get('day', None) is None else int(self.request.query_params.get('day'))
        today = datetime.now()
        last_day = today - timedelta(days=days_diff)
        employee_list = self.get_queryset()
        shops_list = self.get_shops()
        data = []
        data_total = []
        order_obj = Order.objects.filter(buyer_shop__id__in=shops_list,
                                         created_at__date__lte=today, created_at__date__gte=last_day).values('ordered_by')\
            .annotate(no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(no_of_ordered_sku_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces')) \
            .annotate(avg_no_of_ordered_sku_pieces=Avg('ordered_cart__rt_cart_list__no_of_pieces')) \
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer') * F(
            'ordered_cart__rt_cart_list__no_of_pieces'),
                                         output_field=FloatField())) \
            .annotate(avg_ordered_amount=Avg(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer') * F(
            'ordered_cart__rt_cart_list__no_of_pieces'),
                                         output_field=FloatField())) \
            .order_by('ordered_by')

        avg_order_obj = Order.objects.filter(buyer_shop__id__in=shops_list, created_at__date__lte=today, created_at__date__gte=last_day).values('ordered_by') \
            .annotate(buyer_shop_count=Count('buyer_shop')) \
            .annotate(sum_no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer') * F(
            'ordered_cart__rt_cart_list__no_of_pieces'),output_field=FloatField())).order_by('ordered_by')

        buyer_order_obj = Order.objects.filter(buyer_shop__id__in=shops_list, created_at__date__lte=today, created_at__date__gte=last_day).values('buyer_shop').annotate(
            buyer_shop_count=Count('ordered_by')).order_by('ordered_by')

        print(order_obj.query)
        print("------------")

        print(avg_order_obj.query)
        print("------------")

        print(buyer_order_obj.query)
        print("------------")
        buyer_order_map = {i['buyer_shop']: (i['buyer_shop_count'],) for i in buyer_order_obj}
        avg_order_map = {i['buyer_shop']: (i['sum_no_of_ordered_sku'], i['ordered_amount']) for i in avg_order_obj}

        order_map = {i['buyer_shop']: (i['no_of_ordered_sku'], i['no_of_ordered_sku_pieces'], i['avg_no_of_ordered_sku_pieces'],
        i['ordered_amount'], i['avg_ordered_amount']) for i in order_obj}

        ordered_sku_pieces_total, ordered_amount_total, store_added_total, avg_order_total, avg_order_line_items_total, no_of_ordered_sku_total = 0,0,0,0,0,0

        for emp in employee_list:
            store_added = emp.employee.shop_created_by.filter(created_at__date__lte=today, created_at__date__gte=last_day).count()
            rt = {
                'ordered_sku_pieces': order_map[emp.shop.id][1] if emp.shop.id in order_map else 0,
                'ordered_amount': round(order_map[emp.shop.id][3], 2) if emp.shop.id in order_map else 0,
                'delivered_amount': 0,
                'store_added': store_added,
                'unique_calls_made': 0,
                'avg_order_val': round(avg_order_map[emp.shop.id][1] / buyer_order_map[emp.shop.id][0], 2) if emp.shop.id in buyer_order_map else 0,
                'avg_order_line_items': round(avg_order_map[emp.shop.id][0] / buyer_order_map[emp.shop.id][0], 2) if emp.shop.id in buyer_order_map else 0,
                'sales_person_name': emp.employee.get_full_name(),
                'no_of_ordered_sku': order_map[emp.shop.id][0] if emp.shop.id in order_map else 0,
            }
            data.append(rt)
            ordered_sku_pieces_total += order_map[emp.shop.id][1] if emp.shop.id in order_map else 0
            ordered_amount_total += round(order_map[emp.shop.id][3], 2) if emp.shop.id in order_map else 0
            store_added_total += store_added
            no_of_ordered_sku_total += order_map[emp.shop.id][0] if emp.shop.id in order_map else 0
            avg_order_total += round(avg_order_map[emp.shop.id][1] / buyer_order_map[emp.shop.id][0],2) if emp.shop.id in buyer_order_map else 0
            avg_order_line_items_total += round(avg_order_map[emp.shop.id][0] / buyer_order_map[emp.shop.id][0],2) if emp.shop.id in buyer_order_map else 0

            dt={
            'ordered_sku_pieces': ordered_sku_pieces_total,
            'ordered_amount': ordered_amount_total,
            'delivered_amount': 0,
            'store_added': store_added_total,
            'avg_order_val': avg_order_total,
            'avg_order_line_items': avg_order_line_items_total,
            'unique_calls_made': 0,
            'no_of_ordered_sku': no_of_ordered_sku_total,
        }
        data_total.append(dt)

        msg = {'is_success': True, 'message': [""],'response_data': data,'response_data_total':data_total}
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
        shop_user = ShopUserMapping.objects.filter(employee=request.user,status=True)
        if shop_user.exists() and shop_user.last().employee_group.permissions.filter(codename='can_sales_person_add_shop').exists():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            shop = self.perform_create(serializer)
            #self.add_shop_user_mapping(shop)
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
                   'message': ["No permission to add shop"],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        shop = serializer.save(created_by=self.request.user,shop_owner= get_user_model().objects.get(phone_number=self.request.data['shop_owner']))
        return shop

    # def add_shop_user_mapping(self,shop):
    #     if not ShopUserMapping.objects.filter(shop=shop,employee=self.request.user).exists():
    #         ShopUserMapping.objects.create(shop=shop, employee=self.request.user, employee_group=Group.objects.get(name='Sales Executive'))

class SellerShopOrder(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user,status=True)

    def list(self, request, *args, **kwargs):
        data = []
        data_total = []
        shop_user_obj = ShopUserMapping.objects.filter(employee=self.request.user,employee_group__permissions__codename='can_sales_person_add_shop',status=True)
        if not shop_user_obj:
            shop_user_obj = self.get_queryset()
        if not shop_user_obj.exists():
            msg = {'is_success': True, 'message': ["Sorry No matching user found"], 'response_data': data}
            return Response(msg, status=status.HTTP_200_OK)

        today = datetime.now()
        days_diff = 1 if self.request.query_params.get('day', None) is None else int(self.request.query_params.get('day'))
        last_day = today - timedelta(days=days_diff)
        shop_list = shop_user_obj.values('shop', 'shop__id', 'shop__shop_name').order_by('shop').distinct('shop')
        shops_list = shop_user_obj.values('shop').distinct('shop')
        order_obj = Order.objects.filter(buyer_shop__id__in=shops_list, created_at__date__lte=today, created_at__date__gte=last_day).values('buyer_shop','buyer_shop__shop_name').\
            annotate(buyer_shop_count=Count('buyer_shop'))\
            .annotate(no_of_ordered_sku=Count('ordered_cart__rt_cart_list'))\
            .annotate(no_of_ordered_sku_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces'))\
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer')* F('ordered_cart__rt_cart_list__no_of_pieces'),
                                     output_field=FloatField()))\
            .order_by('buyer_shop')

        buyer_order_obj = Order.objects.filter(buyer_shop__id__in=shops_list, created_at__date__lte=today,
                                         created_at__date__gte=last_day).values('buyer_shop').annotate(buyer_shop_count=Count('buyer_shop')).order_by('buyer_shop')

        buyer_order_map = {i['buyer_shop']: (i['buyer_shop_count'],) for i in buyer_order_obj}
        order_map = {i['buyer_shop']: (i['buyer_shop_count'], i['no_of_ordered_sku'], i['no_of_ordered_sku_pieces'],i['ordered_amount']) for i in order_obj}
        no_of_order_total, no_of_ordered_sku_total, no_of_ordered_sku_pieces_total, ordered_amount_total = 0, 0, 0, 0
        for shop in shop_list:
            rt = {
                'name': shop['shop__shop_name'],
                'no_of_order': buyer_order_map[shop['shop']][0] if shop['shop'] in buyer_order_map else 0,
                'no_of_ordered_sku': order_map[shop['shop']][1] if shop['shop'] in order_map else 0,
                'no_of_ordered_sku_pieces': order_map[shop['shop']][2] if shop['shop'] in order_map else 0,
                'ordered_amount': round(order_map[shop['shop']][3],2) if shop['shop'] in order_map else 0,
                'calls_made': 0,
                'delivered_amount': 0,
            }
            data.append(rt)

            no_of_order_total += buyer_order_map[shop['shop']][0] if shop['shop'] in buyer_order_map else 0
            no_of_ordered_sku_total += order_map[shop['shop']][1] if shop['shop'] in order_map else 0
            no_of_ordered_sku_pieces_total += order_map[shop['shop']][2] if shop['shop'] in order_map else 0
            ordered_amount_total += round(order_map[shop['shop']][3], 2) if shop['shop'] in order_map else 0

        dt = {
            'no_of_order': no_of_order_total,
            'no_of_ordered_sku': no_of_ordered_sku_total,
            'no_of_ordered_sku_pieces': no_of_ordered_sku_pieces_total,
            'ordered_amount': ordered_amount_total,
            'calls_made': 0,
            'delivered_amount': 0,
        }
        data_total.append(dt)
        msg = {'is_success': True, 'message': [""],'response_data': data, 'response_data_total':data_total}
        return Response(msg,status=status.HTTP_200_OK)

class SellerShopProfile(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user,status=True)

    def list(self, request, *args, **kwargs):
        data = []
        shop_user_obj = ShopUserMapping.objects.filter(employee=self.request.user, employee_group__permissions__codename='can_sales_person_add_shop', status=True)
        if not shop_user_obj:
            shop_user_obj = self.get_queryset()
        if not shop_user_obj.exists():
            msg = {'is_success': True, 'message': ["Sorry No matching user found"], 'response_data': data}
            return Response(msg, status=status.HTTP_200_OK)

        shop_list = shop_user_obj.values('shop','shop__id','shop__shop_name').order_by('shop').distinct('shop')
        shops_list = shop_user_obj.values('shop').distinct('shop')

        order_list = Order.objects.filter(buyer_shop__id__in=shops_list).values('buyer_shop', 'created_at').\
            annotate(buyer_shop_count=Count('buyer_shop'))\
            .annotate(sum_no_of_ordered_sku=Count('ordered_cart__rt_cart_list'))\
            .annotate(avg_ordered_amount=Avg(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer')* F('ordered_cart__rt_cart_list__no_of_pieces'),
                                     output_field=FloatField())) \
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer') * F(
            'ordered_cart__rt_cart_list__no_of_pieces'),
                                         output_field=FloatField())) \
        .order_by('buyer_shop','created_at')

        avg_order_obj = Order.objects.filter(buyer_shop__id__in=shops_list).values('buyer_shop') \
            .annotate(buyer_shop_count=Count('buyer_shop')) \
            .annotate(sum_no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer') * F('ordered_cart__rt_cart_list__no_of_pieces'),
                                         output_field=FloatField())).order_by('buyer_shop')

        buyer_order_obj = Order.objects.filter(buyer_shop__id__in=shops_list).values('buyer_shop').annotate(
            buyer_shop_count=Count('buyer_shop')).order_by('buyer_shop')

        buyer_order_map = {i['buyer_shop']: (i['buyer_shop_count'],) for i in buyer_order_obj}
        avg_order_map = {i['buyer_shop']: (i['sum_no_of_ordered_sku'], i['ordered_amount']) for i in avg_order_obj}
        order_map = {i['buyer_shop']: (i['buyer_shop_count'], i['sum_no_of_ordered_sku'], i['avg_ordered_amount'], i['created_at'], i['ordered_amount']) for i in order_list}

        for shop in shop_list:
            rt = {
                'name': shop['shop__shop_name'],
                'last_order_date': order_map[shop['shop']][3].strftime('%d-%m-%Y %H:%M') if shop['shop'] in order_map else 0,
                'last_order_value': round(order_map[shop['shop']][4], 2) if shop['shop'] in order_map else 0,
                'ordered_amount': avg_order_map[shop['shop']][1] if shop['shop'] in buyer_order_map else 0,
                'avg_order_value': round(avg_order_map[shop['shop']][1] / buyer_order_map[shop['shop']][0], 2) if shop['shop'] in buyer_order_map else 0,
                'sum_no_of_ordered_sku': avg_order_map[shop['shop']][0] if shop['shop'] in buyer_order_map else 0,
                'avg_ordered_sku': round(avg_order_map[shop['shop']][0] / buyer_order_map[shop['shop']][0], 2) if shop['shop'] in buyer_order_map else 0,
                'buyer_shop_count': buyer_order_map[shop['shop']][0] if shop['shop'] in buyer_order_map else 0,
                'avg_time_between_order': '',
                'last_calls_made': '',
            }
            data.append(rt)
            print(data)

        msg = {'is_success': True, 'message': [""],'response_data': data}
        return Response(msg,status=status.HTTP_200_OK)

class SalesPerformanceView(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        #return ShopUserMapping.objects.filter(employee_id=self.request.query_params.get('user_id', None), status=True).values('shop').order_by('shop').distinct('shop')
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True).values('shop').order_by('shop').distinct('shop')

    def list(self, request, *args, **kwargs):
        days_diff = 15 if self.request.query_params.get('day', None) is None else int(self.request.query_params.get('day'))
        data = []
        today = datetime.now()
        last_day = today - timedelta(days=days_diff)
        one_month = today - timedelta(days=days_diff + days_diff)
        print(self.get_queryset().query)
        if self.get_queryset():
            rt = {
                'name': request.user.get_full_name(),
                'shop_inactive': Order.objects.filter(buyer_shop__in=self.get_queryset()).exclude(created_at__date__lte=today, created_at__date__gte=last_day).count(),
                'shop_onboard': Shop.objects.filter(id__in=self.get_queryset(), status=True,created_at__date__lte=today,created_at__date__gte=last_day).count(),
                'shop_reactivated': Order.objects.filter(buyer_shop__in=self.get_queryset()).filter(~Q(created_at__date__lte=last_day, created_at__date__gte=one_month),
                    Q(created_at__date__lte=today, created_at__date__gte=last_day)).count(),
                'current_target_sales_target': '',
                'current_store_count': Shop.objects.filter(id__in=self.get_queryset(), created_at__date__lte=today, created_at__date__gte=last_day).count(),
            }
            data.append(rt)
            msg = {'is_success': True, 'message': [""], 'response_data': data}
        else:
            msg = {'is_success': False, 'message': ["User not exists"], 'response_data': None}
        return Response(msg,status=status.HTTP_200_OK)

class SalesPerformanceUserView(generics.ListAPIView):
    serializer_class = ShopUserMappingUserSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user,status=True).order_by('employee').distinct('employee')

    def list(self, request, *args, **kwargs):
        shop_emp = ShopUserMapping.objects.filter(employee=self.request.user,employee_group__permissions__codename='can_sales_person_add_shop', status=True)
        if not shop_emp:
            shop_mangr = self.get_queryset()
            msg = {'is_success': True, 'message': [""], 'response_data': self.get_serializer(shop_mangr, many=True).data, 'user_list': shop_mangr.values('employee')}
        elif shop_emp.exists():
            msg = {'is_success': True, 'message': [""], 'response_data': self.get_serializer(shop_emp).data, 'user_list':shop_emp.values('employee')}
        else:
            msg = {'is_success': False, 'message': ["User not exists"], 'response_data': None}
        return Response(msg,status=status.HTTP_200_OK)

class SellerShopListView(generics.ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AddressSerializer

    def get_queryset(self):
        shop_mapped = ShopUserMapping.objects.filter(employee=self.request.user).values('shop')
        shop_list = Address.objects.filter(shop_name__in=shop_mapped,address_type='shipping').order_by('created_at')
        if self.request.query_params.get('mobile_no'):
            shop_list = shop_list.filter(shop_name__shop_owner__phone_number__icontains=self.request.query_params.get('mobile_no'))
        if self.request.query_params.get('shop_name'):
            shop_list = shop_list.filter(shop_name__shop_name__icontains=self.request.query_params.get('shop_name'))
        if self.request.query_params.get('pin_code'):
            shop_list = shop_list.filter(pincode__icontains=self.request.query_params.get('pin_code'))
        if self.request.query_params.get('address'):
            shop_list = shop_list.filter(address_line1__icontains=self.request.query_params.get('address'))
        return shop_list.values('shop_name','shop_name__shop_name','shop_name__shop_owner__phone_number', 'address_line1', 'city__city_name', 'state__state_name', 'pincode', 'address_contact_name','address_contact_number').order_by('shop_name').distinct('shop_name')

    def list(self, request, *args, **kwargs):
        data = []
        queryset = self.get_queryset()
        for shop in queryset:
            dt = {
                'shop_id': shop['shop_name'],
                'shop_name': shop['shop_name__shop_name'],
                'retailer_contact_number': shop['shop_name__shop_owner__phone_number'],
                'address': shop['address_line1'],
                'city': shop['city__city_name'],
                'state': shop['state__state_name'],
                'pincode': shop['pincode'],
                'contact_name': shop['address_contact_name'],
                'contact_number': shop['address_contact_number'],
            }
            data.append(dt)
        is_success =False if not data else True
        msg = {'is_success': is_success, 'message': [""],'response_data': data}
        return Response(msg,status=status.HTTP_200_OK)


class CheckUser(generics.ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        all_user = ShopUserMapping.objects.filter(
            Q(employee=self.request.user) |
            Q(manager=self.request.user), status=True
        )
        if not all_user.exists():
            msg = {'is_success': False, 'message': ["Sorry you are not authorised"], 'response_data': None, 'is_sales': False,'is_sales_manager': False}
        else:
            is_sales = True if ShopUserMapping.objects.filter(employee=self.request.user, employee_group__permissions__codename='can_sales_person_add_shop',status=True).exists() else False
            is_sales_manager = True if ShopUserMapping.objects.filter(manager=self.request.user,status=True).exists() else False
            msg = {'is_success': True, 'message': [""], 'response_data': None,'is_sales':is_sales, 'is_sales_manager':is_sales_manager}
        return Response(msg, status=status.HTTP_200_OK)


class CheckAppVersion(APIView):
    permission_classes = (AllowAny,)

    def get(self,*args, **kwargs):
        version = self.request.GET.get('app_version')
        msg = {'is_success': False, 'message': ['Please send version'], 'response_data': None}
        try:
            app_version = SalesAppVersion.objects.get(app_version=version)
        except ObjectDoesNotExist:
            msg["message"] = ['App version not found']
            return Response(msg, status=status.HTTP_200_OK)

        app_version_serializer = AppVersionSerializer(app_version)
        return Response({"is_success": True, "message": [""], "response_data": app_version_serializer.data})

class StatusChangedAfterAmountCollected(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)


    def post(self, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        cash_collected = self.request.POST.get('cash_collected')
        shipment = OrderedProduct.objects.get(id=shipment_id)
        if float(cash_collected) == float(shipment.cash_to_be_collected()):
            update_order_status(
                close_order_checked=False,
                shipment_id=shipment_id
            )
            msg = {'is_success': True, 'message': ['Status Changed'], 'response_data': None}
        else:
            msg = {'is_success': False, 'message': ['Amount is different'], 'response_data': None}
        return Response(msg, status=status.HTTP_201_CREATED)
