import datetime
import logging
from math import floor

from rest_framework import authentication, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from retailer_backend import messages
from retailer_backend.messages import SUCCESS_MESSAGES, VALIDATION_ERROR_MESSAGES, ERROR_MESSAGES
from retailer_incentive.api.v1.serializers import SchemeShopMappingSerializer, SalesExecutiveListSerializer, \
    SchemeDetailSerializer
from retailer_incentive.models import SchemeSlab
from retailer_incentive.utils import get_shop_scheme_mapping, get_shop_scheme_mapping_based_on_month, get_shop_scheme_mapping_based_on_month_from_db
from shops.models import ShopUserMapping, Shop, ParentRetailerMapping
from retailer_incentive.common_function import get_user_id_from_token, get_total_sales
from accounts.models import User

logger = logging.getLogger('dashboard-api')

today = datetime.date.today()


class ShopSchemeMappingView(APIView):
    """
    This class is used to get Scheme mapped with a shop
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        shop = Shop.objects.filter(id=shop_id).last()
        if shop is None:
            msg = {'is_success': False, 'message': ['No shop found'], 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)
        scheme_shop_mapping = get_shop_scheme_mapping(shop_id)
        if scheme_shop_mapping is None:
            msg = {'is_success': False, 'message': ['No Scheme found for this shop'], 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)
        serializer = SchemeShopMappingSerializer(scheme_shop_mapping)
        msg = {'is_success': True, 'message': ['OK'], 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class ShopPurchaseMatrix(APIView):
    """
    This class is used to get the purchase matrix of a shop under mapped scheme
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        shop = Shop.objects.filter(id=shop_id).last()
        if shop is None:
            msg = {'is_success': False, 'message': ['No shop found'], 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)
        scheme_shop_mapping = get_shop_scheme_mapping(shop_id)
        if scheme_shop_mapping is None:
            msg = {'is_success': False, 'message': ['No Scheme Found for this shop'], 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)
        scheme = scheme_shop_mapping.scheme
        total_sales = get_total_sales(shop_id, scheme.start_date, scheme.end_date)
        scheme_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__lt=total_sales).order_by('min_value').last()

        discount_percentage = 0
        if scheme_slab is not None:
            discount_percentage = scheme_slab.discount_value
        discount_value = floor(discount_percentage * total_sales / 100)
        next_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__gt=total_sales).order_by('min_value').first()
        message = SUCCESS_MESSAGES['SCHEME_SLAB_HIGHEST']
        if next_slab is not None:
            message = SUCCESS_MESSAGES['SCHEME_SLAB_ADD_MORE'].format(floor(next_slab.min_value - total_sales),
                                                                      (
                                                                                  next_slab.min_value * next_slab.discount_value / 100),
                                                                      next_slab.discount_value)
        msg = {'is_success': True, 'message': ['OK'], 'data': {'total_sales': total_sales,
                                                               'discount_percentage': discount_percentage,
                                                               'discount_value': discount_value,
                                                               'message': message}}
        return Response(msg, status=status.HTTP_200_OK)


