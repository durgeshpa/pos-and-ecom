import datetime
import logging
from math import floor
import io
import xlsxwriter

from django.http import HttpResponse
from rest_framework import authentication, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from retailer_backend.messages import SUCCESS_MESSAGES, VALIDATION_ERROR_MESSAGES, ERROR_MESSAGES
from retailer_incentive.api.v1.serializers import SchemeShopMappingSerializer, SalesExecutiveListSerializer, \
    SchemeDetailSerializer, SchemeSlabSerializer, IncentiveSerializer, GetIncentiveSerializer, \
    GetListIncentiveSerializer
from retailer_incentive.models import SchemeSlab, IncentiveDashboardDetails, Incentive, BulkIncentive
from retailer_incentive.utils import get_shop_scheme_mapping, get_shop_scheme_mapping_based
from shops.models import ShopUserMapping, Shop, ParentRetailerMapping
from retailer_incentive.common_function import get_user_id_from_token, get_total_sales, shop_scheme_not_mapped
from accounts.models import User

from retailer_backend.utils import SmallOffsetPagination

# Get an instance of a logger
logger = logging.getLogger('dashboard-api')
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

today = datetime.date.today()


# retailer - app
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
            msg = {'is_success': False, 'message': ['No shop found'], 'data': None}
            return Response(msg, status=status.HTTP_200_OK)
        today_date = datetime.date.today()
        current_year = today_date.year
        current_month = today_date.month
        input_month = int(request.GET.get('month', current_month))
        response_data = list()
        # Incentive
        incentive = Incentive.objects.filter(
            shop_id=shop_id, created_at__date__year=current_year, created_at__date__month=input_month).last()
        incentive_data = GetListIncentiveSerializer(incentive, read_only=True).data
        # Active Scheme
        if input_month == current_month:
            scheme_shop_mapping = get_shop_scheme_mapping(shop_id)
            if scheme_shop_mapping:
                scheme = scheme_shop_mapping.scheme
                total_sales = get_total_sales(shop_id, scheme_shop_mapping.start_date, scheme_shop_mapping.end_date)
                scheme_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__lt=total_sales).order_by(
                    'min_value').last()
                discount_percentage = scheme_slab.discount_value if scheme_slab else 0
                discount_value = floor(discount_percentage * total_sales / 100)
                next_slab = SchemeSlab.objects.filter(scheme=scheme, min_value__gt=total_sales).order_by(
                    'min_value').first()
                message = SUCCESS_MESSAGES['SCHEME_SLAB_HIGHEST']
                if next_slab is not None:
                    message = SUCCESS_MESSAGES['SCHEME_SLAB_ADD_MORE'].format(floor(next_slab.min_value - total_sales),
                                                                              (
                                                                                      next_slab.min_value *
                                                                                      next_slab.discount_value / 100),
                                                                              next_slab.discount_value)
                se, sm = self.current_contact(shop)
                scheme_data = self.per_scheme_data(scheme, total_sales, discount_percentage, discount_value,
                                                   scheme.start_date, scheme.end_date, sm, se)
                # message = SUCCESS_MESSAGES['SCHEME_BUY_MORE']
                # scheme_data['message'] = message
                response_data.append(scheme_data)

        # Inactive schemes
        previous_schemes = IncentiveDashboardDetails.objects.select_related('mapped_scheme'). \
            filter(shop_id=shop_id, start_date__year=current_year, start_date__month=input_month,
                   end_date__year=current_year, end_date__month=input_month).order_by('-start_date', 'scheme_priority')
        start_end_list = []
        if previous_schemes:
            for scheme in previous_schemes:
                start_end = str(scheme.start_date) + str(scheme.end_date)
                if start_end in start_end_list:
                    continue
                start_end_list += [start_end]
                response_data.append(self.per_scheme_data(scheme.mapped_scheme, scheme.purchase_value,
                                                          scheme.discount_percentage, scheme.incentive_earned,
                                                          scheme.start_date, scheme.end_date, scheme.sales_manager,
                                                          scheme.sales_executive))

        msg = {'is_success': True, 'message': ['OK'], 'incentive_data': incentive_data, 'data': response_data,}
        if not response_data:
            msg = {'is_success': False, 'message': ['No Scheme Found for this shop'], 'data':None}
        return Response(msg, status=status.HTTP_200_OK)

    @staticmethod
    def current_contact(shop):
        """
            Current Sales Executive and Manager for shop
        """
        sales_executive = None
        sales_manager = None

        shop_user_mapping = shop.shop_user.filter(employee_group__name='Sales Executive', status=True).last()

        if shop_user_mapping is not None:
            try:
                sales_executive = shop_user_mapping.employee
                sales_manager = shop_user_mapping.manager.employee
            except:
                sales_executive = None
                sales_manager = None
        return sales_executive, sales_manager

    @staticmethod
    def per_scheme_data(scheme, sales, discount_p, discount_val, start, end, sm, se):
        """
            Response for single scheme for shop
        """
        slabs = SchemeSlab.objects.filter(scheme=scheme)
        slab_data = SchemeSlabSerializer(slabs, many=True).data
        return {'scheme': scheme.id,
                'scheme_name': scheme.name,
                'total_sales': sales,
                'discount_percentage': discount_p,
                # 'discount_value': discount_val,
                'discount_value': 'As per the terms and conditions provided.',
                'start_date': start,
                'end_date': end,
                'slabs': slab_data,
                'se_name': se.first_name + ' ' + se.last_name if se else '',
                'se_no': se.phone_number if se else '',
                'sm_name': sm.first_name + ' ' + sm.last_name if sm else '',
                'sm_no': sm.phone_number if sm else ''}


