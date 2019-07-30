from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from rest_framework.response import Response
from .serializers import (RetailerTypeSerializer, ShopTypeSerializer,
        ShopSerializer, ShopPhotoSerializer, ShopDocumentSerializer, ShopUserMappingSerializer, SellerShopSerializer, AppVersionSerializer)
from shops.models import (RetailerType, ShopType, Shop, ShopPhoto, ShopDocument, ShopUserMapping, SalesAppVersion)
from rest_framework import generics
from addresses.models import City, Area, Address
from rest_framework import status
from django.contrib.auth import get_user_model
from retailer_backend.messages import SUCCESS_MESSAGES, VALIDATION_ERROR_MESSAGES
from rest_framework.parsers import FormParser, MultiPartParser

from datetime import datetime,timedelta
from django.db.models import Q,Sum,Count,F, FloatField, Avg
from retailer_to_sp.models import Order
from django.contrib.auth.models import Group
User =  get_user_model()
from addresses.api.v1.serializers import AddressSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist


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
        return ShopUserMapping.objects.filter(manager=self.request.user,status=True)

    def list(self, request, *args, **kwargs):
        days_diff = 1 if self.request.query_params.get('day', None) is None else int(self.request.query_params.get('day'))
        today = datetime.now()
        last_day = today - timedelta(days=days_diff)
        employee_list = self.get_queryset()
        data = []
        data_total = []
        order_obj = Order.objects.filter(buyer_shop__created_by__id__in=employee_list,
                                         created_at__range=[today, last_day]).values('ordered_by',
                                                                                     'ordered_by__first_name')\
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
        order_map = {i['ordered_by']: (i['no_of_ordered_sku'], i['no_of_ordered_sku_pieces'], i['avg_no_of_ordered_sku_pieces'],
        i['ordered_amount'], i['avg_ordered_amount']) for i in order_obj}

        ordered_sku_pieces_total, ordered_amount_total, store_added_total, avg_order_total, avg_order_line_items_total, no_of_ordered_sku_total = 0,0,0,0,0,0

        for emp in employee_list:
            store_added = emp.employee.shop_created_by.filter(created_at__range=[last_day, today]).count()
            rt = {
                'ordered_sku_pieces': order_map[emp.id][1] if order_map else 0,
                'ordered_amount': round(order_map[emp.id][3], 2) if order_map else 0,
                'delivered_amount': 0,
                'store_added': store_added,
                'avg_order_val': round(order_map[emp.id][4], 2) if order_map else 0,
                'avg_order_line_items': round(order_map[emp.id][2], 2) if order_map else 0,
                'unique_calls_made': 0,
                'sales_person_name': emp.employee.get_full_name(),
                'no_of_ordered_sku': order_map[emp.id][0] if order_map else 0,
            }
            data.append(rt)
            ordered_sku_pieces_total += order_map[emp.id][1] if order_map else 0
            ordered_amount_total += round(order_map[emp.id][3], 2) if order_map else 0
            store_added_total += store_added
            avg_order_total += round(order_map[emp.id][4], 2) if order_map else 0
            avg_order_line_items_total += round(order_map[emp.id][2], 2) if order_map else 0
            no_of_ordered_sku_total += order_map[emp.id][1] if order_map else 0

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
            self.add_shop_user_mapping(shop)
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

    def add_shop_user_mapping(self,shop):
        if not ShopUserMapping.objects.filter(shop=shop,employee=self.request.user).exists():
            ShopUserMapping.objects.create(shop=shop, employee=self.request.user, employee_group=Group.objects.get(name='Sales Executive'))