class ShopUserMappingView(APIView):
    """
    This class is used to get the Shop User Mapping related data
    Returns:
        Sales Executive name and number
        Sales Manager name and number
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        shop_id = request.GET.get('shop_id')
        shop = Shop.objects.filter(id=shop_id).last()
        if shop is None:
            msg = {'is_success': False, 'message': ['No shop found'], 'data': {}}
            return Response(msg, status=status.HTTP_200_OK)

        sales_executive_name = ''
        sales_executive_number = ''
        sales_manager_name = ''
        sales_manager_number = ''

        shop_user_mapping = shop.shop_user.filter(employee_group__name='Sales Executive', status=True).last()

        if shop_user_mapping is not None:
            sales_executive = shop_user_mapping.employee
            sales_executive_name = sales_executive.first_name + ' ' + sales_executive.last_name
            sales_executive_number = sales_executive.phone_number
            parent_shop_id = ParentRetailerMapping.objects.filter(retailer_id=shop_id).last().parent_id
            parent_shop_user_mapping = ShopUserMapping.objects.filter(shop=parent_shop_id,
                                                                      employee=sales_executive, status=True).last()
            if parent_shop_user_mapping and parent_shop_user_mapping.manager is not None:
                sales_manager = parent_shop_user_mapping.manager.employee
                sales_manager_name = sales_manager.first_name + ' ' + sales_manager.last_name
                sales_manager_number = sales_manager.phone_number
        msg = {'is_success': True, 'message': ['OK'], 'data': {'se_name': sales_executive_name,
                                                               'se_no': sales_executive_number,
                                                               'sm_name': sales_manager_name,
                                                               'sm_no': sales_manager_number
                                                               }}
        return Response(msg, status=status.HTTP_200_OK)


class SalesManagerLogin(APIView):
    """
        This class is used to get the mapped 'Sales Executive' for 'Sales Manager'
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SalesExecutiveListSerializer
    queryset = ShopUserMapping.objects.all()

    def get(self, request):
        # get user from token
        user = get_user_id_from_token(request)
        if type(user) == str:
            msg = {'is_success': False,
                   'error_message': user,
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            # check if user_type is Sales Manager
            if user.user_type == 7:  # 'Sales Manager'
                shop_mapping_object = (self.queryset.filter(
                    employee=user.shop_employee.instance, status=True))
                if shop_mapping_object:
                    executive_list = []
                    for shop_mapping in shop_mapping_object:
                        executive = self.queryset.filter(manager=shop_mapping).distinct('employee_id')
                        for sales_executive in executive:
                            if sales_executive.employee.user_type == 6 and \
                                    sales_executive.employee_group.name == 'Sales Executive':
                                executive_list.append(sales_executive)
                    executive_serializer = self.serializer_class(executive_list, many=True)
                    return Response({"detail": messages.SUCCESS_MESSAGES["2001"],
                                     "data": executive_serializer.data,
                                     'is_success': True}, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False,
                       'error_message': "User is not Authorised",
                       'response_data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        except Exception as error:
            logger.exception(error)
            return Response({"detail": "Error while getting mapped Sales Executive for Sales Manager",
                             'is_success': False}, status=status.HTTP_200_OK)


class IncentiveDashBoard(APIView):
    """
        This class is used to get the incentive details of all mapped Shop
        for 'Sales Executive'
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    queryset = ShopUserMapping.objects.all()

    def get_user_id_or_error_message(self, request):
        user = get_user_id_from_token(request)
        if not type(user) == str:
            if user.user_type == 7:
                user_id = request.GET.get('user_id')
                user = User.objects.filter(id=user_id).last()
                if user is None:
                    return "Please Provide a Valid user_id"
        return user

    def get(self, request):
        user = self.get_user_id_or_error_message(request)
        if type(user) == str:
            msg = {'is_success': False,
                   'error_message': user,
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        try:
            # check if user_type is Sales Executive
            if user.user_type == 6:  # 'Sales Executive'
                month = int(request.GET.get('month')) if request.GET.get(
                    'month') else today.month
                if month == today.month:
                    mapped_shop_scheme_details = self.get_sales_executive_shop_scheme_details(user, month)
                else:
                    mapped_shop_scheme_details = self.get_sales_executive_details_from_database(user, month)
                return Response({"detail": messages.SUCCESS_MESSAGES["2001"],
                                 "data": mapped_shop_scheme_details,
                                 'is_success': True}, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False,
                       'error_message': "User is not Authorised",
                       'response_data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        except Exception as error:
            logger.exception(error)
            return Response({"detail": "Error while getting data for Sales Executive",
                             'is_success': False}, status=status.HTTP_200_OK)

    def get_sales_executive_shop_scheme_details(self, user, month):
        shop_mapping_object = (self.queryset.filter(
            employee=user.shop_employee.instance, status=True))
        if shop_mapping_object:
            scheme_shop_mapping_list = []
            for shop_scheme in shop_mapping_object:
                scheme_shop_mapping = get_shop_scheme_mapping_based_on_month(shop_scheme.shop_id, month)
                if scheme_shop_mapping:
                    for scheme_shop_mapping in scheme_shop_mapping:
                        scheme_shop_mapping_list.append(scheme_shop_mapping)
            if scheme_shop_mapping_list:
                scheme_data_list = []
                for scheme_shop_map in scheme_shop_mapping_list:
                    scheme = scheme_shop_map.scheme
                    total_sales = get_total_sales(scheme_shop_map.shop_id, scheme_shop_map.start_date,
                                                  scheme_shop_map.end_date)
                    discount_percentage = 0
                    discount_value = floor(discount_percentage * total_sales / 100)
                    all_scheme_slab =SchemeSlab.objects.filter(scheme=scheme).order_by('min_value')
                    if all_scheme_slab:
                        for scheme_slab_value in all_scheme_slab:
                            scheme_slab = scheme_slab_value.min_value <= total_sales
                            if scheme_slab:
                                discount_percentage = scheme_slab.discount_value
                                discount_value = floor(discount_percentage * total_sales / 100)
                            shop = Shop.objects.filter(id=scheme_shop_map.shop_id).last()
                            scheme_data = {'shop_id': shop.id,
                                           'shop_name': shop.shop_name,
                                           'mapped_scheme_id': scheme.id,
                                           'mapped_scheme': scheme.name,
                                           'total_sales': total_sales,
                                           'discount_percentage': discount_percentage,
                                           'discount_value': discount_value,
                                           'start_date': scheme_shop_map.start_date,
                                           'end_date': scheme_shop_map.end_date
                                           }
                            scheme_data_list.append(scheme_data)
                return scheme_data_list

    def get_sales_executive_details_from_database(self, user, month):
        shop_mapping_object = (self.queryset.filter(
            employee=user.shop_employee.instance, status=True))
        if shop_mapping_object:
            scheme_shop_mapping_list = []
            for shop_scheme in shop_mapping_object:
                shop_scheme_mapped_data = get_shop_scheme_mapping_based_on_month_from_db(shop_scheme.shop_id, month)
                if shop_scheme_mapped_data:
                    for scheme_shop_mapping in shop_scheme_mapped_data:
                        scheme_shop_mapping_list.append(scheme_shop_mapping)
            if scheme_shop_mapping_list:
                scheme_data_list = []
                for shop_map in scheme_shop_mapping_list:
                    shop = Shop.objects.filter(id=shop_map.shop_id).last()
                    scheme_data = [{'shop_id': shop.id,
                                    'shop_name': shop.shop_name,
                                    'mapped_scheme_id': shop_map.mapped_scheme_id,
                                    'mapped_scheme': shop_map.mapped_scheme.name,
                                    'total_sales': shop_map.purchase_value,
                                    'discount_percentage': shop_map.discount_percentage,
                                    'discount_value': shop_map.incentive_earned,
                                    'start_date': shop_map.start_date,
                                    'end_date': shop_map.end_date
                                    }]
                    scheme_data_list.append(scheme_data)
                return scheme_data_list


class ShopSchemeDetails(APIView):
    """
       This class is used to get SchemeSlab detail based on scheme id
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        scheme_id = request.GET.get('scheme_id')
        scheme_slab = SchemeSlab.objects.filter(id=scheme_id).last()

        if scheme_slab:
            serializer = SchemeDetailSerializer(scheme_slab)
        msg = {'is_success': True, 'message': ['OK'], 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)
