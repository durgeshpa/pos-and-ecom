import json
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from django.db.models import Sum, Count, F, FloatField, Avg
from django.core.exceptions import ObjectDoesNotExist
from django_filters import rest_framework as filters
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status, viewsets, permissions, authentication
from rest_framework.parsers import FormParser, MultiPartParser

from accounts.models import USER_DOCUMENTS_TYPE_CHOICES
from addresses.models import Address
from addresses.api.v1.serializers import AddressSerializer
from common.data_wrapper_view import DataWrapperViewSet
from pos.common_functions import check_pos_shop, pos_check_permission, api_response, check_logged_in_user_is_superuser, \
    check_fofo_shop, check_logged_in_user_has_fofo_config_perm
from retailer_backend.utils import SmallOffsetPagination
from retailer_backend import messages
from retailer_backend.messages import SUCCESS_MESSAGES, ERROR_MESSAGES
from retailer_to_sp.models import OrderedProduct, Order
from retailer_to_sp.api.v1.views import update_trip_status
from retailer_to_sp.views import update_shipment_status_after_return
from shops.common_functions import get_response, serializer_error, serializer_error_batch
from shops.services import shop_search, shop_config_search, shop_category_search, shop_sub_category_search
from shops.filters import FavouriteProductFilter
from products.common_validators import validate_id
from shops.models import (PosShopUserMapping, RetailerType, ShopType, Shop, ShopPhoto, ShopDocument, ShopUserMapping,
                          SalesAppVersion, ShopRequestBrand, ShopTiming, FavouriteProduct, BeatPlanning,
                          DayBeatPlanning, ExecutiveFeedback, USER_TYPE_CHOICES, FOFOConfigurations, FOFOConfigCategory,
                          FOFOConfigSubCategory)
from .serializers import (RetailerTypeSerializer, ShopTypeSerializer, ShopSerializer, ShopPhotoSerializer,
                          ShopDocumentSerializer, ShopTimingSerializer, ShopUserMappingSerializer, SellerShopSerializer,
                          AppVersionSerializer, ShopUserMappingUserSerializer, ShopRequestBrandSerializer,
                          FavouriteProductSerializer, AddFavouriteProductSerializer, ListFavouriteProductSerializer,
                          DayBeatPlanSerializer, FeedbackCreateSerializers, ExecutiveReportSerializer,
                          PosShopUserMappingCreateSerializer, PosShopUserMappingUpdateSerializer, ShopBasicSerializer,
                          FOFOConfigurationsCrudSerializer, FOFOCategoryConfigurationsCrudSerializer,
                          FOFOSubCategoryConfigurationsCrudSerializer, FOFOConfigurationsGetSerializer,
                          FOFOListSerializer)
from ...common_validators import validate_id, get_logged_user_wise_query_set_to_filter_warehouse, \
    get_logged_user_wise_query_set_for_seller_shop, validate_fofo_sub_category

User = get_user_model()

logger = logging.getLogger('shop-api')

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ShopRequestBrandViewSet(DataWrapperViewSet):
    '''
    This class handles all operation of ordered product
    '''
    # permission_classes = (AllowAny,)
    model = ShopRequestBrand
    queryset = ShopRequestBrand.objects.all()
    serializer_class = ShopRequestBrandSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = ShopRequestBrandFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': ShopRequestBrandSerializer,
            'list': ShopRequestBrandSerializer,
            'create': ShopRequestBrandSerializer,
            'update': ShopRequestBrandSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class


class FavouriteProductView(DataWrapperViewSet):
    '''
    This class handles all operation of favourite product for a shop
    '''
    # permission_classes = (AllowAny,)
    model = FavouriteProduct
    serializer_class = FavouriteProductSerializer
    queryset = FavouriteProduct.objects.all()
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = FavouriteProductFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': FavouriteProductSerializer,
            'list': FavouriteProductSerializer,
            'create': AddFavouriteProductSerializer,
            'update': FavouriteProductSerializer,
            'delete': FavouriteProductSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def delete(self, request, *args, **kwargs):

        try:
            buyer_shop = request.query_params['buyer_shop']
            product = request.query_params['product']
            favourite = FavouriteProduct.objects.filter(
                buyer_shop=buyer_shop, product=product)
            if favourite.exists():
                favourite.delete()
                return Response(data={'message': "deleted"})
            else:
                return Response(data={'message': "not found"})

        except Exception as e:
            return Response(data={'message': str(e)})


class FavouriteProductListView(generics.ListAPIView):
    queryset = FavouriteProduct.objects.all()
    serializer_class = ListFavouriteProductSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    # permission_classes = (AllowAny,)
    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = FavouriteProductFilter

    def get_queryset(self):
        buyer_shop = self.request.query_params.get('buyer_shop', None)
        buyer_shop_products = FavouriteProduct.objects.all()
        if buyer_shop:
            buyer_shop_products = buyer_shop_products.filter(
                buyer_shop=buyer_shop
            )
        return buyer_shop_products

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
               'message': [""],
               'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)


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
                        result = ''.join('{} : {}'.format(field, error))
                    errors.append(result)
            msg = {'is_success': False,
                   'message': [error for error in errors],
                   'response_data': None}
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
        user_shops = Shop.objects.filter(shop_owner=self.request.user).values_list('id', flat=True)
        queryset = ShopDocument.objects.filter(shop_name__id__in=list(user_shops))
        shop_id = self.request.query_params.get('shop_id', None)
        if shop_id is not None:
            queryset = queryset.filter(shop_name=shop_id)
        return queryset

    def create(self, request, *args, **kwargs):
        validated_data = self.check_validate_data(request.data)
        if validated_data is None:
            msg = {'is_success': True,
                   'message': ["Documents uploaded successfully"],
                   'response_data': None}
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
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
                        result = ''.join('{} : {}'.format(field, error))
                    errors.append(result)
            msg = {'is_success': False,
                   'message': [error for error in errors],
                   'response_data': None}
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

    def check_validate_data(self, data):

        if 'shop_document_type' in data and (data['shop_document_type'] == ShopDocument.UIDAI or \
                data['shop_document_type'] == ShopDocument.PASSPORT or data['shop_document_type'] == ShopDocument.DL \
                or data['shop_document_type'] == ShopDocument.EC):
            if 'shop_document_number' not in data or not data['shop_document_number']:
                data = None
        elif 'shop_document_type' not in data:
            data = None
        return data


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
               'response_data': serializer.data}
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
        shop = serializer.save(shop_owner=self.request.user, created_by=self.request.user)
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
               'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.is_valid():
            self.perform_create(serializer)
            msg = {'is_success': True, 'message': None,
                   'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['shop, open_timing or closing_timing Required'],
                   'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        timing, created = ShopTiming.objects.update_or_create(shop_id=self.request.data['shop'],
                                                              defaults={
                                                                  'open_timing': self.request.data['open_timing'],
                                                                  'closing_timing': self.request.data['closing_timing'],
                                                                  'break_start_time': self.request.data[
                                                                      'break_start_time'],
                                                                  'break_end_time': self.request.data['break_end_time'],
                                                                  'off_day': self.request.data['off_day'],
        })


