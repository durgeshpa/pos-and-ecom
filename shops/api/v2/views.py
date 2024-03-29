import csv
from decimal import Decimal
import logging
from datetime import datetime, timedelta

from django.db.models.aggregates import Sum
from django.db import transaction
from django.core.exceptions import ValidationError

from products.common_function import get_response, serializer_error
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.http import HttpResponse

from rest_auth import authentication
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, UpdateAPIView, CreateAPIView
from retailer_backend.utils import SmallOffsetPagination

from retailer_to_sp.models import Order, OrderedProductMapping
from addresses.models import Address, Pincode, State, City, address_type_choices, ShopRoute
from shops.models import (BeatPlanning, ParentRetailerMapping, ShopType, Shop, ShopUserMapping, RetailerType,
                          SHOP_TYPE_CHOICES)

from .serializers import (
    AddressSerializer, BeatPlanningExecutivesListSerializers, BeatPlanningExportAsCSVSerializers,
    BeatPlanningListSerializer, BeatPlanningSampleCSVSerializer, BeatPlanningSerializer, CityAddressSerializer,
    ParentRetailerMappingListSerializer, PinCodeAddressSerializer, ServicePartnerShopsSerializer, ShopTypeSerializers,
    ShopCrudSerializers, ShopTypeListSerializers, BulkUpdateShopUserMappingSampleCSVSerializer,
    ShopOwnerNameListSerializer, ShopUserMappingCrudSerializers, StateAddressSerializer, UserSerializers,
    ShopBasicSerializer, BulkUpdateShopSerializer, ShopEmployeeSerializers, ShopManagerListSerializers,
    RetailerTypeSerializer, DisapproveSelectedShopSerializers, PinCodeSerializer, CitySerializer, StateSerializer,
    BulkUpdateShopSampleCSVSerializer, BulkCreateShopUserMappingSerializer, ShopManagerListDistSerializers,
    DownloadShopStatusCSVSerializer, ShopRouteCrudSerializers, ShopRouteUploadSerializer, BulkUpdateShopStatusSerializer
)
from shops.common_functions import *
from shops.services import (related_user_search, search_beat_planning_data, shop_search, get_distinct_pin_codes,
                            get_distinct_cities, get_distinct_states, search_pincode, search_city, shop_owner_search,
                            shop_user_mapping_search, shop_manager_search, shop_employee_search, retailer_type_search,
                            shop_type_search, search_state, parent_shop_search, shop_list_search, shop_route_search)
from shops.common_validators import (
    validate_data_format, validate_id, validate_shop_id, validate_shop_owner_id, validate_state_id, validate_city_id,
    validate_pin_code, validate_data_format_without_json
)

User = get_user_model()

logger = logging.getLogger('shop-api-v2')

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

'''
@author Kamal Agarwal
'''


class ShopTypeListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShopType.objects.all()
    serializer_class = ShopTypeListSerializers

    def get(self, request):
        """ GET Shop Type List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_type_search(self.queryset, search_text)
        shop_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop_type, many=True)
        msg = "" if shop_type else "no shop found"
        return get_response(msg, serializer.data, True)


class ApprovalStatusListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ApprovalStatusList """
        info_logger.info("ApprovalStatusList GET api called.")
        fields = ['id', 'status']
        data = [dict(zip(fields, d)) for d in Shop.APPROVAL_STATUS_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ShopDocumentTypeListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ShopDocumentList """
        info_logger.info("ShopDocumentList GET api called.")
        fields = ['id', 'status']
        data = [dict(zip(fields, d))
                for d in ShopDocument.SHOP_DOCUMENTS_TYPE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ShopInvoiceStatusListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ShopInvoiceStatusList """
        info_logger.info("ShopInvoiceStatusList GET api called.")
        fields = ['id', 'status']
        data = [dict(zip(fields, d))
                for d in ShopInvoicePattern.SHOP_INVOICE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ShopOwnerNameListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShopOwnerNameListSerializer
    queryset = Shop.objects.only('shop_owner__id').distinct('shop_owner__id')

    def get(self, request):
        """ GET API for ShopOwnerNameList """
        info_logger.info("ShopOwnerNameList GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_shop_owner_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop List """
            search_text = self.request.GET.get('search_text')
            if search_text:
                self.queryset = shop_owner_search(self.queryset, search_text)
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shops_data, many=True)
        msg = ""
        return get_response(msg, serializer.data, True)


class AddressListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    add_serializer_class = AddressSerializer
    pincode_serializer_class = PinCodeAddressSerializer
    city_serializer_class = CityAddressSerializer
    state_serializer_class = StateAddressSerializer

    queryset = Address.objects.all()

    def get(self, request):
        """ GET API for Address """
        info_logger.info("Address GET api called.")

        if request.GET.get('pin_code'):
            """ Get Address for specific Pin Code """
            id_validation = validate_pin_code(
                self.queryset, int(request.GET.get('pin_code')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            self.queryset = id_validation['data']

        if request.GET.get('city_id'):
            """ Get Address for specific City ID """
            id_validation = validate_city_id(
                self.queryset, int(request.GET.get('city_id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            self.queryset = id_validation['data']

        if request.GET.get('state_id'):
            """ Get Address for specific State ID """
            id_validation = validate_state_id(
                self.queryset, int(request.GET.get('state_id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            self.queryset = id_validation['data']

        address_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        pin_code_list = get_distinct_pin_codes(self.queryset)
        city_list = get_distinct_cities(self.queryset)
        state_list = get_distinct_states(self.queryset)
        add_serializer = self.add_serializer_class(address_data, many=True)
        data = {
            'addresses': add_serializer.data,
            'pin_codes': self.pincode_serializer_class(pin_code_list, many=True).data,
            'cities': self.city_serializer_class(city_list, many=True).data,
            'states': self.state_serializer_class(state_list, many=True).data
        }

        msg = "" if address_data else "no Address found"
        return get_response(msg, data, True)


class RelatedUsersListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = UserSerializers
    queryset = get_user_model().objects.all()

    def get(self, request):
        """ GET API for RelatedUsersList """
        info_logger.info("RelatedUsersList GET api called.")
        if request.GET.get('id'):
            """ Get User for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            related_users_data = id_validation['data']
        else:
            """ GET Users List """
            search_text = self.request.GET.get('search_text')
            if search_text:
                self.queryset = related_user_search(self.queryset, search_text)
            related_users_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(related_users_data, many=True)
        msg = ""
        return get_response(msg, serializer.data, True)


class ShopCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.order_by('-id')
    serializer_class = ShopCrudSerializers

    def get(self, request):
        """ GET API for Shop """
        info_logger.info("Shop GET api called.")
        shop_total_count = self.queryset.count()
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
            shop_total_count = self.queryset.count()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_data, many=True)
        msg = f"total count {shop_total_count}" if shops_data else "no shop found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Shop Creation with Image """

        info_logger.info("Shop POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Shop Created Successfully.")
            return get_response('shop created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Shop Updation with Image """

        info_logger.info("Shop PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update shop', False)

        # validations for input id
        id_validation = validate_shop_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        shop_instance = id_validation['data']

        serializer = self.serializer_class(instance=shop_instance, data=modified_data, context={'request':request})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Shop Updated Successfully.")
            return get_response('shop updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Shop with image """

        info_logger.info("Shop DELETE api called.")
        if not request.data.get('shop_id'):
            return get_response('please provide shop_id', False)
        try:
            for s_id in request.data.get('shop_id'):
                shop_id = self.queryset.get(id=int(s_id))
                try:
                    shop_id.delete()
                except:
                    return get_response(f'can not delete shop | {shop_id.shop_name} | getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid shop id {s_id}', False)
        return get_response('shop were deleted successfully!', True)

    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        shop_type = self.request.GET.get('shop_type')
        shop_owner = self.request.GET.get('shop_owner')
        pin_code = self.request.GET.get('pin_code')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')
        approval_status = self.request.GET.get('approval_status')
        route = self.request.GET.get('route')

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

        if route:
            self.queryset = self.queryset.filter(shop_routes__route_id=route)

        return self.queryset.distinct('id')


class SellerShopFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.filter(id=600).order_by('-id')
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


class ShopSalesReportView(APIView):
    permission_classes = (AllowAny,)

    def get_sales_report(self, shop_id, start_date, end_date):
        try:
            seller_shop = Shop.objects.get(pk=int(shop_id))
        except:
            return {'error': '{} shop not found'.format(shop_id)}
        orders = Order.objects.using('readonly').filter(seller_shop=seller_shop). \
            exclude(order_status__in=['CANCELLED', 'DENIED']) \
            .select_related('ordered_cart').prefetch_related('ordered_cart__rt_cart_list')
        if start_date:
            orders = orders.using('readonly').filter(created_at__date__gte=start_date)
        if end_date:
            orders = orders.using('readonly').filter(created_at__date__lte=end_date)
        ordered_list = []
        ordered_items = {}
        for order in orders:
            order_shipments = OrderedProductMapping.objects.using('readonly').filter(ordered_product__order=order)
            for cart_product_mapping in order.ordered_cart.rt_cart_list.all():
                product = cart_product_mapping.cart_product
                product_id = cart_product_mapping.cart_product.id
                product_name = cart_product_mapping.cart_product.product_name
                product_sku = cart_product_mapping.cart_product.product_sku
                product_brand = cart_product_mapping.cart_product.product_brand.brand_name
                ordered_qty = cart_product_mapping.no_of_pieces
                all_tax_list = cart_product_mapping.cart_product.product_pro_tax
                # shopName = seller_shop

                product_shipments = order_shipments.filter(product=product)
                product_shipments = product_shipments.aggregate(Sum('delivered_qty'))['delivered_qty__sum']
                if not product_shipments:
                    product_shipments = 0
                tax_sum, get_tax_val = 0, 0
                if all_tax_list.exists():
                    for tax in all_tax_list.using('readonly').all():
                        tax_sum = float(tax_sum) + \
                                  float(tax.tax.tax_percentage)
                    tax_sum = round(tax_sum, 2)
                    get_tax_val = tax_sum / 100
                seller_shop = Shop.objects.filter(
                    id=order.seller_shop_id).last()
                buyer_shop = Shop.objects.filter(id=order.buyer_shop_id).last()
                try:
                    product_price_to_retailer = cart_product_mapping.get_cart_product_price(seller_shop,
                                                                                            buyer_shop).get_per_piece_price(
                        cart_product_mapping.qty)
                except:
                    product_price_to_retailer = 0
                ordered_amount = (Decimal(product_price_to_retailer)
                                  * Decimal(ordered_qty)) / (Decimal(get_tax_val) + 1)
                ordered_tax_amount = (ordered_amount * Decimal(get_tax_val))
                delivered_amount = float((Decimal(
                    product_price_to_retailer) * Decimal(product_shipments)) / (Decimal(get_tax_val) + 1))
                delivered_tax_amount = float(
                    (delivered_amount * float(get_tax_val)))
                if product_sku in ordered_items:
                    ordered_items['ordered_qty'] += ordered_qty
                    ordered_items['ordered_amount'] += ordered_amount
                    ordered_items['ordered_tax_amount'] += ordered_tax_amount
                    ordered_items['delivered_qty'] += product_shipments
                    ordered_items['delivered_amount'] += delivered_amount
                    ordered_items['delivered_tax_amount'] += delivered_tax_amount
                else:
                    ordered_items = {'product_sku': product_sku, 'product_id': product_id, 'product_name': product_name,
                                     'product_brand': product_brand, 'ordered_qty': ordered_qty,
                                     'delivered_qty': product_shipments,
                                     'ordered_amount': ordered_amount, 'ordered_tax_amount': ordered_tax_amount,
                                     'delivered_amount': delivered_amount, 'delivered_tax_amount': delivered_tax_amount,
                                     'seller_shop': seller_shop}
                    ordered_list.append(ordered_items)
        data = ordered_list
        return data

    def get(self, *args, **kwargs):
        from django.http import HttpResponse
        shop_id = self.request.GET.get('shop')
        start_date = self.request.GET.get('start_date', None)
        end_date = self.request.GET.get('end_date', None)
        if end_date and end_date < start_date:
            logger.error(self.request, 'End date cannot be less than the start date')
            return get_response("End date cannot be less than the start date", {}, False)

        if (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(30)) > datetime.strptime(start_date, "%Y-%m-%d"):
            return get_response("max duration is 30 days only in start & end date", {}, False)
        data = self.get_sales_report(shop_id, start_date, end_date)
        if 'error' in data:
            return get_response(data['error'], {}, False)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'SKU', 'Product Name', 'Brand', 'Ordered Qty', 'Delivered Qty', 'Ordered Amount',
                         'Ordered Tax Amount', 'Delivered Amount', 'Delivered Tax Amount', 'Seller_shop'])
        for dic in data:
            writer.writerow(
                [dic['product_id'], dic['product_sku'], dic['product_name'], dic['product_brand'], dic['ordered_qty'],
                 dic['delivered_qty'], dic['ordered_amount'], dic['ordered_tax_amount'], dic['delivered_amount'],
                 dic['delivered_tax_amount'], dic['seller_shop']])

        return response


class ServicePartnerShopsListView(generics.ListAPIView):
    queryset = Shop.objects.select_related('shop_owner', 'shop_type', 'shop_type__shop_sub_type', ) \
        .filter(shop_type__shop_type__in=['sp', ]) \
        .only('id', 'shop_name', 'status', 'shop_type__shop_type', 'shop_type__shop_sub_type__retailer_type_name',
              'shop_owner__first_name', 'shop_owner__last_name', 'shop_owner__phone_number',)
    serializer_class = ServicePartnerShopsSerializer
    permission_classes = (AllowAny,)

    def list(self, request, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return get_response("", serializer.data, True)


class ParentShopsListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ParentRetailerMapping.objects.filter(status=True). \
        select_related('parent', 'parent__shop_owner', 'parent__shop_type', 'parent__shop_type__shop_sub_type',) \
        .only('parent__id', 'parent__shop_name', 'parent__status', 'parent__shop_owner__id',
              'parent__shop_owner__first_name', 'parent__shop_owner__last_name', 'parent__shop_owner__phone_number',
              'parent__shop_type__shop_type', 'parent__shop_type__shop_sub_type__retailer_type_name',) \
        .distinct('parent__id')
    serializer_class = ParentRetailerMappingListSerializer

    def get(self, request):
        info_logger.info("Shop GET api called.")
        """ GET Shop List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = parent_shop_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no shop found"
        return get_response(msg, serializer.data, True)


class ShopListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.filter(approval_status=2).select_related('shop_owner', 'shop_type') \
        .only('id', 'shop_name', 'shop_owner', 'shop_type').order_by('-id')
    serializer_class = ShopBasicSerializer

    def get(self, request):
        info_logger.info("Shop GET api called.")
        """ GET Shop List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_list_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no shop found"
        return get_response(msg, serializer.data, True)


class ShopManagerListDisView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    # get 'Sales Manager'
    queryset = ShopUserMapping.objects.select_related('manager', 'employee', ).filter(employee__user_type=7).distinct('employee')
    serializer_class = ShopManagerListDistSerializers

    def get(self, request):
        info_logger.info("Shop Manager GET api called.")
        """ GET Shop Manager List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_manager_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no shop manager found"
        return get_response(msg, serializer.data, True)


class ShopManagerListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    # get 'Sales Manager'
    queryset = ShopUserMapping.objects.select_related('manager', 'employee',).\
        filter(employee__user_type=7, employee_group__permissions__codename='can_sales_manager_add_shop',
               status=True).order_by('-id')
    # queryset = ShopUserMapping.objects.filter(employee_group__permissions__codename='can_sales_manager_add_shop').\
    #     distinct('employee')
    serializer_class = ShopManagerListSerializers

    def get(self, request):
        info_logger.info("Shop Manager GET api called.")
        """ GET Shop Manager List """
        shop_id = self.request.GET.get('shop_id')
        if shop_id:
            self.queryset = self.queryset.filter(shop_id=shop_id)
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_manager_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no shop manager found"
        return get_response(msg, serializer.data, True)


class ShopEmployeeListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = get_user_model().objects.values('id', 'phone_number', 'first_name', 'last_name').order_by('-id')
    serializer_class = ShopEmployeeSerializers

    def get(self, request):
        info_logger.info("Shop Employee api called.")
        """ GET Shop Employee List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_employee_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no employee found"
        return get_response(msg, serializer.data, True)


class ShopUserMappingView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShopUserMapping.objects.select_related('shop', 'shop__shop_type', 'shop__shop_owner', 'manager',
                                                      'employee', 'employee_group', ). \
        prefetch_related('shop_user_map_log', 'shop_user_map_log__updated_by', ) \
        .only('id', 'status', 'created_at', 'shop', 'shop__status', 'shop__shop_owner', 'shop__shop_owner__id',
              'shop__shop_name', 'shop__shop_type', 'shop__shop_owner', 'shop__shop_code', 'updated_by__id',
              'updated_by__first_name', 'updated_by__phone_number', 'updated_by__last_name', 'shop__shop_owner__id',
              'shop__shop_owner__first_name', 'shop__shop_owner__phone_number', 'manager',
              'shop__shop_owner__last_name', 'employee_group', 'employee', 'employee__id', 'employee__first_name',
              'employee__last_name', 'employee__phone_number', ).order_by('-id')

    serializer_class = ShopUserMappingCrudSerializers

    def get(self, request):
        """ GET API for ShopUserMapping """
        info_logger.info("ShopUserMapping GET api called.")
        shop_user_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get ShopUserMapping for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET ShopUserMapping List """
            try:
                self.queryset = self.search_filter_shop_user_mapping_data()
            except Exception as e:
                return get_response(",".join(e), False)
            shop_user_total_count = self.queryset.count()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_data, many=True)
        msg = f"total count {shop_user_total_count}" if shops_data else "no shop mapping found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Shop Mapping"""

        info_logger.info("Shop POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Shop Mapping Created Successfully.")
            return get_response('shop mapping created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Shop Mapping Updation """

        info_logger.info("Shop Mapping PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update shop mapping', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        sho_user_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=sho_user_instance, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Shop Mapping Updated Successfully.")
            return get_response('shop mapping updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    # @transaction.atomic
    def delete(self, request):
        """ Delete Shop User Mapping """

        info_logger.info("ShopUser Mapping DELETE api called.")
        if not request.data.get('shop_user_mapping_id'):
            return get_response('please select shop user mapping id to delete shop user mapping', False)
        try:
            for id in request.data.get('shop_user_mapping_id'):
                shop_user_mapped_id = self.queryset.get(id=int(id))
                try:
                    shop_user_mapped_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'shap_user_mapped_id': shop_user_mapped_id}
                    info_logger.info("shap_user_mapped_id deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete user shop mapping {shop_user_mapped_id}, '
                                        f'because this user shop mapping getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid shop user mapping id {id}', False)
        return get_response('shop user mapping were deleted successfully!', True)

    def search_filter_shop_user_mapping_data(self):
        search_text = self.request.GET.get('search_text')
        shop_id = self.request.GET.get('shop_id')
        manager_id = self.request.GET.get('manager_id')
        emp_id = self.request.GET.get('emp_id')
        status = self.request.GET.get('status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        '''search using shop_name and parent_shop based on criteria that matches'''
        if search_text:
            self.queryset = shop_user_mapping_search(self.queryset, search_text)
        '''Filters using shop_id, manager_id, emp_id, city, status, start_date'''
        if shop_id:
            self.queryset = self.queryset.filter(shop__id=shop_id)
        if manager_id:
            self.queryset = self.queryset.filter(manager__employee__id=manager_id)
        if emp_id:
            self.queryset = self.queryset.filter(employee__id=emp_id)
        if status:
            self.queryset = self.queryset.filter(status=status)

        if (end_date and not start_date) or (start_date and not end_date):
            raise ValidationError("please select both start & end date")

        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("End date should be greater than start date")
            self.queryset = self.queryset.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        return self.queryset.distinct('id')


class ShopTypeChoiceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET ShopTypeChoice List for ShopType Creation"""

        info_logger.info("ShopTypeChoiceView GET api called.")
        """ GET ShopTypeChoiceView List """
        fields = ['shop_type', 'shop_type_name', ]
        data = [dict(zip(fields, d)) for d in SHOP_TYPE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class RetailerTypeList(GenericAPIView):
    queryset = RetailerType.objects.values('id', 'retailer_type_name')
    serializer_class = RetailerTypeSerializer

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = retailer_type_search(self.queryset, search_text)
        retailer_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(retailer_type, many=True)
        msg = "" if retailer_type else "no retailer type found"
        return get_response(msg, serializer.data, True)


class ShopTypeView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShopType.objects.select_related('shop_sub_type', 'updated_by', ). \
        prefetch_related('shop_type_log', 'shop_type_log__updated_by', ) \
        .only('id', 'shop_sub_type', 'updated_by', 'shop_type', 'shop_min_amount').order_by('-id')
    serializer_class = ShopTypeSerializers

    def get(self, request):
        """ GET Shop Type List """
        shop_type_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Shop Type for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_type_data = id_validation['data']
        else:
            """ GET Shop Type List """
            self.queryset = self.search_shop_type()
            shop_type_total_count = self.queryset.count()
            shops_type_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_type_data, many=True)
        msg = f"total count {shop_type_total_count}" if shops_type_data else "no shop type found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Shop Type"""

        info_logger.info("Shop Type POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Shop Type Created Successfully.")
            return get_response('shop type created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Shop Type Updation """

        info_logger.info("Shop Type PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update shop type', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        sho_user_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=sho_user_instance, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Shop Type Updated Successfully.")
            return get_response('shop type updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Shop Type """

        info_logger.info("Shop Type DELETE api called.")
        if not request.data.get('shop_type_id'):
            return get_response('please select shop type id to delete shop type', False)
        try:
            for s_id in request.data.get('shop_type_id'):
                shop_type_obj = self.queryset.get(id=int(s_id))
                try:
                    shop_type_obj.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'shop_type_id': shop_type_obj}
                    info_logger.info("shop_type_id deleted info ", dict_data)
                except Exception as e:
                    return get_response(f'You can not delete shop type {shop_type_obj}, '
                                        f'because this shop type getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid shop type id {s_id}', False)
        return get_response('shop type were deleted successfully!', True)

    def search_shop_type(self):
        search_text = self.request.GET.get('search_text')
        shop_type = self.request.GET.get('shop_type')
        status = self.request.GET.get('status')

        '''search using shop_type based on criteria that matches'''
        if search_text:
            self.queryset = shop_type_search(self.queryset, search_text)

        if shop_type:
            self.queryset = self.queryset.filter(id=shop_type)
        if status:
            self.queryset = self.queryset.filter(status=status)

        return self.queryset


class DisapproveShopSelectedShopView(UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    shop_list = Shop.objects.values('id', )
    serializer_class = DisapproveSelectedShopSerializers

    def put(self, request):
        """ PUT API for Disapproved Selected Shop """

        info_logger.info("Shop Disapproved PUT api called.")
        serializer = self.serializer_class(instance=self.shop_list.filter(id__in=request.data['shop_id_list']),
                                           data=request.data, partial=True, context = {'request': request})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('shop disapproved successfully!', True)
        return get_response(serializer_error(serializer), None)


class StateView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = State.objects.only('id', 'state_name', )
    serializer_class = StateSerializer

    def get(self, request):
        """ GET API for Shop """
        info_logger.info("State GET api called.")

        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = search_state(self.queryset, search_text)
        state_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(state_data, many=True)
        msg = "" if state_data else "no state found"
        return get_response(msg, serializer.data, True)


class CityView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = City.objects.select_related('state').only('id', 'city_name', 'state')
    serializer_class = CitySerializer

    def get(self, request):
        """ GET API for City """
        info_logger.info("City GET api called.")
        state_id = self.request.GET.get('state_id', None)
        if state_id:
            self.queryset = self.queryset.filter(state__id=state_id)
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = search_city(self.queryset, search_text)
        city_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(city_data, many=True)
        msg = "" if city_data else "no city found"
        return get_response(msg, serializer.data, True)


class PinCodeView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Pincode.objects.select_related('city').only('id', 'city', 'pincode')
    serializer_class = PinCodeSerializer

    def get(self, request):
        """ GET API for PinCode """
        info_logger.info("PinCode GET api called.")
        search_text = self.request.GET.get('search_text')
        city_id = self.request.GET.get('city_id', None)
        if city_id:
            self.queryset = self.queryset.filter(city__id=city_id)
        if search_text:
            self.queryset = search_pincode(self.queryset, search_text)
        pin_code_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(pin_code_data, many=True)
        msg = "" if pin_code_data else "no pincode found"
        return get_response(msg, serializer.data, True)


class AddressTypeChoiceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET AddressTypeChoice List for Shop Creation"""

        info_logger.info("AddressTypeChoiceView GET api called.")
        """ GET address_type_choices List """
        fields = ['address_type', 'address_type_name', ]
        data = [dict(zip(fields, d)) for d in address_type_choices]
        msg = ""
        return get_response(msg, data, True)


class BulkUpdateShopSampleCSV(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkUpdateShopSampleCSVSerializer

    def post(self, request):
        """ POST API for Download Selected Shop CSV """

        info_logger.info("BulkUpdateShopSampleCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("BulkUpdateShopSample CSV Exported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class BulkCreateShopUserMappingSampleCSV(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkUpdateShopUserMappingSampleCSVSerializer

    def get(self, request):
        filename = "shop_user_list.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(['shop_id', 'manager', 'employee', 'employee_group'])
        writer.writerow(['23', '8989787878', '8989898989', '2'])
        return HttpResponse(response, content_type='text/csv')


class BulkCreateShopUserMappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkCreateShopUserMappingSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)


class BulkUpdateShopView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkUpdateShopSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('shops updated successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)


class BeatPlanningExecutivesListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = None

    queryset = User.objects.all()

    def get(self, request):
        info_logger.info("Executive GET api called.")
        """ GET Executive List """
        search_text = self.request.GET.get('search_text')

        # get manager object
        shop_mapping_object = ShopUserMapping.objects.filter(
            employee=request.user.shop_employee.instance,
            employee_group__permissions__codename='can_sales_manager_add_shop', status=True)

        # condition to check the current user is super user  or manager
        if request.user.shop_employee.instance.is_superuser:
            self.queryset = self.queryset. \
                filter(user_type=6, shop_employee__employee_group__name__iexact='Sales Executive', is_active=True). \
                distinct('id')
            self.serializer_class = ShopEmployeeSerializers
            if search_text:
                self.queryset = shop_employee_search(self.queryset, search_text)
        else:
            self.serializer_class = BeatPlanningExecutivesListSerializers
            self.queryset = ShopUserMapping.objects. \
                filter(employee__user_type=6, employee_group__name__iexact='Sales Executive',
                       manager__in=shop_mapping_object, status=True).distinct('employee_id')
            if search_text:
                self.queryset = shop_manager_search(self.queryset, search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no shop manager found"
        return get_response(msg, serializer.data, True)


class BeatPlanningExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BeatPlanningExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Beat Planning CSV """

        info_logger.info("BeatPlanningExportAsCSVView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Beat Planning CSV exported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class BeatPlanningListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = BeatPlanning.objects.select_related('manager', 'executive'). \
        only('id', 'status', 'created_at', 'modified_at', 'manager__id', 'executive__id'). \
        order_by('-id')
    serializer_class = BeatPlanningListSerializer

    def get(self, request):
        """ GET API for BeatPlanning """
        info_logger.info("BeatPlanning GET api called.")
        manager_id = self.request.GET.get('manager_id', None)
        executive_id = self.request.GET.get('executive_id', None)
        status = self.request.GET.get('status', None)
        if manager_id:
            self.queryset = self.queryset.filter(manager__id=manager_id)
        if executive_id:
            self.queryset = self.queryset.filter(executive__id=executive_id)
        if status:
            self.queryset = self.queryset.filter(status=status)
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = search_beat_planning_data(self.queryset, search_text)
        bp_total_count = self.queryset.count()
        beat_planning_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(beat_planning_data, many=True)
        msg = f"total count {bp_total_count}" if beat_planning_data else "no beat planning found"
        return get_response(msg, serializer.data, True)

    def delete(self, request):
        """ Delete Beat Planning """

        info_logger.info("Beat Planning DELETE api called.")
        if not request.data.get('beat_planning_id'):
            return get_response('please select beat planning id to delete beat planning', False)
        try:
            for id in request.data.get('beat_planning_id'):
                beat_planning_id = self.queryset.get(id=int(id))
                try:
                    beat_planning_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'shap_user_mapped_id': beat_planning_id}
                    info_logger.info("shap_user_mapped_id deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete beat planning {beat_planning_id}, '
                                        f'because this beat planning getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid beat planning id {id}', False)
        return get_response('beat planning were deleted successfully!', True)


class BeatPlanningSampleCSV(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BeatPlanningSampleCSVSerializer

    def post(self, request):
        """ POST API for Download Sample CSV for Beat Planning """

        info_logger.info("BeatPlanningSampleCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save(created_by=request.user)
            info_logger.info("BeatPlanningSampleCSV Exported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class BeatPlanningView(GenericAPIView):
    """
    This class is used to upload csv file for sales executive to set the Beat Plan
    """
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BeatPlanningSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)


class DownloadShopStatusCSV(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = DownloadShopStatusCSVSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ShopRouteCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShopRoute.objects.order_by('-id')
    serializer_class = ShopRouteCrudSerializers

    def get(self, request):
        """ GET API for Shop Route """
        info_logger.info("Shop Route GET api called.")
        shop_route_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Shop Route for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop Route List """
            self.queryset = self.search_filter_shops_data()
            shop_route_total_count = self.queryset.count()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_data, many=True)
        msg = f"total count {shop_route_total_count}" if shops_data else "no shop route found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Shop Route Creation with Image """

        info_logger.info("Shop Route POST api called.")
        modified_data = validate_data_format_without_json(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Shop Route Created Successfully.")
            return get_response('shop route created successfully!', serializer.data, True)
        return get_response(serializer_error(serializer))

    def put(self, request):
        """ PUT API for Shop Route Updation with Image """

        info_logger.info("Shop Route PUT api called.")
        modified_data = validate_data_format_without_json(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update shop')

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        shop_route_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=shop_route_instance, data=modified_data, context={'request':request})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Shop Route Updated Successfully.")
            return get_response('shop route updated!', serializer.data, True)
        return get_response(serializer_error(serializer))

    def delete(self, request):
        """ Delete Shop Route with image """

        info_logger.info("Shop Route DELETE api called.")
        if not request.data.get('shop_route_id'):
            return get_response('please provide shop_route_id')
        try:
            for s_id in request.data.get('shop_route_id'):
                shop_route_id = self.queryset.get(id=int(s_id))
                try:
                    shop_route_id.delete()
                except:
                    return get_response(f'can not delete shop route | {shop_route_id.shop_route_name} | getting used')
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid shop route id.')
        return get_response('shop were deleted successfully!', None, True)

    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        shop_id = self.request.GET.get('shop_id')
        route_id = self.request.GET.get('route_id')
        city = self.request.GET.get('city')

        '''search using shop_name, route city name & route name based on criteria that matches'''
        if search_text:
            self.queryset = shop_route_search(self.queryset, search_text)

        '''Filters using shop_id, route_id, city'''
        if shop_id:
            self.queryset = self.queryset.filter(shop_id=shop_id)

        if route_id:
            self.queryset = self.queryset.filter(route_id=route_id)

        if city:
            self.queryset = self.queryset.filter(route__city__id=city)

        return self.queryset.distinct('id')


class ShopRouteSampleFile(generics.GenericAPIView):

    def get(self, request, *args, **kwargs):
        """
        This function will return an Sample File in csv format which can be used for Downloading RetailerCatalogue Sample File
        (It is used when user wants to create new retailer products)
        """
        filename = "shop_route_sample_file.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(["shop_id", "shop_name", "city_id", "city_name", "route_id", "route"])
        writer.writerow([45887, "Shiv Store", 33, "Gwalior", 1, "abc"])
        writer.writerow([45886, "Bajrang fram fresh", 33, "Gwalior", 1, "abc"])
        return response


class ShopRouteUploadView(generics.GenericAPIView):
    """
    This class is used to upload csv file for Shop Route to map the route with shop
    """
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ShopRouteUploadSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)


class ShopDeActivateChoiceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET ShopDeActivateChoice List for Shop Updation"""

        info_logger.info("ShopDeActivateChoiceView GET api called.")
        """ GET ShopDeActivateChoiceView List """
        fields = ['key', 'value', ]
        data = [dict(zip(fields, d)) for d in Shop.DISAPPROVED_STATUS_REASON_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class BulkShopStatusUpdateView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkUpdateShopStatusSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)