class SalesManagerLogin(APIView):
    """
        This class is used to get the mapped 'Sales Executive' for 'Sales Manager'
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SalesExecutiveListSerializer
    queryset = ShopUserMapping.objects.all()

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True)

    def get(self, request):
        # get user from token
        user = get_user_id_from_token(request)
        if type(user) == str:
            msg = {'success': False,
                   'message': ["User is not Authorised"],
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            # check if user_type is Sales Manager
            if user.user_type == 7:  # 'Sales Manager'
                executive_list = ShopUserMapping.objects.filter(manager__in=self.get_manager(), status=True).order_by(
                    'employee').distinct('employee')
                executive_list_paginate = SmallOffsetPagination().paginate_queryset(executive_list, request)
                executive_serializer = self.serializer_class(executive_list_paginate, many=True)
                if executive_serializer.data:
                    message = [SUCCESS_MESSAGES["2001"]]
                else:
                    message = [ERROR_MESSAGES["4016"]]
                return Response({"message": message,
                                 "data": executive_serializer.data,
                                 'is_success': True}, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False,
                       'message': ["User is not Authorised"],
                       'data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        except Exception as error:
            logger.exception(error)
            return Response({"message": ["Error while getting mapped Sales Executive for Sales Manager"],
                             "data": None,
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
                   'message': ['User is not Authorised'],
                   'data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        try:
            # check if user_type is Sales Executive
            if user.user_type == 6:  # 'Sales Executive'
                month = int(request.GET.get('month')) if request.GET.get(
                    'month') else today.month

                mapped_shop_scheme_details = self.get_sales_executive_shop_scheme_details(user, month)
                messages = SUCCESS_MESSAGES["2001"]

                if mapped_shop_scheme_details is None:
                    messages = "Scheme Mapping is not exist."
                return Response({"message": [messages],
                                 "data": mapped_shop_scheme_details,
                                 'is_success': True}, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False,
                       'message': ["User is not Authorised"],
                       'data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        except Exception as error:
            logger.exception(error)
            return Response({"message": ["Error while getting data for Sales Executive"],
                             'is_success': False, 'data': None}, status=status.HTTP_200_OK)

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True)

    def get_sales_executive_shop_scheme_details(self, user, month):
        if self.request.user.user_type == 6:
            shop_mapping_object = (self.queryset.filter(
                employee=user.shop_employee.instance, status=True).order_by('shop').distinct('shop'))
        else:
            shop_mapping_object = ShopUserMapping.objects.filter(manager__in=self.get_manager(),
                                                                 employee=user.shop_employee.instance,
                                                                 status=True, shop_id=2020).order_by('shop').distinct('shop')
        if shop_mapping_object:
            scheme_shop_mapping_list = []
            scheme_data_list = []
            for shop_scheme in shop_mapping_object:
                scheme_shop_mapping = get_shop_scheme_mapping_based(shop_scheme.shop_id, month)
                if scheme_shop_mapping:
                    for scheme_sh_map in scheme_shop_mapping:
                        scheme_shop_mapping_list.append(scheme_sh_map)
                else:
                    shop = Shop.objects.filter(id=shop_scheme.shop_id).last()
                    scheme_data = shop_scheme_not_mapped(shop)
                    scheme_data_list.append(scheme_data)
            if scheme_shop_mapping_list:
                for scheme_shop_map in scheme_shop_mapping_list:
                    if month == today.month:
                        current_year = today.year
                        try:
                            scheme = scheme_shop_map.scheme
                            total_sales = get_total_sales(scheme_shop_map.shop_id, scheme_shop_map.start_date,
                                                          scheme_shop_map.end_date)
                            scheme_slab = SchemeSlab.objects.filter(scheme=scheme,
                                                                    min_value__lt=total_sales).order_by('min_value').last()
                            discount_percentage = 0
                            if scheme_slab is not None:
                                discount_percentage = scheme_slab.discount_value
                            discount_value = floor(discount_percentage * total_sales / 100)

                            # Incentive
                            incentive = Incentive.objects.filter(
                                shop_id=scheme_shop_map.shop_id, created_at__date__year=current_year,
                                created_at__date__month=today.month).last()
                            incentive_data = GetListIncentiveSerializer(incentive, read_only=True).data
                            # scheme_data = incentive_data
                            shop = Shop.objects.filter(id=scheme_shop_map.shop_id).last()
                            scheme_data = {'shop_id': shop.id,
                                           'shop_name': str(shop.shop_name),
                                           'mapped_scheme_id': str(scheme.id),
                                           'mapped_scheme': str(scheme.name),
                                           'discount_value': str(total_sales),
                                           'discount_percentage': str(discount_percentage),
                                           'incentive_earned': str(discount_value),
                                           'start_date': str(scheme_shop_map.start_date.strftime("%Y-%m-%d")),
                                           'end_date': str(scheme_shop_map.end_date.strftime("%Y-%m-%d"))
                                           }
                        except:
                            shop = Shop.objects.filter(id=scheme_shop_map.shop_id).last()
                            scheme_data = {'shop_id': shop.id,
                                           'shop_name': str(shop.shop_name),
                                           'mapped_scheme_id': str(scheme_shop_map.mapped_scheme_id),
                                           'mapped_scheme': str(scheme_shop_map.mapped_scheme.name),
                                           'discount_value': str(scheme_shop_map.purchase_value),
                                           'discount_percentage': str(scheme_shop_map.discount_percentage),
                                           'incentive_earned': str(scheme_shop_map.incentive_earned),
                                           'start_date': str(scheme_shop_map.start_date.strftime("%Y-%m-%d")),
                                           'end_date': str(scheme_shop_map.end_date.strftime("%Y-%m-%d"))
                                           }
                    else:
                        shop = Shop.objects.filter(id=scheme_shop_map.shop_id).last()
                        scheme_data = {'shop_id': shop.id,
                                       'shop_name': str(shop.shop_name),
                                       'mapped_scheme_id': str(scheme_shop_map.mapped_scheme_id),
                                       'mapped_scheme': str(scheme_shop_map.mapped_scheme.name),
                                       'discount_value': str(scheme_shop_map.purchase_value),
                                       'discount_percentage': str(scheme_shop_map.discount_percentage),
                                       'incentive_earned': str(scheme_shop_map.incentive_earned),
                                       'start_date': str(scheme_shop_map.start_date.strftime("%Y-%m-%d")),
                                       'end_date': str(scheme_shop_map.end_date.strftime("%Y-%m-%d"))
                                       }
                    scheme_data_list.append(scheme_data)
            scheme_data_list = SmallOffsetPagination().paginate_queryset(scheme_data_list, self.request)
            return scheme_data_list


class ShopSchemeDetails(APIView):
    """
       This class is used to get SchemeSlab detail based on scheme id
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        scheme_id = request.GET.get('scheme_id')
        scheme_slab = SchemeSlab.objects.filter(scheme_id=scheme_id).last()

        if scheme_slab:
            serializer = SchemeDetailSerializer(scheme_slab)
        msg = {'is_success': True, 'message': ['OK'], 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class BulkIncentiveSampleFileView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ Get API for Download sample XLSX to Create Incentive """

        # Set up the Http response.
        filename = 'incentive_sheet.xlsx'
        info_logger.info("Get API for Download sample XLSX to Create Incentive api called.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        bold = workbook.add_format({'bold': True})
        worksheet.write('A1', 'shop_id', bold)
        worksheet.write('B1', 'shop_name', bold)
        worksheet.write('C1', 'capping_applicable', bold)
        worksheet.write('D1', 'capping_value', bold)
        worksheet.write('E1', 'date_of_calculation', bold)
        worksheet.write('E1', 'total_ex_tax_delivered_value', bold)
        worksheet.write('E1', 'incentive', bold)
        row = 1
        col = 0
        worksheet.write(row, col, 322)
        worksheet.write(row, col + 1, 'Yes')
        worksheet.write(row, col + 2, 50000)
        worksheet.write(row, col + 3, '2021-11-23')
        worksheet.write(row, col + 4, 4550)
        worksheet.write(row, col + 5, 1200)

        workbook.close()
        # Rewind the buffer.
        output.seek(0)
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=%s' % filename

        return response


class BulkCreateIncentiveView(APIView):

    def get(self, request):
        scheme_slab = BulkIncentive.objects.order_by('-id')
        if scheme_slab:
            serializer = GetIncentiveSerializer(scheme_slab, many=True)
        msg = {'is_success': True, 'message': ['OK'], 'data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """ POST API for Create Bulk Incentive """
        # user = self.check_user(request.user)
        # info_logger.info("BulkIncentiveView POST api called.")
        # if type(user) == str:
        #     return Response(user, status=status.HTTP_400_BAD_REQUEST)

        incentive_serializer = IncentiveSerializer(data=request.data)
        if incentive_serializer.is_valid():
            response = incentive_serializer.save(uploaded_by=request.user)
            if isinstance(response, HttpResponse):
                return response
            return Response("File uploaded sucessfully.", status=status.HTTP_201_CREATED)
        else:
            return Response(incentive_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def check_user(self, user):
    #     if not user.user_type == 7 or not user.user_type == 6:
    #         return "User is not Authorised"
    #     return user