class TeamListView(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user)

    def get_employee_list(self):
        return ShopUserMapping.objects.filter(manager__in=self.get_manager(), status=True).order_by(
            'employee').distinct('employee')

    def get_shops(self):
        return ShopUserMapping.objects.filter(employee__in=self.get_employee_list().values('employee'),
                                              status=True).values('shop').order_by('shop').distinct('shop')

    def ger_order(self, shops_list, today, last_day):
        return Order.objects.filter(buyer_shop__id__in=shops_list,
                                    created_at__date__lte=today, created_at__date__gte=last_day).values('ordered_by') \
            .annotate(shops_ordered=Count('ordered_by')) \
            .annotate(no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(no_of_ordered_sku_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces')) \
            .annotate(avg_no_of_ordered_sku_pieces=Avg('ordered_cart__rt_cart_list__no_of_pieces')) \
            .annotate(ordered_amount=Sum(F('order_amount'),
                                         output_field=FloatField())) \
            .annotate(avg_ordered_amount=Avg(F('order_amount'),
                                             output_field=FloatField())) \
            .order_by('ordered_by')

    def ger_order_new(self, shops_list, today, last_day):
        return Order.objects.filter(buyer_shop__id__in=shops_list,
                                    created_at__date__lte=today, created_at__date__gte=last_day).values('buyer_shop') \
            .annotate(shops_ordered=Count('buyer_shop')) \
            .annotate(no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(no_of_ordered_sku_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces')) \
            .annotate(avg_no_of_ordered_sku_pieces=Avg('ordered_cart__rt_cart_list__no_of_pieces')) \
            .annotate(ordered_amount=Sum(F('order_amount'),
                                         output_field=FloatField())) \
            .annotate(avg_ordered_amount=Avg(F('order_amount'),
                                             output_field=FloatField())) \
            .order_by('buyer_shop')

    def get_buyer_shop(self, shops_list, today, last_day):
        return Order.objects.filter(buyer_shop__id__in=shops_list, created_at__date__lte=today,
                                    created_at__date__gte=last_day).values('ordered_by').annotate(
            buyer_shop_count=Count('ordered_by')).order_by('ordered_by')

    def list(self, request, *args, **kwargs):
        days_diff = int(self.request.query_params.get('day', 1))
        to_date = datetime.now() + \
            timedelta(days=1) if days_diff == 1 else datetime.now() - \
            timedelta(days=1)
        if days_diff == 1:
            from_date = to_date - timedelta(days=days_diff)
        elif days_diff == 30:
            from_date = datetime.now() - relativedelta(months=+1)
        else:
            from_date = datetime.now() - timedelta(days=days_diff)
        employee_map = ShopUserMapping.objects.filter(
            manager__in=self.get_manager(), status=True)
        if not employee_map.exists():
            msg = {'is_success': False, 'message': [
                "Sorry No matching user found"], 'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)
        employee_map = ShopUserMapping.objects.filter(manager__in=self.get_manager(), status=True,
                                                      shop__shop_type__shop_type__in=['r', 'f'])
        employee_shop_map = {}
        for e in employee_map:
            employee_shop_map[e.employee] = employee_shop_map[e.employee] + [
                e.shop.id] if e.employee in employee_shop_map else [e.shop.id]
        shops_list = self.get_shops()
        data = []
        data_total = []
        order_obj = self.ger_order_new(shops_list, to_date, from_date)
        order_map = {i['buyer_shop']: (i['no_of_ordered_sku'], i['no_of_ordered_sku_pieces'], i['ordered_amount'],
                                       i['shops_ordered']) for i in order_obj}

        ordered_sku_pieces_total, ordered_amount_total, store_added_total, avg_order_total, avg_order_line_items_total, no_of_ordered_sku_total, shops_ordered_total = 0, 0, 0, 0, 0, 0, 0
        shops_considered = []
        for emp in employee_shop_map:
            store_added = emp.shop_created_by.filter(created_at__date__lte=to_date,
                                                     created_at__date__gte=from_date).count()
            ordered_sku_pieces = 0
            ordered_amount = 0
            shops_ordered = 0
            avg_order_val = 0
            avg_order_line_items = 0
            no_of_ordered_sku = 0
            buyer_shops = employee_shop_map[emp]
            for shop in buyer_shops:
                if shop in order_map:
                    ordered_sku_pieces += order_map[shop][1]
                    ordered_amount += order_map[shop][2]
                    shops_ordered += order_map[shop][3]
                    no_of_ordered_sku += order_map[shop][0]
                    if shop not in shops_considered:
                        ordered_sku_pieces_total += ordered_sku_pieces
                        ordered_amount_total += round(ordered_amount, 2)
                        no_of_ordered_sku_total += no_of_ordered_sku
                        shops_ordered_total += shops_ordered

            if shops_ordered > 0:
                avg_order_val = round(ordered_amount / shops_ordered, 2)
                avg_order_line_items = round(
                    no_of_ordered_sku / shops_ordered, 2)
            rt = {
                'ordered_sku_pieces': ordered_sku_pieces,
                'ordered_amount': round(ordered_amount, 2),
                'delivered_amount': 0,
                'store_added': store_added,
                'unique_calls_made': 0,
                'avg_order_val': avg_order_val,
                'avg_order_line_items': avg_order_line_items,
                'sales_person_name': emp.get_full_name(),
                'executive_contact_number': emp.phone_number,
                'no_of_ordered_sku': no_of_ordered_sku,
                'shops_ordered': shops_ordered
            }
            data.append(rt)
            store_added_total += store_added
            shops_considered += buyer_shops
        try:
            avg_order_total = round(
                ordered_amount_total/shops_ordered_total, 2)
        except:
            avg_order_total = 0
        try:
            avg_order_line_items_total = round(
                no_of_ordered_sku_total/shops_ordered_total, 2)
        except:
            avg_order_line_items_total = 0
        dt = {
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
        data = SmallOffsetPagination().paginate_queryset(data, self.request)
        msg = {'is_success': True, 'message': [
            ""], 'response_data': data, 'response_data_total': data_total}
        return Response(msg, status=status.HTTP_200_OK)


class SellerShopView(generics.ListCreateAPIView):
    serializer_class = SellerShopSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Shop.objects.filter(shop_owner=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
               'message': ["%s shops found" % (queryset.count())],
               'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if ShopUserMapping.objects.filter(employee=self.request.user,
                                          employee_group__permissions__codename='can_sales_person_add_shop',
                                          status=True).exists():
            if not get_user_model().objects.filter(phone_number=self.request.data['shop_owner']).exists():
                msg = {'is_success': False,
                       'message': ["No user is registered with this number"],
                       'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            shop = self.perform_create(serializer)
            # self.add_shop_user_mapping(shop)
            msg = {'is_success': True,
                   'message': [SUCCESS_MESSAGES['USER_SHOP_ADDED']],
                   'response_data': [{
                       "id": shop.pk,
                       "shop_id": shop.pk,
                       "shop_name": shop.shop_name,
                   }]}

            return Response(msg, status=status.HTTP_200_OK)
        else:
            msg = {'is_success': False,
                   'message': ["No permission to add shop"],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        shop = serializer.save(created_by=self.request.user,
                               shop_owner=get_user_model().objects.get(phone_number=self.request.data['shop_owner']))
        return shop

    # def add_shop_user_mapping(self,shop):
    #     if not ShopUserMapping.objects.filter(shop=shop,employee=self.request.user).exists():
    #         ShopUserMapping.objects.create(shop=shop, employee=self.request.user, employee_group=Group.objects.get(name='Sales Executive'))


class SellerShopOrder(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True)

    def get_child_employee(self):
        return ShopUserMapping.objects.filter(manager__in=self.get_manager(),
                                              shop__shop_type__shop_type__in=['r', 'f', 'sp'], status=True)

    def get_shops(self):
        return ShopUserMapping.objects.filter(employee__in=self.get_child_employee().values('employee'),
                                              manager__in=self.get_manager(),
                                              shop__shop_type__shop_type__in=['r', 'f', ], status=True)

    def get_order(self, shops_list, today, last_day):
        return Order.objects.filter(buyer_shop__id__in=shops_list, created_at__date__lte=today,
                                    created_at__date__gte=last_day).values('buyer_shop', 'buyer_shop__shop_name'). \
            annotate(buyer_shop_count=Count('buyer_shop')) \
            .annotate(no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(no_of_ordered_sku_pieces=Sum('ordered_cart__rt_cart_list__no_of_pieces')) \
            .order_by('buyer_shop')

    def get_shop_count(self, shops_list, today, last_day):
        return Order.objects.filter(buyer_shop__id__in=shops_list, created_at__date__lte=today,
                                    created_at__date__gte=last_day).values('buyer_shop').annotate(
            buyer_shop_count=Count('buyer_shop')) \
            .annotate(ordered_amount=Sum(F('order_amount'),
                                         output_field=FloatField())
                      ).order_by('buyer_shop')

    def list(self, request, *args, **kwargs):
        data = []
        data_total = []
        shop_user_obj = ShopUserMapping.objects.filter(employee=self.request.user,
                                                       employee_group__permissions__codename='can_sales_person_add_shop',
                                                       shop__shop_type__shop_type__in=['r', 'f'], status=True)
        if not shop_user_obj.exists():
            shop_user_obj = self.get_shops()
            if not shop_user_obj.exists():
                msg = {'is_success': False, 'message': ["Sorry No matching user found"], 'response_data': data,
                       'response_data_total': data_total}
                return Response(msg, status=status.HTTP_200_OK)

        days_diff = int(self.request.query_params.get('day', 1))
        to_date = datetime.now() + \
            timedelta(days=1) if days_diff == 1 else datetime.now() - \
            timedelta(days=1)
        if days_diff == 1:
            from_date = to_date - timedelta(days=days_diff)
        elif days_diff == 30:
            from_date = datetime.now() - relativedelta(months=+1)
        else:
            from_date = datetime.now() - timedelta(days=days_diff)

        shop_list = list(shop_user_obj.values(
            'shop', 'shop__id', 'shop__shop_name', 'shop__shop_owner__phone_number').distinct('shop'))
        shop_list = sorted(shop_list, key=lambda a: a['shop__shop_name'])
        shops_list = shop_user_obj.values('shop').distinct('shop')
        order_obj = self.get_order(shops_list, to_date, from_date)
        buyer_order_obj = self.get_shop_count(shops_list, to_date, from_date)
        # if self.request.user.shop_employee.last().employee_group.name == 'Sales Executive':
        #     order_obj = order_obj.filter(ordered_by = self.request.user)
        #     buyer_order_obj = buyer_order_obj.filter(ordered_by = self.request.user)
        # elif self.request.user.shop_employee.last().employee_group.name == 'Sales Manager':
        #     executives_list = self.get_child_employee().values('employee')
        #     order_obj = order_obj.filter(ordered_by__in = executives_list)
        #     buyer_order_obj = order_obj.filter(ordered_by__in = executives_list)

        buyer_order_map = {i['buyer_shop']: (
            i['buyer_shop_count'], i['ordered_amount']) for i in buyer_order_obj}
        order_map = {i['buyer_shop']: (i['buyer_shop_count'], i['no_of_ordered_sku'], i['no_of_ordered_sku_pieces']) for
                     i in order_obj}
        no_of_order_total, no_of_ordered_sku_total, no_of_ordered_sku_pieces_total, ordered_amount_total = 0, 0, 0, 0
        for shop in shop_list:
            rt = {
                'name': shop['shop__shop_name'],
                'shop_contact_number': shop['shop__shop_owner__phone_number'],
                'no_of_order': buyer_order_map[shop['shop']][0] if shop['shop'] in buyer_order_map else 0,
                'no_of_ordered_sku': order_map[shop['shop']][1] if shop['shop'] in order_map else 0,
                'no_of_ordered_sku_pieces': order_map[shop['shop']][2] if shop['shop'] in order_map else 0,
                'ordered_amount': round(buyer_order_map[shop['shop']][1], 2) if shop['shop'] in buyer_order_map else 0,
                'calls_made': 0,
                'delivered_amount': 0,
            }
            data.append(rt)

            no_of_order_total += buyer_order_map[shop['shop']
                                                 ][0] if shop['shop'] in buyer_order_map else 0
            no_of_ordered_sku_total += order_map[shop['shop']
                                                 ][1] if shop['shop'] in order_map else 0
            no_of_ordered_sku_pieces_total += order_map[shop['shop']
                                                        ][2] if shop['shop'] in order_map else 0
            ordered_amount_total += round(
                buyer_order_map[shop['shop']][1], 2) if shop['shop'] in buyer_order_map else 0

        dt = {
            'no_of_order': no_of_order_total,
            'no_of_ordered_sku': no_of_ordered_sku_total,
            'no_of_ordered_sku_pieces': no_of_ordered_sku_pieces_total,
            'ordered_amount': round(ordered_amount_total, 2),
            'calls_made': 0,
            'delivered_amount': 0,
        }
        data_total.append(dt)
        data = SmallOffsetPagination().paginate_queryset(data, self.request)
        msg = {'is_success': True, 'message': [
            ""], 'response_data': data, 'response_data_total': data_total}
        return Response(msg, status=status.HTTP_200_OK)


class SellerShopProfile(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True)

    def get_child_employee(self):
        return ShopUserMapping.objects.filter(manager__in=self.get_manager(),
                                              shop__shop_type__shop_type__in=['r', 'f', 'sp'], status=True)

    def get_shops(self):
        return ShopUserMapping.objects.filter(employee__in=self.get_child_employee().values('employee'),
                                              manager__in=self.get_manager(),
                                              shop__shop_type__shop_type__in=['r', 'f', 'sp'], status=True)

    def get_order(self, shops_list):
        return Order.objects.filter(buyer_shop__id__in=shops_list).values('buyer_shop', 'created_at'). \
            annotate(buyer_shop_count=Count('buyer_shop')) \
            .annotate(sum_no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(avg_ordered_amount=Avg(F('ordered_cart__rt_cart_list__cart_product_price__selling_price') * F(
                'ordered_cart__rt_cart_list__no_of_pieces'),
                output_field=FloatField())) \
            .annotate(ordered_amount=Sum(F('ordered_cart__rt_cart_list__cart_product_price__selling_price') * F(
                'ordered_cart__rt_cart_list__no_of_pieces'),
                output_field=FloatField())) \
            .order_by('buyer_shop', 'created_at')

    def get_avg_order_count(self, shops_list):
        return Order.objects.filter(buyer_shop__id__in=shops_list).values('buyer_shop') \
            .annotate(buyer_shop_count=Count('buyer_shop')) \
            .annotate(sum_no_of_ordered_sku=Count('ordered_cart__rt_cart_list')) \
            .annotate(ordered_amount=Sum(F('order_amount'),
                                         output_field=FloatField())).order_by('buyer_shop')

    def get_buyer_shop_count(self, shops_list):
        return Order.objects.filter(buyer_shop__id__in=shops_list).values('buyer_shop').annotate(
            buyer_shop_count=Count('buyer_shop')).order_by('buyer_shop')

    def list(self, request, *args, **kwargs):
        data = []
        shop_user_obj = ShopUserMapping.objects.filter(employee=self.request.user,
                                                       employee_group__permissions__codename='can_sales_person_add_shop',
                                                       shop__shop_type__shop_type__in=['r', 'f'], status=True)
        if not shop_user_obj:
            shop_user_obj = self.get_shops()
            if not shop_user_obj.exists():
                msg = {'is_success': False, 'message': [
                    "Sorry No matching user found"], 'response_data': data}
                return Response(msg, status=status.HTTP_200_OK)

        shop_list = shop_user_obj.values(
            'shop', 'shop__id', 'shop__shop_name', 'shop__shop_owner__phone_number').order_by('shop__shop_name')
        shops_list = shop_user_obj.values('shop').distinct('shop')
        order_list = self.get_order(shops_list)
        avg_order_obj = self.get_avg_order_count(shops_list)
        buyer_order_obj = self.get_buyer_shop_count(shops_list)
        # if self.request.user.shop_employee.last().employee_group.name == 'Sales Executive':
        #     order_list = order_list.filter(ordered_by = self.request.user)
        #     avg_order_obj = avg_order_obj.filter(ordered_by = self.request.user)
        #     buyer_order_obj = buyer_order_obj.filter(ordered_by = self.request.user)
        # elif self.request.user.shop_employee.last().employee_group.name == 'Sales Manager':
        #     executives_list = self.get_child_employee().values('employee')
        #     order_list = order_list.filter(ordered_by__in = executives_list)
        #     avg_order_obj = avg_order_obj.filter(ordered_by__in = executives_list)
        #     buyer_order_obj = buyer_order_obj.filter(ordered_by__in = executives_list)
        buyer_order_map = {i['buyer_shop']: (
            i['buyer_shop_count'],) for i in buyer_order_obj}
        avg_order_map = {i['buyer_shop']: (
            i['sum_no_of_ordered_sku'], i['ordered_amount']) for i in avg_order_obj}
        order_map = {i['buyer_shop']: (
            i['buyer_shop_count'], i['sum_no_of_ordered_sku'], i['avg_ordered_amount'], i['created_at'],
            i['ordered_amount']) for i in order_list}

        for shop in shop_list:
            try:
                order_value = round(
                    order_map[shop['shop']][4], 2) if shop['shop'] in order_map else 0
            except:
                order_value = 0
            rt = {
                'name': shop['shop__shop_name'],
                'shop_contact_number': shop['shop__shop_owner__phone_number'],
                'last_order_date': order_map[shop['shop']][3].strftime('%d-%m-%Y %H:%M') if shop['shop'] in order_map else 0,
                'last_order_value': order_value,
                'ordered_amount': avg_order_map[shop['shop']][1] if shop['shop'] in buyer_order_map else 0,
                'avg_order_value': round(avg_order_map[shop['shop']][1] / buyer_order_map[shop['shop']][0], 2) if shop[
                    'shop'] in buyer_order_map else 0,
                'sum_no_of_ordered_sku': avg_order_map[shop['shop']][0] if shop['shop'] in buyer_order_map else 0,
                'avg_ordered_sku': round(avg_order_map[shop['shop']][0] / buyer_order_map[shop['shop']][0], 2) if shop[
                    'shop'] in buyer_order_map else 0,
                'buyer_shop_count': buyer_order_map[shop['shop']][0] if shop['shop'] in buyer_order_map else 0,
                'avg_time_between_order': '',
                'last_calls_made': '',
            }
            data.append(rt)
        data = SmallOffsetPagination().paginate_queryset(data, self.request)
        msg = {'is_success': True, 'message': [""], 'response_data': data}
        return Response(msg, status=status.HTTP_200_OK)


class SalesPerformanceView(generics.ListAPIView):
    serializer_class = ShopUserMappingSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(employee=self.request.user,
                                              employee_group__permissions__codename='can_sales_person_add_shop',
                                              shop__shop_type__shop_type__in=['r', 'f'], status=True).values(
            'shop').order_by('shop').distinct('shop')

    def list(self, request, *args, **kwargs):
        days_diff = 1 if self.request.query_params.get('day', None) is None else int(
            self.request.query_params.get('day'))
        data = []
        next_15_day = 15
        next_30_day = 30
        today = datetime.now()
        last_day = today - timedelta(days=days_diff)
        one_month = today - timedelta(days=days_diff + days_diff)

        last_15_day = today - timedelta(days=days_diff + next_15_day)
        last_30_day = today - timedelta(days=days_diff + next_30_day)

        first_15_day = Order.objects.filter(buyer_shop__id__in=self.get_queryset()).filter(created_at__date__lte=today,
                                                                                           created_at__date__gte=last_15_day).values(
            'buyer_shop').annotate(buyer_shop_count=Count('buyer_shop'))
        next_15_day = Order.objects.filter(buyer_shop__id__in=self.get_queryset()).filter(
            created_at__date__lte=last_15_day, created_at__date__gte=last_30_day).values('buyer_shop').annotate(
            buyer_shop_count=Count('buyer_shop'))

        if self.get_queryset():
            rt = {
                'name': request.user.get_full_name(),
                'shop_inactive': abs(
                    Order.objects.filter(buyer_shop__id__in=self.get_queryset(), created_at__date__lte=today,
                                         created_at__date__gte=last_15_day).values('buyer_shop').annotate(
                        buyer_shop_count=Count('buyer_shop')).count() - self.get_queryset().count()),
                'shop_onboard': Shop.objects.filter(created_by=self.request.user, status=True,
                                                    created_at__date__lte=today,
                                                    created_at__date__gte=last_day).count(),
                'shop_reactivated': first_15_day.difference(next_15_day).count(),
                'current_target_sales_target': '',
                'current_store_count': Shop.objects.filter(created_by=self.request.user, created_at__date__lte=today,
                                                           created_at__date__gte=last_day).count(),
            }
            data.append(rt)
            msg = {'is_success': True, 'message': [""], 'response_data': data}
        else:
            msg = {'is_success': False, 'message': [
                "User not exists"], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)


class SalesPerformanceUserView(generics.ListAPIView):
    serializer_class = ShopUserMappingUserSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ShopUserMapping.objects.filter(manager=self.request.user, shop__shop_type__shop_type__in=['r', 'f'],
                                              status=True).order_by('employee').distinct('employee')

    def list(self, request, *args, **kwargs):
        shop_emp = ShopUserMapping.objects.filter(employee=self.request.user, shop__shop_type__shop_type__in=['r', 'f'],
                                                  employee_group__permissions__codename='can_sales_person_add_shop',
                                                  status=True)
        if not shop_emp:
            shop_mangr = self.get_queryset()
            msg = {'is_success': True, 'message': [""],
                   'response_data': self.get_serializer(shop_mangr, many=True).data,
                   'user_list': shop_mangr.values('employee')}
        elif shop_emp.exists():
            msg = {'is_success': True, 'message': [""], 'response_data': self.get_serializer(shop_emp).data,
                   'user_list': shop_emp.values('employee')}
        else:
            msg = {'is_success': False, 'message': [
                "User not exists"], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)


class SellerShopListView(generics.ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AddressSerializer

    def get_queryset(self):
        shop_mapped = ShopUserMapping.objects.filter(employee=self.request.user,
                                                     shop__shop_type__shop_type__in=['r', 'f'], status=True).values(
            'shop')
        shop_list = Address.objects.filter(shop_name__id__in=shop_mapped, address_type='shipping').order_by(
            'created_at')
        if self.request.query_params.get('mobile_no'):
            shop_list = shop_list.filter(
                shop_name__shop_owner__phone_number__icontains=self.request.query_params.get('mobile_no'))
        if self.request.query_params.get('shop_name'):
            shop_list = shop_list.filter(
                shop_name__shop_name__icontains=self.request.query_params.get('shop_name'))
        if self.request.query_params.get('pin_code'):
            shop_list = shop_list.filter(
                pincode__icontains=self.request.query_params.get('pin_code'))
        if self.request.query_params.get('address'):
            shop_list = shop_list.filter(
                address_line1__icontains=self.request.query_params.get('address'))
        return shop_list.values('shop_name', 'shop_name__shop_name', 'shop_name__shop_owner__phone_number',
                                'address_line1', 'city__city_name', 'state__state_name', 'pincode',
                                'address_contact_name', 'address_contact_number').order_by('shop_name').distinct(
            'shop_name')

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
        is_success = False if not data else True
        msg = {'is_success': is_success,
               'message': [""], 'response_data': data}
        return Response(msg, status=status.HTTP_200_OK)


class CheckUser(generics.ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        all_user = ShopUserMapping.objects.filter(
            employee=self.request.user, status=True)
        if not all_user.exists():
            msg = {'is_success': False, 'message': ["Sorry you are not authorised"], 'response_data': None,
                   'is_sales': False, 'is_sales_manager': False, 'is_delivery_boy': False, 'is_picker': False,
                   'is_putaway': False, 'is_auditor': False}
        else:
            is_sales = True if ShopUserMapping.objects.filter(employee=self.request.user,
                                                              employee_group__permissions__codename='can_sales_person_add_shop',
                                                              shop__shop_type__shop_type__in=[
                                                                  'r', 'f'],
                                                              status=True).exists() else False
            is_sales_manager = True if ShopUserMapping.objects.filter(employee=self.request.user,
                                                                      employee_group__permissions__codename='can_sales_manager_add_shop',
                                                                      shop__shop_type__shop_type='sp',
                                                                      status=True).exists() else False
            is_delivery_boy = True if ShopUserMapping.objects.filter(employee=self.request.user,
                                                                     employee_group__permissions__codename='is_delivery_boy',
                                                                     status=True).exists() else False
            is_picker = True if 'Picker Boy' in self.request.user.groups.values_list(
                'name', flat=True) else False
            is_putaway = True if 'Putaway' in self.request.user.groups.values_list(
                'name', flat=True) else False
            is_auditor = True if self.request.user.groups.filter(
                name='Warehouse-Auditor').exists() else False
            msg = {'is_success': True, 'message': [""], 'response_data': None, 'is_sales': is_sales,
                   'is_sales_manager': is_sales_manager, 'is_delivery_boy': is_delivery_boy,
                   'is_picker': is_picker, 'is_putaway': is_putaway, 'is_auditor': is_auditor}
        return Response(msg, status=status.HTTP_200_OK)


class CheckAppVersion(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, *args, **kwargs):
        version = self.request.GET.get('app_version')
        msg = {'is_success': False, 'message': [
            'Please send version'], 'response_data': None}
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
        trip = self.request.POST.get('trip')
        shipment = OrderedProduct.objects.get(id=shipment_id)
        if float(cash_collected) == float(shipment.cash_to_be_collected()):
            shipment_status = update_shipment_status_after_return(shipment)
            # shipment_status = update_shipment_status_with_id(shipment)
            if shipment_status == "FULLY_RETURNED_AND_COMPLETED":
                update_trip_status(trip)
            msg = {'is_success': True, 'message': [
                'Status Changed'], 'response_data': None}
        else:
            msg = {'is_success': False, 'message': [
                'Amount is different'], 'response_data': None}
        return Response(msg, status=status.HTTP_201_CREATED)


class DayBeatPlan(viewsets.ModelViewSet):
    """
    This class is used to get the beat plan for sales executive
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DayBeatPlanSerializer
    queryset = BeatPlanning.objects.all()
    http_method_names = ['get', 'post']

    def list(self, *args, **kwargs):
        """

        :param args: non-keyword argument
        :param kwargs: keyword argument
        :return: Beat Plan for Sales executive otherwise error message
        """
        if self.request.user.user_type == 7:
            try:
                if self.request.GET['executive_id']:
                    executive = User.objects.filter(id = int(self.request.GET['executive_id'])).last()
            except Exception as e:
                return Response({"detail": messages.ERROR_MESSAGES["4020"],
                                 'is_success': False}, status=status.HTTP_200_OK)
        else:
            executive = self.request.user
        try:
            if self.request.GET['next_plan_date'] == datetime.today().strftime("%Y-%m-%d"):
                beat_user = self.queryset.filter(executive=executive,
                                                 executive__user_type=executive.user_type,
                                                 executive__is_active=True)
                if beat_user.exists():
                    try:
                        for beat in beat_user:
                            day_beat_plan = DayBeatPlanning.objects.filter(beat_plan=beat,
                                                                           next_plan_date=self.request.GET[
                                                                               'next_plan_date'])
                            if day_beat_plan.exists():
                                for day_beat in day_beat_plan:
                                    executive_obj = ExecutiveFeedback.objects.filter(
                                        day_beat_plan=day_beat)
                                    if executive_obj.exists():
                                        beat_plan_serializer = self.serializer_class(
                                            day_beat_plan, many=True)
                                        return Response({"detail": SUCCESS_MESSAGES["2001"],
                                                         "data": beat_plan_serializer.data,
                                                         'is_success': True},
                                                        status=status.HTTP_200_OK)
                    except Exception as error:
                        logger.exception(error)
                        return Response({"detail": messages.ERROR_MESSAGES["4006"] % self.request.GET['next_plan_date'],
                                         'is_success': False},
                                        status=status.HTTP_200_OK)
                    return Response({"detail": messages.ERROR_MESSAGES["4014"], "data": [],
                                     'is_success': True},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"detail": messages.ERROR_MESSAGES["4014"],
                                     'is_success': True, "data": []},
                                    status=status.HTTP_200_OK)
            else:
                try:
                    queryset = self.queryset
                    if self.request.user.user_type == 6:
                        queryset = BeatPlanning.objects.filter(status=True)
                    beat_user = queryset.filter(executive=executive,
                                                executive__user_type=executive.user_type,
                                                executive__is_active=True)
                    beat_user_obj = DayBeatPlanning.objects.filter(beat_plan__in=beat_user,
                                                                   next_plan_date=self.request.GET[
                                                                       'next_plan_date'])
                except Exception as error:
                    logger.exception(error)
                    return Response({"detail": messages.ERROR_MESSAGES["4014"],
                                     'is_success': True, "data": []},
                                    status=status.HTTP_200_OK)
                beat_plan_serializer = self.serializer_class(
                    beat_user_obj, many=True)
                if beat_plan_serializer.data.__len__() <= 0:
                    return Response({"detail": messages.ERROR_MESSAGES["4014"], "data": beat_plan_serializer.data,
                                     'is_success': True},
                                    status=status.HTTP_200_OK)
                return Response({"detail": SUCCESS_MESSAGES["2001"], "data": beat_plan_serializer.data,
                                 'is_success': True},
                                status=status.HTTP_200_OK)
        except Exception as error:
            logger.exception(error)
            return Response({"detail": messages.ERROR_MESSAGES["4008"],
                             'is_success': False}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """

        :param request: request params
        :param args: non-keyword argument
        :param kwargs: keyword argument
        :return: serialized data of executive feedback
        """
        if request.POST['feedback_date'] == datetime.today().strftime("%Y-%m-%d"):
            day_beat_plan = DayBeatPlanning.objects.filter(id=request.POST['day_beat_plan'],
                                                           next_plan_date=request.POST['feedback_date'])
            if day_beat_plan:
                serializer = FeedbackCreateSerializers(
                    data=request.data, context={'request': request})
                if serializer.is_valid():
                    result = serializer.save()
                    if result:
                        return Response({"detail": SUCCESS_MESSAGES["2002"], 'is_success': True,
                                         "data": serializer.data}, status=status.HTTP_201_CREATED)
                    return Response({"detail": ERROR_MESSAGES['4011'], 'is_success': False}, status=status.HTTP_200_OK)
                else:
                    return Response({"detail": ERROR_MESSAGES['4018'], 'is_success': False}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": ERROR_MESSAGES['4018'], 'is_success': False}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": ERROR_MESSAGES['4017'], 'is_success': True}, status=status.HTTP_200_OK)


class ExecutiveReport(viewsets.ModelViewSet):
    """
    This class is used to get the report for sales executive
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ExecutiveReportSerializer
    queryset = ShopUserMapping.objects.all()
    http_method_names = ['get']

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True)

    def list(self, *args, **kwargs):
        """

        :param args: non-keyword argument
        :param kwargs: keyword argument
        :return: Report for Sales executive otherwise error message
        """
        try:
            feedback_executive = ShopUserMapping.objects.filter(manager__in=self.get_manager(), status=True).order_by(
                'employee').distinct('employee')
            executive_report_serializer = self.serializer_class(feedback_executive, many=True,
                                                                context={'report': self.request.GET['report']})
            data = SmallOffsetPagination().paginate_queryset(
                executive_report_serializer.data, self.request)
            return Response({"detail": messages.SUCCESS_MESSAGES["2001"],
                             "data": data,
                             'is_success': True}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.exception(error)


def set_shop_map_cron():
    """
    Cron job for create data in Executive Feedback Model
    :return:
    """
    try:
        beat_plan = BeatPlanning.objects.filter(status=True)
        for beat in beat_plan:
            next_plan_date = datetime.today()
            day_beat_plan = DayBeatPlanning.objects.filter(
                beat_plan=beat, next_plan_date=next_plan_date,status=True)
            for day_beat in day_beat_plan:
                ExecutiveFeedback.objects.get_or_create(day_beat_plan=day_beat)
    except Exception as error:
        logger.exception(error)


class ShopListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    queryset = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2,
                                   pos_enabled=1).only('id', 'shop_name', 'shop_owner', 'shop_type').\
        order_by('-id')
    serializer_class = ShopBasicSerializer

    def get(self, request):
        """ GET Shop List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no shop found"
        return get_response(msg, serializer.data, True)


class UserTypeListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        """ GET API for UserTypeList """
        fields = ['id', 'type']
        data = [dict(zip(fields, d)) for d in USER_TYPE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class PosShopUserMappingView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    queryset = PosShopUserMapping.objects.order_by('-id')
    serializer_class = PosShopUserMappingCreateSerializer

    @check_pos_shop
    @pos_check_permission
    def post(self, request, *args, **kwargs):
        serializer = PosShopUserMappingCreateSerializer(data=request.data, context={'shop': kwargs['shop'],
                                                                                    'created_by': request.user})
        if serializer.is_valid():
            serializer.save()
            return get_response('User Mapped Successfully!', None, True, status.HTTP_200_OK)
        return get_response(serializer_error(serializer), False)

    @check_pos_shop
    @pos_check_permission
    def put(self, request, *args, **kwargs):
        data = request.data
        data['id'] = kwargs['pk']
        serializer = PosShopUserMappingUpdateSerializer(data=data, context={'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.update(kwargs['pk'], serializer.data)
            return get_response('User Mapping Updated Successfully!', None, True, status.HTTP_200_OK)
        return get_response(serializer_error(serializer), False)


class UserDocumentChoices(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        '''
        API to get list of Shop User Document list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in USER_DOCUMENTS_TYPE_CHOICES]
        msg = [""]
        return get_response(msg, data, True)


class ShopDocumentChoices(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        '''
        API to get list of Shop Document list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in [(ShopDocument.FSSAI, "Fssai License No"),
                                               (ShopDocument.DRUG_L, 'Drug License'),
                                               (ShopDocument.ELE_BILL, "Shop Electricity Bill"),
                                               (ShopDocument.UDYOG_AADHAR, 'Udyog Aadhar'),
                                               # (ShopDocument.SLN, "Shop License No"),
                                               (ShopDocument.WSVD, "Weighing Scale Verification Document")]]
        msg = [""]
        return get_response(msg, data, True)


class FOFOConfigCategoryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    queryset = FOFOConfigCategory.objects.order_by('-id')
    serializer_class = FOFOCategoryConfigurationsCrudSerializer

    @check_logged_in_user_has_fofo_config_perm
    def get(self, request):
        """ GET Category List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_category_search(self.queryset, search_text)
        category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        msg = "" if category else "no category found"
        return get_response(msg, serializer.data, True)

    @check_logged_in_user_has_fofo_config_perm
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('category created Successfully!', None, True, status.HTTP_200_OK)
        return get_response(serializer_error(serializer), False)

    @check_logged_in_user_has_fofo_config_perm
    def put(self, request):
        """ PUT API for Category Updation """

        if 'id' not in request.data:
            return get_response('please provide id to update category', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        cat_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=cat_instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('category updated Successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class FOFOConfigSubCategoryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    queryset = FOFOConfigSubCategory.objects.order_by('-id')
    serializer_class = FOFOSubCategoryConfigurationsCrudSerializer

    @check_logged_in_user_has_fofo_config_perm
    def get(self, request):
        """ GET Sub-Category List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_sub_category_search(self.queryset, search_text)
        sub_category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(sub_category, many=True)
        msg = "" if sub_category else "no sub category found"
        return get_response(msg, serializer.data, True)

    @check_logged_in_user_has_fofo_config_perm
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('sub category created Successfully!', None, True, status.HTTP_200_OK)
        return get_response(serializer_error(serializer), False)

    @check_logged_in_user_has_fofo_config_perm
    def put(self, request):
        """ PUT API for Sub Category Updation """

        if 'id' not in request.data:
            return get_response('please provide id to update sub category', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        cat_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=cat_instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('sub category updated Successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class FOFOListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    queryset = FOFOConfigCategory.objects.order_by('-id')
    serializer_class = FOFOListSerializer

    @check_logged_in_user_has_fofo_config_perm
    def get(self, request, *args, **kwargs):
        """ GET Cat Sub-Cat Configurations List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_category_search(self.queryset, search_text)
        category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = FOFOListSerializer(category, many=True)
        msg = "" if category else "no data found"
        return get_response(msg, serializer.data, True)


class FOFOConfigurationsView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    queryset = FOFOConfigurations.objects.order_by('-id')
    serializer_class = FOFOConfigurationsCrudSerializer

    @check_logged_in_user_has_fofo_config_perm
    @check_fofo_shop
    def get(self, request, *args, **kwargs):
        """ GET FOFO  List """
        shop = kwargs['shop']
        search_text = self.request.GET.get('search_text')
        queryset = self.queryset.filter(shop=shop)
        if request.GET.get('id'):
            """ Get FOFO Configurations for specific ID """
            id_validation = validate_id(queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            queryset = id_validation['data']
        serializer = FOFOConfigurationsGetSerializer(queryset, context={'shop': shop,
                                                                        'search_text': search_text,
                                                                        'id': request.GET.get('id')})
        msg = "" if queryset else "no configurations found"
        return get_response(msg, serializer.data, True)

    @check_logged_in_user_has_fofo_config_perm
    @check_fofo_shop
    def post(self, request, *args, **kwargs):
        shop = kwargs['shop']
        modified_data = self.validate_request_data()
        if 'error' in modified_data:
            return api_response(modified_data['error'])
        validated_data = validate_fofo_sub_category(modified_data['data'], shop)
        if 'error' in validated_data:
            return api_response(validated_data['error'])
        serializer = self.serializer_class(data=validated_data['data'], many=True)
        if serializer.is_valid():
            serializer.save()
            return get_response('Configurations has been done Successfully!', None, True, status.HTTP_200_OK)
        return get_response(serializer_error_batch(serializer), False)

    @check_logged_in_user_has_fofo_config_perm
    @check_fofo_shop
    def put(self, request, *args, **kwargs):
        shop = kwargs['shop']
        modified_data = self.validate_request_data()
        if 'error' in modified_data:
            return api_response(modified_data['error'])
        validated_data = validate_fofo_sub_category(modified_data['data'], shop)
        if 'error' in validated_data:
            return api_response(validated_data['error'])

        resp_data = self.create_or_update_configurations(validated_data['data'])
        if 'error' in resp_data:
            return api_response(validated_data['error'])
        return get_response('Configurations has been done Successfully!', None, True, status.HTTP_200_OK)

    def create_or_update_configurations(self, data_list):
        for data in data_list:
            instance, created = FOFOConfigurations.objects.update_or_create(
                shop_id=data['shop'], key_id=data['key'], defaults={'value': data['value']})
        return {'data': 'Configurations has been done Successfully!'}

    def validate_request_data(self):
        # Validate product data
        try:
            data = self.request.data["data"]
            if not isinstance(data, list):
                return {'error': 'Format of data is expected to be a list.'}
        except:
            return {'error': "Invalid Data Format"}
        return {'data': data}





class SellerShopFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.all()
    serializer_class = ShopBasicSerializer

    def get(self, request):
        """ GET API for Shop """
        info_logger.info("Shop GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop List """
            self.queryset = get_logged_user_wise_query_set_for_seller_shop(request.user, self.queryset)
            self.queryset = self.search_filter_shops_data()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_data, many=True)
        msg = "" if shops_data else "no shop found"
        return get_response(msg, serializer.data, True)

    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        shop_type = self.request.GET.get('shop_type')
        shop_owner = self.request.GET.get('shop_owner')
        pin_code = self.request.GET.get('pin_code')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')
        approval_status = self.request.GET.get('approval_status')

        '''search using shop_name and parent_shop based on criteria that matches'''
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)

        '''Filters using shop_type, shop_owner, pin_code, city, status, approval_status'''
        if shop_type:
            self.queryset = self.queryset.filter(shop_type__id=shop_type)

        if shop_owner:
            self.queryset = self.queryset.filter(shop_owner=shop_owner)

        if pin_code:
            self.queryset = self.queryset.filter(shop_name_address_mapping__pincode_link__id=pin_code)

        if city:
            self.queryset = self.queryset.filter(shop_name_address_mapping__city__id=city)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if approval_status:
            self.queryset = self.queryset.filter(approval_status=approval_status)

        return self.queryset.distinct('id')


class DispatchCenterFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.filter(shop_type__shop_type='dc').order_by('-id')
    serializer_class = ShopBasicSerializer

    def get(self, request):
        """ GET API for Shop """
        info_logger.info("Shop GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop List """
            self.queryset = get_logged_user_wise_query_set_to_filter_warehouse(request.user, self.queryset)
            self.queryset = self.search_filter_shops_data()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_data, many=True)
        msg = "" if shops_data else "no shop found"
        return get_response(msg, serializer.data, True)

    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        parent_shop = self.request.GET.get('parent_shop')
        shop_type = self.request.GET.get('shop_type')
        shop_owner = self.request.GET.get('shop_owner')
        pin_code = self.request.GET.get('pin_code')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')
        approval_status = self.request.GET.get('approval_status')

        '''search using shop_name and parent_shop based on criteria that matches'''
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)

        '''Filters using parent_shop, shop_type, shop_owner, pin_code, city, status, approval_status'''
        if shop_type:
            self.queryset = self.queryset.filter(shop_type__id=shop_type)

        if parent_shop:
            self.queryset = self.queryset.filter(retiler_mapping__parent_id=parent_shop)

        if shop_owner:
            self.queryset = self.queryset.filter(shop_owner=shop_owner)

        if pin_code:
            self.queryset = self.queryset.filter(shop_name_address_mapping__pincode_link__id=pin_code)

        if city:
            self.queryset = self.queryset.filter(shop_name_address_mapping__city__id=city)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if approval_status:
            self.queryset = self.queryset.filter(approval_status=approval_status)

        return self.queryset.distinct('id')


class RetailerShopFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.filter(shop_type__shop_type='r').order_by('-id')
    serializer_class = ShopBasicSerializer

    def get(self, request):
        """ GET API for Shop """
        info_logger.info("Shop GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop List """
            self.queryset = self.search_filter_shops_data()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_data, many=True)
        msg = "" if shops_data else "no shop found"
        return get_response(msg, serializer.data, True)

    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        parent_shop = self.request.GET.get('parent_shop')
        shop_type = self.request.GET.get('shop_type')
        shop_owner = self.request.GET.get('shop_owner')
        pin_code = self.request.GET.get('pin_code')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')
        approval_status = self.request.GET.get('approval_status')

        '''search using shop_name and parent_shop based on criteria that matches'''
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)

        '''Filters using parent_shop, shop_type, shop_owner, pin_code, city, status, approval_status'''
        if shop_type:
            self.queryset = self.queryset.filter(shop_type__id=shop_type)

        if parent_shop:
            self.queryset = self.queryset.filter(retiler_mapping__parent_id=parent_shop)

        if shop_owner:
            self.queryset = self.queryset.filter(shop_owner=shop_owner)

        if pin_code:
            self.queryset = self.queryset.filter(shop_name_address_mapping__pincode_link__id=pin_code)

        if city:
            self.queryset = self.queryset.filter(shop_name_address_mapping__city__id=city)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if approval_status:
            self.queryset = self.queryset.filter(approval_status=approval_status)

        return self.queryset.distinct('id')