class SellerShopOrder(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user)

    def list(self, request, *args, **kwargs):
        days_diff = 1 if self.request.query_params.get('day', None) is None else int(self.request.query_params.get('day'))
        data = []
        data_total = []
        today = datetime.now()
        last_day = today - timedelta(days=days_diff)
        employee_list = ShopUserMapping.objects.filter(manager=self.request.user).values('employee')
        shop_list = Shop.objects.filter(created_by__id__in=employee_list).values('shop_name','id').order_by('shop_name')
        order_obj = Order.objects.filter(buyer_shop__created_by__id__in=employee_list,created_at__range=[today, last_day]).values('buyer_shop','buyer_shop__shop_name').\
            annotate(buyer_shop_count=Count('buyer_shop'))\
            .annotate(no_of_ordered_sku=Count('ordered_cart__rt_cart_list'))\
            .annotate(no_of_ordered_sku_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces'))\
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer')* F('ordered_cart__rt_cart_list__no_of_pieces'),
                                     output_field=FloatField()))\
            .order_by('buyer_shop')
        order_map = {i['buyer_shop']: (i['buyer_shop_count'], i['no_of_ordered_sku'], i['no_of_ordered_sku_pieces'],i['ordered_amount']) for i in order_obj}
        no_of_order_total, no_of_ordered_sku_total, no_of_ordered_sku_pieces_total, ordered_amount_total = 0, 0, 0, 0
        for shop in shop_list:
            rt = {
                'name': shop['shop_name'],
                'no_of_order': order_map[shop['id']][0] if order_map else 0,
                'no_of_ordered_sku': order_map[shop['id']][1] if order_map else 0,
                'no_of_ordered_sku_pieces': order_map[shop['id']][2] if order_map else 0,
                'ordered_amount': round(order_map[shop['id']][3],2) if order_map else 0,
                'calls_made': 0,
                'delivered_amount': 0,
            }
            data.append(rt)

            no_of_order_total += order_map[shop['id']][0] if order_map else 0
            no_of_ordered_sku_total += order_map[shop['id']][1] if order_map else 0
            no_of_ordered_sku_pieces_total += order_map[shop['id']][2] if order_map else 0
            ordered_amount_total += round(order_map[shop['id']][3], 2) if order_map else 0

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
        return ShopUserMapping.objects.filter(manager=self.request.user)

    def list(self, request, *args, **kwargs):
        data = []
        shop_user_obj = ShopUserMapping.objects.filter(manager=self.request.user,status=True)
        employee_list = shop_user_obj.values('employee')
        shop_list = shop_user_obj.values('shop','shop__id','shop__shop_name').distinct('shop')
        #shop_list = Shop.objects.filter(created_by__id__in=employee_list).values('shop_name','id').order_by('shop_name')
        order_obj = Order.objects.filter(buyer_shop__created_by__id__in=employee_list).order_by('buyer_shop').last()

        order_list = Order.objects.filter(buyer_shop__created_by__id__in=employee_list).values('buyer_shop','buyer_shop__shop_name').\
            annotate(buyer_shop_count=Count('buyer_shop'))\
            .annotate(no_of_ordered_sku=Avg('ordered_cart__rt_cart_list'))\
            .annotate(ordered_amount=Avg(F('ordered_cart__rt_cart_list__cart_product_price__price_to_retailer')* F('ordered_cart__rt_cart_list__no_of_pieces'),
                                     output_field=FloatField()))\
            .order_by('buyer_shop')
        order_map = {i['buyer_shop']: (i['buyer_shop_count'], i['no_of_ordered_sku'], i['ordered_amount']) for i in order_list}

        for shop in shop_list:
            rt = {
                'name': shop['shop__shop_name'],
                'last_order_date': order_obj.created_at.strftime('%d-%m-%Y %H:%M') if order_obj else 0,
                'last_order_value': order_obj.ordered_cart.subtotal if order_obj else 0,
                'avg_order_value': round(order_map[shop['shop']][2], 2) if order_map else 0,
                'avg_ordered_sku': round(order_map[shop['shop']][1], 0) if order_map else 0,
                'avg_time_between_order': '',
                'last_calls_made': '',
            }
            data.append(rt)

        msg = {'is_success': True, 'message': [""],'response_data': data}
        return Response(msg,status=status.HTTP_200_OK)

class SalesPerformanceView(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user,status=True)

    def list(self, request, *args, **kwargs):
        days_diff = 1 if self.request.query_params.get('day', None) is None else int(self.request.query_params.get('day'))
        data = []
        shop_emp = ShopUserMapping.objects.filter(employee=self.request.user, status=True)
        shop_mangr = ShopUserMapping.objects.filter(manager=self.request.user, status=True)
        if shop_emp.exists() and shop_emp.last().employee_group.permissions.filter(codename='can_sales_person_add_shop').exists():
            today = datetime.now()
            last_day = today - timedelta(days=days_diff)
            one_month = today - timedelta(days=days_diff + days_diff)
            shop_obj = Shop.objects.filter(created_by=request.user)
            rt = {
                'name': request.user.first_name,
                'shop_inactive': shop_obj.filter(status=True).exclude(
                    shop_obj.rt_buyer_shop_order.filter(created_at__gte=last_day)).count() if hasattr(Order,'rt_buyer_shop_order') else 0,
                'shop_onboard': shop_obj.filter(status=True, created_at__gte=last_day).count() if shop_obj.filter(
                    status=True, created_at__gte=last_day) and shop_obj.retiler_mapping.exists() else 0,
                'shop_reactivated': shop_obj.filter(status=True).rt_buyer_shop_order.filter(
                    ~Q(created_at__range=[one_month, last_day]), Q(created_at__gte=last_day)) if hasattr(Order,'rt_buyer_shop_order') else 0,
                'current_target_sales_target': '',
                'current_store_count': shop_obj.filter(created_at__gte=last_day).count(),
            }
            data.append(rt)
            msg = {'is_success': True, 'message': [""], 'response_data': data}

        elif shop_mangr.exists():
            for employee in shop_mangr:
                today = datetime.now()
                last_day = today - timedelta(days=days_diff)
                one_month = today - timedelta(days=days_diff+days_diff)
                shop_obj = Shop.objects.filter(created_by=employee.employee)
                rt = {
                    'name': employee.employee.first_name,
                    'shop_inactive': shop_obj.filter(status=True).exclude(shop_obj.rt_buyer_shop_order.filter(created_at__gte=last_day)).count() if hasattr(Order, 'rt_buyer_shop_order') else 0,
                    'shop_onboard':  shop_obj.filter(status=True, created_at__gte=last_day).count() if shop_obj.filter(status=True,created_at__gte=last_day) and shop_obj.retiler_mapping.exists() else 0,
                    'shop_reactivated': shop_obj.filter(status=True).rt_buyer_shop_order.filter(~Q(created_at__range=[one_month,last_day]),Q(created_at__gte=last_day)) if hasattr(Order, 'rt_buyer_shop_order') else 0,
                    'current_target_sales_target': '',
                    'current_store_count': shop_obj.filter(created_at__gte=last_day).count(),
                }
                data.append(rt)
            msg = {'is_success': True, 'message': [""], 'response_data': data}
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
        shop_user = ShopUserMapping.objects.filter(employee=self.request.user)
        is_sales = True if shop_user.exists() and shop_user.last().employee.has_perm('shops.can_sales_person_add_shop') else False
        msg = {'is_success': True, 'message': [""], 'response_data': None,'is_sales':is_sales}
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

