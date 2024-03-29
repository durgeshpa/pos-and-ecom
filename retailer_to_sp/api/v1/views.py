import logging
import math
import re
import json
from django.core.mail import send_mail
import codecs
from django.http import HttpResponse
from datetime import date as datetime_date
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha512
from operator import itemgetter
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Sum, Q, Case, When, Value, FloatField, IntegerField
from django.core.files.base import ContentFile
from django.db import transaction, models
from django.db.models import F, Sum, Q, Count, Value, Case, When, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from num2words import num2words
from rest_framework import status, generics, permissions
from rest_auth import authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_auth.authentication import TokenAuthentication
from retailer_backend import common_function
from wkhtmltopdf.views import PDFTemplateResponse
from pyfcm import FCMNotification

from accounts.api.v1.serializers import PosUserSerializer, PosShopUserSerializer
from addresses.models import Address, City, Pincode
from audit.views import BlockUnblockProduct
from barCodeGenerator import barcodeGen, qrCodeGen, merged_barcode_gen
from global_config.views import get_config, get_config_fofo_shops, get_config_fofo_shop
from pos.payU_payment import send_request_refund
from shops.models import Shop, ParentRetailerMapping, ShopUserMapping, ShopMigrationMapp, PosShopUserMapping, \
    FOFOConfig, ShopTiming
from brand.models import Brand
from categories import models as categorymodel
from common.common_utils import (create_file_name, single_pdf_file, create_merge_pdf_name, merge_pdf_files,
                                 create_invoice_data, whatsapp_opt_in, whatsapp_order_cancel, whatsapp_order_refund,
                                 whatsapp_order_delivered, sms_order_delivered, sms_out_for_delivery,
                                 sms_order_dispatch, sms_order_placed, return_item_home_pickup, return_item_drop)
from common.constants import PREFIX_CREDIT_NOTE_FILE_NAME, ZERO, PREFIX_INVOICE_FILE_NAME, INVOICE_DOWNLOAD_ZIP_NAME, \
    PREFIX_RETURN_CHALLAN_FILE_NAME, BULK_CREATE_NO_OF_RECORDS
from common.data_wrapper_view import DataWrapperViewSet
from coupon.models import Coupon, CusotmerCouponUsage
from coupon.serializers import CouponSerializer
from ecom.api.v1.serializers import EcomOrderListSerializer, EcomShipmentSerializer, PastPurchasedProductSerializer, \
    RetailerProductSerializer
from ecom.models import Address as EcomAddress, EcomOrderAddress, UserPastPurchases
from ecom.utils import check_ecom_user_shop, check_ecom_user
from global_config.models import GlobalConfig
from global_config.views import get_config_fofo_shop
from gram_to_brand.models import (GRNOrderProductMapping, OrderedProductReserved as GramOrderedProductReserved,
                                  PickList, ProductGRNCostPriceMapping)
from marketing.models import ReferralCode
from pos import error_code
from pos.api.v1.serializers import (BasicCartSerializer, BasicCartListSerializer, CheckoutSerializer,
                                    BasicOrderSerializer, BasicOrderListSerializer, OrderReturnCheckoutSerializer,
                                    OrderedDashBoardSerializer, PosShopSerializer, BasicCartUserViewSerializer,
                                    OrderReturnGetSerializer, BasicOrderDetailSerializer, AddressCheckoutSerializer,
                                    RetailerProductResponseSerializer, PosShopUserMappingListSerializer,
                                    PaymentTypeSerializer, PosEcomOrderDetailSerializer,
                                    RetailerOrderedDashBoardSerializer, PosEcomShopSerializer)
from pos.common_functions import (api_response, delete_cart_mapping, ORDER_STATUS_MAP, RetailerProductCls,
                                  update_customer_pos_cart, PosInventoryCls, RewardCls, serializer_error,
                                  check_pos_shop, PosAddToCart, PosCartCls, ONLINE_ORDER_STATUS_MAP,
                                  pos_check_permission_delivery_person, ECOM_ORDER_STATUS_MAP, get_default_qty,
                                  pos_check_user_permission, mark_pos_product_online_enabled, coupon_point_update)
from pos.models import (RetailerProduct, Payment as PosPayment,
                        PaymentType, MeasurementUnit, PosTrip)
from pos.offers import BasicCartOffers
from pos.tasks import update_es, order_loyalty_points_credit
from products.models import ProductPrice, ProductOption, Product
from retailer_backend.common_function import getShopMapping, checkNotShopAndMapping, return_order_id_pattern
from retailer_backend.messages import ERROR_MESSAGES
from retailer_backend.utils import SmallOffsetPagination
from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping,
                                     Order as GramMappedOrder)
from retailer_to_sp.common_function import check_date_range, capping_check, generate_credit_note_id, \
    get_logged_user_wise_query_set_for_trip_invoices
from retailer_to_sp.common_function import dispatch_trip_search, trip_search
from retailer_to_sp.common_function import getShopLicenseNumber, getShopCINNumber, getGSTINNumber, getShopPANNumber
from retailer_to_sp.models import (Cart, CartProductMapping, CreditNote, LastMileTripReturnMapping, Order,
                                   OrderedProduct, Payment, CustomerCare,
                                   Feedback, OrderedProductMapping as ShipmentProducts, Return, Trip, PickerDashboard,
                                   ShipmentRescheduling, Note, OrderedProductBatch,
                                   OrderReturn, ReturnItems, OrderedProductMapping, ShipmentPackaging,
                                   DispatchTrip, DispatchTripShipmentMapping, INVOICE_AVAILABILITY_CHOICES,
                                   DispatchTripShipmentPackages, LastMileTripShipmentMapping, PACKAGE_VERIFY_CHOICES,
                                   DispatchTripCrateMapping, ShipmentPackagingMapping, TRIP_TYPE_CHOICE, ShopCrate,
                                   LastMileTripShipmentPackages, ShipmentNotAttempt, RoundAmount,
                                   ReturnOrder, ReturnOrderProduct, ReturnOrderProductImage, Barcode, BarcodeGenerator,
                                   ReturnProductBatch, DispatchTripReturnOrderMapping, CartOffers)

from retailer_to_sp.tasks import send_invoice_pdf_email, insert_search_term
from shops.api.v1.serializers import ShopBasicSerializer, SellerShopSerializer
from sp_to_gram.models import OrderedProductReserved
from sp_to_gram.tasks import es_search, upload_shop_stock, upload_all_products_in_es
from wms.common_functions import OrderManagement, get_stock, is_product_not_eligible, get_response, \
    get_logged_user_wise_query_set_for_shipment, get_logged_user_wise_query_set_for_dispatch, \
    get_logged_user_wise_query_set_for_dispatch_trip, get_logged_user_wise_query_set_for_dispatch_crates, \
    get_logged_user_wise_query_set_for_shipment_packaging, return_putaway
from wms.common_validators import validate_id, validate_data_format, validate_data_days_date_request, validate_shipment
from retailer_backend.settings import AWS_MEDIA_URL
from wms.models import OrderReserveRelease, InventoryType, PosInventoryState, PosInventoryChange, Crate
from zoho.models import ZohoInvoice

from wms.views import shipment_not_attempt_inventory_change, shipment_reschedule_inventory_change
from .serializers import (ProductsSearchSerializer, CartSerializer, OrderSerializer,
                          CustomerCareSerializer, OrderNumberSerializer, GramPaymentCodSerializer,
                          GramMappedCartSerializer, GramMappedOrderSerializer,
                          OrderDetailSerializer, OrderedProductSerializer, OrderedProductMappingSerializer,
                          RetailerShopSerializer, SellerOrderListSerializer, OrderListSerializer,
                          ReadOrderedProductSerializer, FeedBackSerializer,
                          ShipmentDetailSerializer, SuperStoreCartSerializer, TripSerializer, ShipmentSerializer,
                          PickerDashboardSerializer,
                          ShipmentReschedulingSerializer, ShipmentReturnSerializer, ParentProductImageSerializer,
                          ShopSerializer, OrderPaymentStatusChangeSerializers,
                          ShipmentProductSerializer, RetailerOrderedProductMappingSerializer,
                          ShipmentQCSerializer, ShipmentPincodeFilterSerializer, CitySerializer,
                          DispatchItemsSerializer, DispatchDashboardSerializer,
                          UserSerializers, DispatchTripCrudSerializers, DispatchInvoiceSerializer,
                          TripSummarySerializer, ShipmentNotAttemptSerializer, DispatchTripStatusChangeSerializers,
                          LoadVerifyPackageSerializer, ShipmentPackageSerializer, TripShipmentMappingSerializer,
                          UnloadVerifyPackageSerializer, LastMileTripCrudSerializers,
                          LastMileTripShipmentsSerializer, VerifyRescheduledShipmentPackageSerializer,
                          ShipmentCompleteVerifySerializer, VerifyReturnShipmentProductsSerializer,
                          ShipmentCratesValidatedSerializer, LastMileTripStatusChangeSerializers,
                          ShipmentDetailsByCrateSerializer, LoadVerifyCrateSerializer, UnloadVerifyCrateSerializer,
                          DispatchTripShipmentMappingSerializer, PackagesUnderTripSerializer,
                          MarkShipmentPackageVerifiedSerializer, ShipmentPackageProductsSerializer,
                          DispatchCenterCrateSerializer, DispatchCenterShipmentPackageSerializer,
                          LoadLastMileInvoiceSerializer, LastMileTripSummarySerializer,
                          LastMileLoadVerifyPackageSerializer, RemoveLastMileInvoiceFromTripSerializer,
                          VerifyNotAttemptShipmentPackageSerializer, VerifyShipmentPackageSerializer,
                          DetailedShipmentPackageInfoSerializer, DetailedShipmentPackagingMappingInfoSerializer,
                          VerifyBackwardTripItemsSerializer, BackwardTripQCSerializer, PosOrderUserSearchSerializer,
                          SuperStoreOrderListSerializer, SuperStoreOrderDetailSerializer,
                          LastMileTripReturnOrdersBasicDetailSerializer,
                          ReturnOrderTripProductSerializer, DispatchCenterReturnOrderSerializer,
                          ReturnOrderProductSerializer,
                          LoadVerifyReturnOrderSerializer, UnLoadVerifyReturnOrderSerializer,
                          BackwardTripReturnItemsSerializer,
                          MarkReturnOrderItemVerifiedSerializer, DeliveryReturnOrderSerializer,
                          ShopExecutiveUserSerializer,
                          LastMileTripSerializers, AddressSerializer,) #ProductPriceSerlizer, RetailPastPurchesSerlizer)

from ...common_validators import validate_shipment_dispatch_item, validate_trip_user, \
    get_shipment_by_crate_id, get_shipment_by_shipment_label, validate_shipment_id, validate_trip_shipment, \
    validate_trip, validate_shipment_label, validate_trip_shipment_package, check_user_can_plan_trip, \
    validate_last_mile_trip_user
from wms.services import check_whc_manager_coordinator_supervisor_qc_executive, shipment_search, \
    check_whc_manager_dispatch_executive, check_qc_dispatch_executive, check_dispatch_executive
from pos.payU_payment import *
from fcm.utils import get_device_model
from datetime import datetime

from ...utils import round_half_down, get_fin_year_start_date

Device = get_device_model()

User = get_user_model()

logger = logging.getLogger('django')

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
elastic_logger = logging.getLogger('elastic_log')


def distance(shop_location, order_location):
    """
    Calculate distance between order location and shop location
    """
    lat1, lon1 = shop_location
    lat2, lon2 = order_location
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c
    return d


def get_order_location(shop):
    """
    Get shop location ...
    """
    return float(shop.latitude), float(shop.longitude)


class PickerDashboardViewSet(DataWrapperViewSet):
    '''
    This class handles all operation of ordered product
    '''
    # permission_classes = (AllowAny,)
    model = PickerDashboard
    queryset = PickerDashboard.objects.all()
    serializer_class = PickerDashboardSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = PickerDashboardFilter

    def get_queryset(self):
        shop_id = self.request.query_params.get('shop_id', None)
        picker_dashboard = PickerDashboard.objects.all()

        if shop_id is not None:
            picker_dashboard = picker_dashboard.filter(
                order__seller_shop__id=shop_id, picking_status='picking_pending'
            )
        return picker_dashboard


class OrderedProductViewSet(APIView):
    '''
    This class handles all operation of ordered product
    '''
    model = OrderedProduct
    queryset = OrderedProduct.objects.all()
    serializer_class = OrderedProductSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        shipment_id = self.request.query_params.get('shipment_id', None)
        ordered_product = self.queryset.filter(
            id=shipment_id
        )
        serializer = ReadOrderedProductSerializer(ordered_product[0])
        msg = {'is_success': True, 'message': [''], 'response_data': {'results': [serializer.data]}}
        return Response(msg, status=status.HTTP_200_OK)


class OrderedProductMappingView(DataWrapperViewSet):
    '''
    This class handles all operation of ordered product mapping
    '''
    # permission_classes = (AllowAny,)
    model = ShipmentProducts
    serializer_class = OrderedProductMappingSerializer
    queryset = ShipmentProducts.objects.all()
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = OrderedProductMappingFilter

    def get_serializer_class(self):
        '''
        Returns the serializer according to action of viewset
        '''
        serializer_action_classes = {
            'retrieve': OrderedProductMappingSerializer,
            'list': OrderedProductMappingSerializer,
            'create': OrderedProductMappingSerializer,
            'update': OrderedProductMappingSerializer
        }
        if hasattr(self, 'action'):
            return serializer_action_classes.get(self.action, self.serializer_class)
        return self.serializer_class

    def get_queryset(self):
        ordered_product = self.request.query_params.get('ordered_product', None)
        ordered_product_mapping = ShipmentProducts.objects.all()
        if ordered_product is not None:
            ordered_product_mapping = ordered_product_mapping.filter(
                ordered_product=ordered_product
            )
        return ordered_product_mapping


class ProductsList(generics.ListCreateAPIView):
    permission_classes = (AllowAny,)
    model = Product
    serializer_class = ProductsSearchSerializer

    def get_queryset(self):
        grn = GRNOrderProductMapping.objects.all()
        p_list = []
        for p in grn:
            product = p.product
            id = product.pk
            p_list.append(id)

        products = Product.objects.filter(pk__in=p_list)
        for product in products:
            name = product.product_name
            product_price = ProductPrice.objects.get(product=product)
            mrp = product_price.mrp
            ptr = product_price.price_to_retailer
            status = product_price.status
            product_option = ProductOption.objects.get(product=product)
            pack_size = product_option.package_size.pack_size_name
            weight = product_option.weight.weight_name
            return name, mrp, ptr, status, pack_size, weight


class SearchProducts(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        """
            Search and get catalogue products from ElasticSearch
            Inputs
            ---------
            index ('string')
                values
                    '1' : GramFactory Catalogue
                    '3' : Retailer Shop Catalogue
                    '4' : Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
            shop_id ('string')
                description
                    To get products from index '1' specific to parent shop
            search_type ('string')
                values
                    '1' : Exact Match
                    '2' : Normal Match
            output_type ('string')
                values
                    '1' : Raw
                    '2' : Processed
            ean_code ('string')
                description
                    To get products for search_type '1' based on given ean_code
            keyword ('string')
                description
                    To get products for search_type '2' based on given keyword
        """
        index_type = request.GET.get('index_type', '1')
        # GramFactory Catalogue
        elastic_logger.info("Elastic search starts, index type:: {}".format(index_type))
        if index_type == '1':
            return self.gf_search()
        # Retailer Shop Catalogue
        elif index_type == '3':
            return self.rp_search(request, *args, **kwargs)
        # Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
        elif index_type == '4':
            return self.rp_gf_search(request, *args, **kwargs)
        else:
            return api_response("Please Provide A Valid Index Type")

    @check_pos_shop
    def rp_search(self, request, *args, **kwargs):
        """
            Search Retailer Shop Catalogue
        """
        shop_id = kwargs['shop'].id
        app_type = kwargs['app_type']
        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        elastic_logger.info("Shop id :: {}, App type :: {}, Search type :: {}".format(shop_id, app_type, search_type))
        if search_type == '1':
            results = self.rp_exact_search(shop_id)
        # Normal Search
        elif search_type == '2':
            results = self.rp_normal_search(shop_id, app_type)
        else:
            return api_response("Please Provide A Valid Search Type")
        if results:
            return api_response('Products Found', results, status.HTTP_200_OK, True)
        else:
            return api_response('No Products Found', None, status.HTTP_200_OK)

    def rp_exact_search(self, shop_id):
        """
            Search Retailer Shop Catalogue On Exact Match
        """
        ean_code = self.request.GET.get('ean_code')
        output_type = self.request.GET.get('output_type', '1')
        elastic_logger.info("EAN code :: {}, Output type :: {}".format(ean_code, output_type))

        filter_list = [{"term": {"is_deleted": False}}]

        # if int(self.request.GET.get('include_discounted', '1')) == 0:
        #     filter_list.append({"term": {"is_discounted": False}})

        if self.request.GET.get('include_discounted') and \
                int(self.request.GET.get('include_discounted')) == 1:
            filter_list.append({"term": {"is_discounted": True}})
        elif self.request.GET.get('include_discounted') and \
                int(self.request.GET.get('include_discounted')) == 0:
            filter_list.append({"term": {"is_discounted": False}})

        if self.request.GET.get('product_pack_type') in ['loose', 'packet']:
            filter_list.append({"term": {"product_pack_type": self.request.GET.get('product_pack_type')}})

        elastic_logger.info("Filter list :: {}".format(filter_list))
        must_not = dict()
        if int(self.request.GET.get('ean_not_available', '0')) == 1:
            must_not = {"exists": {"field": "ean"}}
        if ean_code and ean_code != '':
            filter_list.append({"term": {"ean": ean_code}})
        body = dict()
        if filter_list and must_not:
            body["query"] = {"bool": {"filter": filter_list, "must_not": must_not}}
        elif must_not:
            body['query'] = {"bool": {"must_not": must_not}}
        elif filter_list:
            body["query"] = {"bool": {"filter": filter_list}}
        return self.process_rp(output_type, body, shop_id)

    def rp_normal_search(self, shop_id, app_type=None):
        """
            Search Retailer Shop Catalogue On Similar Match
        """
        keyword = self.request.GET.get('keyword')
        output_type = self.request.GET.get('output_type', '1')
        category_ids = self.request.GET.get('category_ids')
        brand = self.request.GET.get('brands')
        sub_category_ids = self.request.GET.get('sub_category_ids')

        max_selling_price = self.request.GET.get('max_selling_price', None)
        min_percentage_discount = self.request.GET.get('min_percentage_discount', None)

        elastic_logger.info(
            "Keyword :: {}, Output type :: {}, Category :: {}, Sub-category :: {}".format(keyword, output_type,
                                                                                          category_ids,
                                                                                          sub_category_ids))
        filter_list = [{"term": {"is_deleted": False}}]
        if min_percentage_discount:
                filter_list.append({"range": {"margin": {"gte": min_percentage_discount}}})
        if max_selling_price:
                filter_list.append({"range": {"ptr": {"lte": max_selling_price}}})

        if int(self.request.GET.get('online_enabled', 0)) == 1:
            filter_list.append({"term": {"online_enabled": True}})
            filter_list.append({"term": {"status": 'active'}})
        if int(self.request.GET.get('offline', 0)) == 1:
            filter_list.append({"term": {"online_enabled": False}})
            filter_list.append({"term": {"status": 'active'}})
        if int(self.request.GET.get('inactive', 0)) == 1:
            filter_list.append({"term": {"status": 'deactivated'}})

        if app_type == '3':
            filter_list.append({"term": {"status": 'active'}})
            filter_list.append({"term": {"online_enabled": True}})
            shop = Shop.objects.filter(id=shop_id).last()
            if shop and shop.online_inventory_enabled:
                filter_list.append({"range": {"stock_qty": {"gt": 0}}})
        body = dict()
        query_string = dict()

        # if int(self.request.GET.get('include_discounted', '1')) == 0:
        #     filter_list.append({"term": {"is_discounted": False}})

        if self.request.GET.get('include_discounted') and \
                int(self.request.GET.get('include_discounted')) == 1:
            filter_list.append({"term": {"is_discounted": True}})
        elif self.request.GET.get('include_discounted') and \
                int(self.request.GET.get('include_discounted')) == 0:
            filter_list.append({"term": {"is_discounted": False}})

        if self.request.GET.get('product_pack_type', 'packet') == 'loose':
            filter_list.append({"term": {"product_pack_type": 'loose'}})

        must_not = dict()
        if int(self.request.GET.get('ean_not_available', '0')) == 1:
            must_not = {"exists": {"field": "ean"}}

        if keyword:
            keyword = keyword.strip()
            if keyword.isnumeric():
                query_string = {"query": keyword + "*", "fields": ["ean"]}
            else:
                # Insert into DB asynchronously
                offset = int(self.request.GET.get('offset', 0))
                if offset == 0:
                    insert_search_term.delay(keyword)
                tokens = keyword.split()
                keyword = ""
                for word in tokens:
                    keyword += "*" + word + "* "
                keyword = keyword.strip()
                query_string = {"query": "*" + keyword + "*", "fields": ["category", "sub_category", "brand", "name"],
                                "minimum_should_match": 2}
        if category_ids:
            category = category_ids.split(',')
            if app_type == '3':
                category = categorymodel.B2cCategory.objects.filter(id__in=category, status=True).last()
                category_filter = str(category)
                if category and category.b2c_cat_parent.exists():
                    filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})
                else:
                    filter_list.append({"match_phrase": {"category": {"query": category_filter}}})
            else:
                category_filter = str(categorymodel.Category.objects.filter(id__in=category, status=True).last())
                filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})

        if sub_category_ids:
            # sub_category = sub_category_ids.split(',')
            # sub_category_filter = str(categorymodel.Category.objects.filter(id__in=sub_category, status=True).last())
            filter_list.append({"term": {"sub_category": sub_category_ids}})

        if brand:
            if brand.isnumeric():
                brand = brand.split(',')
                brand = "{}".format(Brand.objects.filter(id__in=list(brand)).last())
            filter_list.append({"match": {
                "brand": {"query": brand, "operator": "and"}
            }})

        elastic_logger.info("Filter list :: {}".format(filter_list))
        elastic_logger.info("Query string :: {}".format(query_string))

        if filter_list and query_string:
            body['query'] = {"bool": {"must": {"query_string": query_string}, "filter": filter_list}}
        elif query_string:
            body['query'] = {"bool": {"must": {"query_string": query_string}}}
        elif filter_list:
            body['query'] = {"bool": {"filter": filter_list}}
        if must_not:
            if body and body['query']:
                body['query']['bool']['must_not'] = must_not
            else:
                body['query'] = {"bool": {"must_not": must_not}}
        return self.process_rp(output_type, body, shop_id, app_type)

    @check_pos_shop
    def rp_gf_search(self, request, *args, **kwargs):
        """
            Search Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
        """
        shop_id = kwargs['shop'].id
        app_type = kwargs['app_type']
        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        if search_type == '1':
            results = self.rp_gf_exact_search(shop_id, app_type)
        elif search_type == '2':
            results = self.rp_gf_normal_search(shop_id, app_type)
        else:
            return api_response("Provide a valid search type")
        if results:
            return api_response('Products Found', results, status.HTTP_200_OK, True)
        else:
            return api_response('No Products Found', None, status.HTTP_200_OK)

    def rp_gf_exact_search(self, shop_id, app_type):
        """
            Exact Search Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
        """
        response = {}
        # search retailer products first
        rp_results = self.rp_exact_search(shop_id)
        if rp_results:
            response['product_type'] = 'shop_catalogue'
            response['products'] = rp_results
        # search GramFactory products if retailer products not found
        else:
            gf_results = self.gf_exact_search(app_type)
            if gf_results:
                response['product_type'] = 'gf_catalogue'
                response['products'] = gf_results
        return response

    def rp_gf_normal_search(self, shop_id, app_type):
        """
            Keyword Search Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
        """
        response = {}
        # search retailer products first
        rp_results = self.rp_normal_search(shop_id)
        if rp_results:
            response['product_type'] = 'shop_catalogue'
            response['products'] = rp_results
        # search GramFactory products if retailer products not found
        else:
            gf_results = self.gf_pos_normal_search(app_type)
            if gf_results:
                response['product_type'] = 'gf_catalogue'
                response['products'] = gf_results
        return response

    def process_rp(self, output_type, body, shop_id, app_type=None):
        """
        Modify Es results for response based on output_type - Raw OR Processed
        """
        body["from"] = int(self.request.GET.get('offset', 0))
        body["size"] = int(self.request.GET.get('pro_count', 50))
        sort_by = self.request.GET.get('sort_by', 'modified_at')
        sort_order = self.request.GET.get('sort_order', 'desc')
        sort_by = sort_by if sort_by in ['ptr', 'combo_available', "margin"] else 'modified_at'
        sort_order = sort_order if sort_order in ['asc'] else 'desc'
        if sort_by == 'modified_at':
            sort_order = 'desc'
        if sort_by == 'combo_available':
            sort_order = 'desc'
        body["sort"] = {sort_by: sort_order}
        elastic_logger.info("Body :: {}".format(body))
        p_list = []
        cart_check = False
        # Ecom Cart
        if app_type == '3' and self.request.user.id:
            cart = Cart.objects.filter(cart_type='ECOM', seller_shop_id=shop_id, buyer=self.request.user,
                                       cart_status='active').prefetch_related('rt_cart_list').last()
            if cart:
                cart_check = True
                cart_products = cart.rt_cart_list.all()
        # Raw Output
        if output_type == '1':
            # body["_source"] = {"includes": ["id", "name", "ptr", "mrp", "margin", "ean", "status", "product_images",
            #                                 "description", "linked_product_id", "stock_qty", 'offer_price',
            #                                 'offer_start_date', 'offer_end_date']}
            try:
                products_list = es_search(index='rp-{}'.format(shop_id), body=body)
                for p in products_list['hits']['hits']:
                    p_list.append(p["_source"])
                if len(p_list) >= 10 and (
                        self.request.GET.get('max_selling_price') or self.request.GET.get('min_percentage_discount')):
                    param = self.request.query_params
                    pass_parm = '?'
                    for k in param:
                        if k != 'pro_count':
                            pass_parm = pass_parm + f'{k}={param[k]}&'
                    pass_parm = pass_parm + 'pro_count=50'
                    p_list.append({'total_items': len(p_list),
                                   'vew_more': self.request.get_full_path().split('?')[0] + pass_parm})
            except Exception as e:
                error_logger.error(e)
        # Processed Output
        else:
            # body["_source"] = {"includes": ["id", "name", "ptr", "mrp", "margin", "ean", "status", "product_images",
            #                                 "description", "linked_product_id", "stock_qty", 'offer_price',
            #                                 'offer_start_date', 'offer_end_date']}
            try:
                products_list = es_search(index='rp-{}'.format(shop_id), body=body)
                product_ids = []
                for p in products_list['hits']['hits']:
                    product_ids += [p["_source"]['id']]
                    BasicCartOffers.cart = None
                coupons = BasicCartOffers.get_basic_combo_coupons(product_ids, shop_id, 1,
                                                                  ["coupon_code", "coupon_type", "purchased_product"])
                for p in products_list['hits']['hits']:
                    if cart_check:
                        p = self.modify_rp_cart_product_es(cart, cart_products, p)
                    for coupon in coupons:
                        if int(coupon['purchased_product']) == int(p["_source"]['id']):
                            p['_source']['coupons'] = [coupon]
                    p_list.append(p["_source"])
                if len(p_list) >= 10 and (
                        self.request.GET.get('max_selling_price') or self.request.GET.get('min_percentage_discount')):
                    param = self.request.query_params
                    pass_parm = '?'
                    for k in param:
                        if k != 'pro_count':
                            pass_parm = pass_parm + f'{k}={param[k]}&'
                    pass_parm = pass_parm + 'pro_count=50'
                    p_list.append({'total_items': len(p_list),
                                   'vew_more': self.request.get_full_path().split('?')[0] + pass_parm})

            except Exception as e:
                error_logger.error(e)
        elastic_logger.info("Product list :: {}".format(p_list))
        return p_list

    @staticmethod
    def modify_rp_cart_product_es(cart, cart_products, p):
        for c_p in cart_products:
            if c_p.retailer_product_id != p["_source"]["id"]:
                continue
            if cart.offers:
                cart_offers = cart.offers
                combo_offers = list(filter(lambda d: d['type'] in ['combo'], cart_offers))
                for offer in combo_offers:
                    if offer['item_id'] == c_p.retailer_product_id:
                        p["_source"]["free_product_text"] = 'Free - ' + str(
                            offer['free_item_qty_added']) + ' items of ' + str(
                            offer['free_item_name']) + ' | Buy ' + str(offer['item_qty']) + ' Get ' + str(
                            offer['free_item_qty'])
            p["_source"]["cart_qty"] = c_p.qty or 0
        return p

    def gf_search(self):
        """
            Search GramFactory Catalogue
        """
        search_type = self.request.GET.get('search_type', '2')
        # app_type = self.request.GET.get('app_type', '0')
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        if app_type != '2':
            # Normal Search
            if search_type == '2':
                results, is_store_active = self.gf_normal_search(app_type)
                if results:
                    return api_response(['Products Found'], results, status.HTTP_200_OK, True, is_store_active)
                else:
                    return api_response(['No Products Found'], None, status.HTTP_200_OK, False, is_store_active)
            else:
                return api_response(["Please Provide A Valid Search Type"])
        else:
            # Exact Search
            if search_type == '1':
                results = self.gf_exact_search(app_type)
            # Normal Search
            elif search_type == '2':
                results = self.gf_pos_normal_search(app_type)
            else:
                return api_response("Please Provide A Valid Search Type")
            if results:
                return api_response('Products Found', results, status.HTTP_200_OK, True)
            else:
                return api_response('Product not found in GramFactory catalog. Please add new Product.', None,
                                    status.HTTP_200_OK)

    def gf_exact_search(self, app_type):
        """
            Search GramFactory Catalogue Exact Ean
        """
        ean_code = self.request.GET.get('ean_code')
        body = dict()
        if ean_code and ean_code != '':
            filters = [{"term": {"ean": ean_code}}]
            if app_type != '4':
                filters.append({"term": {"product_type": 'grocery'}})
            else:
                filters.append({"term": {"product_type": 'superstore'}})

            body["query"] = {"bool": {"filter": filters}}

        return self.process_gf(app_type, body)

    def gf_normal_search(self, app_type):
        """
            Search GramFactory Catalogue By Name, Brand, Category
            Full catalogue or for a particular parent shop
        """
        shop_id = self.request.GET.get('shop_id') if self.request.GET.get('shop_id') else None
        shop, parent_shop, cart_products, cart, cart_check = None, None, None, None, False
        if app_type == '4':
            shop_id = self.request.META.get('HTTP_SHOP_ID', None)
        # check if shop exists
        try:
            shop = Shop.objects.get(id=shop_id, status=True)
        except ObjectDoesNotExist:
            pass
        # if shop exists, check if it is approved
        else:
            if shop.shop_approved:
                parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
                # if parent shop is sp
                if parent_mapping.parent.shop_type.shop_type == 'sp':
                    info_logger.info("user {} ".format(self.request.user))
                    info_logger.info("shop {} ".format(shop_id))
                    cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop_id=shop_id,
                                               cart_status__in=['active', 'pending']).last()
                    if cart:
                        cart_products, cart_check = cart.rt_cart_list.all(), True
                    parent_shop = parent_mapping.parent
        # store approved and parent = sp
        is_store_active = {'is_store_active': True if parent_shop else False}
        query = self.search_query()
        if app_type == '4':
            body = {'query': query, "aggs": {"margin_stats": {"stats": {"field": "margin"}},
                                             "selling_price_stats": {
                                                 "stats": {"field": "super_store_product_selling_price"}},
                                             "brand": {"terms": {"field": "brand.keyword"},
                                                       },
                                             }}
        else:
            body = {'query': query, }
        return self.process_gf(app_type, body, shop, parent_shop, cart_check, cart, cart_products), is_store_active

    def gf_pos_normal_search(self, app_type):
        """
            Search GramFactory Catalogue By Name
        """
        body = {'query': self.search_query(), }
        return self.process_gf(app_type, body)

    def process_gf(self, app_type, body, shop=None, parent_shop=None, cart_check=False, cart=None, cart_products=None):
        """
            Modify Es results for response based on shop
        """
        body["from"] = int(self.request.GET.get('offset', 0))
        body["size"] = int(self.request.GET.get('pro_count', 100))
        sort_by = self.request.GET.get('sort_by', 'modified_at')
        sort_order = self.request.GET.get('sort_order', 'asc')
        sort_by = sort_by if sort_by in ['ptr', "margin"] else 'ptr'
        sort_order = sort_order if sort_order in ['asc', 'desc'] else 'asc'
        if sort_by == 'ptr' and app_type == '4':
            sort_by = 'super_store_product_selling_price'
        elif sort_by == 'ptr' and app_type == '1':
            sort_by = 'ptr'
        if sort_by == 'margin':
            sort_order = 'desc'
        body["sort"] = {sort_by: sort_order}
        p_list = []
        if app_type == '1':
            es_index = 'all_products'
        # elif app_type == '4':
        #     es_index = GlobalConfig.objects.get(key='current_wh_active').value
        else:
            es_index = 'all_b2c_product'

        # No Shop Id OR Store Inactive
        if not parent_shop:
            body["_source"] = {"includes": ["id", "name", "product_images", "pack_size", "brand_case_size",
                                            "weight_unit", "weight_value", "visible", "mrp", "ean",
                                            "super_store_product_selling_price"]}
            products_list = es_search(index=es_index, body=body)
            for p in products_list['hits']['hits']:
                p["_source"]["description"] = p["_source"]["name"]
                p["_source"]["super_store_product_selling_price"] = p["_source"]["super_store_product_selling_price"]
                p_list.append(p["_source"])
            return p_list
        # Active Store
        products_list = es_search(index=parent_shop.id, body=body)
        for p in products_list['hits']['hits']:
            try:
                p = self.modify_gf_product_es_price(p, shop, parent_shop)
            except:
                continue
            product = Product.objects.filter(id=p["_source"]["id"]).last()
            if not product:
                logger.info("No product found in DB matching for ES product with id: {}".format(p["_source"]["id"]))
                continue
            p["_source"]["coupon"] = self.get_coupons_gf_product(product)
            if cart_check:
                p = self.modify_gf_cart_product_es(cart, cart_products, p)
            p_list.append(p["_source"])
        if len(p_list) != 0 and not (self.request.GET.get('max_selling_price') or self.request.GET.get('min_percentage_discount')):
            if products_list.get('aggregations'):
                p_list.append(products_list['aggregations'])
        if len(p_list) >= 10 and  (
                self.request.GET.get('max_selling_price') or self.request.GET.get('min_percentage_discount')):
            param =  self.request.query_params
            pass_parm = '?'
            for k in param:
                if k != 'pro_count':
                    pass_parm = pass_parm + f'{k}={param[k]}&'
            pass_parm = pass_parm + 'pro_count=50'
            p_list.append({'total_items': len(p_list), 'vew_more': self.request.get_full_path().split('?')[0] + pass_parm})

        return p_list

    def search_query(self):
        """
            Search query for gf normal search
        """
        product_ids = self.request.GET.get('product_ids')
        brand = self.request.GET.get('brands')
        category = self.request.GET.get('categories')
        keyword = self.request.GET.get('keyword', None)
        is_discounted = self.request.GET.get('is_discounted', None)
        margin_min = self.request.GET.get('margin_min', None)
        margin_max = self.request.GET.get('margin_max', None)
        selling_price_min = self.request.GET.get('selling_price_min', None)
        selling_price_max = self.request.GET.get('selling_price_max', None)
        max_selling_price = self.request.GET.get('max_selling_price', None)
        min_percentage_discount = self.request.GET.get('min_percentage_discount', None)
        filter_list = []
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        if app_type == '4':
            filter_list = [
                {"term": {"status": True}},
                {"term": {"visible": True}},
                {"term": {"product_type": 'superstore'}}
            ]
            if margin_min and margin_max:
                filter_list.append({"range": {"margin": {"gte": margin_min, "lte":margin_max}}})
            if min_percentage_discount:
                filter_list.append({"range": {"margin": {"gte": min_percentage_discount}}})

            if max_selling_price:
                filter_list.append({"range": {"super_store_product_selling_price": {"lte": max_selling_price}}})

            if selling_price_min and selling_price_max:
                filter_list.append({"range": {
                    "super_store_product_selling_price": {"gte": selling_price_min, "lte": selling_price_max}}})
        else:
            if app_type != '2':
                filter_list = [
                    {"term": {"status": True}},
                    {"term": {"visible": True}},
                    {"range": {"available": {"gt": 0}}}
                ]
            filter_list.append({"term": {"product_type": 'grocery'}})

        if is_discounted:
            filter_list.append({"term": {"is_discounted": is_discounted}}, )
        if min_percentage_discount:
            if not is_discounted:
                filter_list.append({"term": {"is_discounted": False}}, )
            filter_list.append({"range": {"margin": {"gte": min_percentage_discount}}})
        if product_ids:
            product_ids = product_ids.split(',')
            filter_list.append({"ids": {"type": "product", "values": product_ids}})
            query = {"bool": {"filter": filter_list}}
            return query
        query = {"bool": {"filter": filter_list}}
        if not (category or brand or keyword):
            return query
        if brand:
            if brand.isnumeric():
                brand = brand.split(',')
                brand = "{}".format(Brand.objects.filter(id__in=list(brand)).last())
                filter_list.append({"match": {
                    "brand": {"query": brand, "operator": "and"}
                }})
            else:
                filter_list.append({"terms": {"brand.keyword": json.loads(brand)}})
            # filter_list.append({"term": {"brand": brand}})
        elif keyword:
            q = {"multi_match": {"query": keyword, "fields": ["name^5", "category", "brand"], "type": "cross_fields"}}
            query["bool"]["must"] = [q]
        if category:
            category = category.split(',')
            category_filter = str(categorymodel.Category.objects.filter(id__in=category, status=True).last())
            filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})
        return query

    @staticmethod
    def get_coupons_gf_product(product):
        product_coupons = product.getProductCoupons()
        catalogue_coupons = Coupon.objects.filter(coupon_code__in=product_coupons, coupon_type='catalog')
        brand_coupons = Coupon.objects.filter(coupon_code__in=product_coupons, coupon_type='brand').order_by(
            'rule__cart_qualifying_min_sku_value')
        coupons_queryset = catalogue_coupons | brand_coupons
        coupons = CouponSerializer(coupons_queryset, many=True).data
        if coupons_queryset:
            for coupon in coupons_queryset:
                for product_coupon in coupon.rule.product_ruleset.filter(purchased_product=product):
                    if product_coupon.max_qty_per_use > 0:
                        max_qty = product_coupon.max_qty_per_use
                        for i in coupons:
                            if i['coupon_type'] == 'catalog':
                                i['max_qty'] = max_qty
        return coupons

    @staticmethod
    def modify_gf_cart_product_es(cart, cart_products, p):
        for c_p in cart_products:
            if c_p.cart_product_id != p["_source"]["id"]:
                continue
            if cart.offers:
                cart_offers = cart.offers
                product_offers = list(filter(lambda d: d['sub_type'] in ['discount_on_product'], cart_offers))
                for i in product_offers:
                    if i['item_sku'] == c_p.cart_product.product_sku:
                        p["_source"]["discounted_product_subtotal"] = Decimal(i['discounted_product_subtotal'])
                brand_offers = list(filter(lambda d: d['sub_type'] in ['discount_on_brand'], cart_offers))
                for j in p["_source"]["coupon"]:
                    for i in (brand_offers + product_offers):
                        if j['coupon_code'] == i['coupon_code']:
                            j['is_applied'] = True
            p["_source"]["user_selected_qty"] = c_p.qty or 0
            p["_source"]["ptr"] = c_p.applicable_slab_price
            p["_source"]["no_of_pieces"] = int(c_p.qty) * int(c_p.cart_product.product_inner_case_size)
            p["_source"]["sub_total"] = c_p.qty * Decimal(c_p.item_effective_prices)
        return p

    @staticmethod
    def modify_gf_product_es_price(p, shop, parent_shop):
        price_details = p["_source"]["price_details"]
        if str(shop.id) in price_details['store'].keys():
            p["_source"]["price_details"] = price_details['store'][str(shop.id)]
        elif str(shop.get_shop_pin_code) in price_details['pincode'].keys():
            p["_source"]["price_details"] = price_details['pincode'][str(shop.get_shop_pin_code)]
        elif str(shop.get_shop_city.id) in price_details['city'].keys():
            p["_source"]["price_details"] = price_details['city'][str(shop.get_shop_city.id)]
        elif str(parent_shop.id) in price_details['store'].keys():
            p["_source"]["price_details"] = price_details['store'][str(parent_shop.id)]

        c = 0
        for price_detail in p["_source"]["price_details"]:
            p["_source"]["price_details"][c]["ptr"] = round(p["_source"]["price_details"][c]["ptr"], 2)
            p["_source"]["price_details"][c]["margin"] = round(p["_source"]["price_details"][c]["margin"], 2)
            c += 1
        return p


# class GramGRNProductsList(APIView):
#     permission_classes = (AllowAny,)
#     serializer_class = GramGRNProductsSearchSerializer
#
#     def search_query(self, request):
#         filter_list = [
#             {"term": {"status": True}},
#             {"term": {"visible": True}},
#             {"range": {"available": {"gt": 0}}}
#         ]
#         if self.product_ids:
#             filter_list.append({"ids": {"type": "product", "values": self.product_ids}})
#             query = {"bool": {"filter": filter_list}}
#             return query
#         query = {"bool": {"filter": filter_list}}
#         if not (self.category or self.brand or self.keyword):
#             return query
#         if self.brand:
#             brand_name = "{} -> {}".format(Brand.objects.filter(id__in=list(self.brand)).last(), self.keyword)
#             filter_list.append({"match": {
#                 "brand": {"query": brand_name, "fuzziness": "AUTO", "operator": "and"}
#             }})
#
#         elif self.keyword:
#             q = {
#                     "multi_match": {
#                         "query":     self.keyword,
#                         "fields":    ["name^5", "category", "brand"],
#                         "type":      "cross_fields"
#                     }
#                 }
#             query["bool"]["must"] = [q]
#         if self.category:
#             category_filter = str(categorymodel.Category.objects.filter(id__in=self.category, status=True).last())
#             filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})
#
#         return query
#
#     def post(self, request, format=None):
#         self.product_ids = request.data.get('product_ids')
#         self.brand = request.data.get('brands')
#         self.category = request.data.get('categories')
#         self.keyword = request.data.get('product_name', None)
#         shop_id = request.data.get('shop_id')
#         offset = int(request.data.get('offset', 0))
#         page_size = int(request.data.get('pro_count', 50))
#         grn_dict = None
#         cart_check = False
#         is_store_active = True
#         sort_preference = request.GET.get('sort_by_price')
#
#         '''1st Step
#             Check If Shop Is exists then 2nd pt else 3rd Pt
#         '''
#         query = self.search_query(request)
#
#         try:
#             shop = Shop.objects.get(id=shop_id, status=True)
#         except ObjectDoesNotExist:
#             '''3rd Step
#                 If no shop found then
#             '''
#             message = "Shop not active or does not exists"
#             is_store_active = False
#         else:
#             '''2nd Step
#                 Check if shop found then check whether it is sp 4th Step or retailer 5th Step
#             '''
#             if not shop.shop_approved:
#                 message = "Shop Mapping Not Found"
#                 is_store_active = False
#             # try:
#             #     parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
#             # except ObjectDoesNotExist:
#             else:
#                 parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
#                 if parent_mapping.parent.shop_type.shop_type == 'sp':
#                     '''4th Step
#                         SP mapped data shown
#                     '''
#                     body = {"from": offset, "size": page_size, "query": query}
#                     products_list = es_search(index=parent_mapping.parent.id, body=body)
#                     info_logger.info("user {} ".format(self.request.user))
#                     info_logger.info("shop {} ".format(shop_id))
#
#                     cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop_id=shop_id,
#                                                cart_status__in=['active', 'pending']).last()
#                     if cart:
#                         cart_products = cart.rt_cart_list.all()
#                         cart_check = True
#                 else:
#                     is_store_active = False
#         p_list = []
#         if not is_store_active:
#             body = {
#                 "from": offset,
#                 "size": page_size,
#                 "query": query,
#                 "_source": {"includes": ["name", "product_images", "pack_size", "weight_unit", "weight_value", "visible"]}
#             }
#             products_list = es_search(index="all_products", body=body)
#
#         for p in products_list['hits']['hits']:
#             if is_store_active:
#                 if not Product.objects.filter(id=p["_source"]["id"]).exists():
#                     logger.info("No product found in DB matching for ES product with id: {}".format(p["_source"]["id"]))
#                     continue
#                 product = Product.objects.get(id=p["_source"]["id"])
#                 product_coupons = product.getProductCoupons()
#                 coupons_queryset1 = Coupon.objects.filter(coupon_code__in=product_coupons, coupon_type='catalog')
#                 coupons_queryset2 = Coupon.objects.filter(coupon_code__in=product_coupons,
#                                                           coupon_type='brand').order_by(
#                     'rule__cart_qualifying_min_sku_value')
#                 coupons_queryset = coupons_queryset1 | coupons_queryset2
#                 coupons = CouponSerializer(coupons_queryset, many=True).data
#                 p["_source"]["coupon"] = coupons
#                 # check in case of multiple coupons
#                 if coupons_queryset:
#                     for coupon in coupons_queryset:
#                         for product_coupon in coupon.rule.product_ruleset.filter(purchased_product=product):
#                             if product_coupon.max_qty_per_use > 0:
#                                 max_qty = product_coupon.max_qty_per_use
#                                 for i in coupons:
#                                     if i['coupon_type'] == 'catalog':
#                                         i['max_qty'] = max_qty
#                 check_price_mrp = product.product_mrp
#             if cart_check == True:
#                 for c_p in cart_products:
#                     if c_p.cart_product_id == p["_source"]["id"]:
#                         keyValList2 = ['discount_on_product']
#                         keyValList3 = ['discount_on_brand']
#                         if cart.offers:
#                             exampleSet2 = cart.offers
#                             array2 = list(filter(lambda d: d['sub_type'] in keyValList2, exampleSet2))
#                             for i in array2:
#                                 if i['item_sku'] == c_p.cart_product.product_sku:
#                                     discounted_product_subtotal = i['discounted_product_subtotal']
#                                     p["_source"]["discounted_product_subtotal"] = discounted_product_subtotal
#                             array3 = list(filter(lambda d: d['sub_type'] in keyValList3, exampleSet2))
#                             for j in coupons:
#                                 for i in (array3 + array2):
#                                     if j['coupon_code'] == i['coupon_code']:
#                                         j['is_applied'] = True
#                         user_selected_qty = c_p.qty or 0
#                         no_of_pieces = int(c_p.qty) * int(c_p.cart_product.product_inner_case_size)
#                         p["_source"]["user_selected_qty"] = user_selected_qty
#                         p["_source"]["ptr"] = c_p.applicable_slab_price
#                         p["_source"]["no_of_pieces"] = no_of_pieces
#                         p["_source"]["sub_total"] = c_p.qty * c_p.item_effective_prices
#             counter=0
#             try:
#                 for price_detail in p["_source"]["price_details"]:
#                     p["_source"]["price_details"][counter]["ptr"]=round(p["_source"]["price_details"][counter]["ptr"],2)
#                     p["_source"]["price_details"][counter]["margin"] = round(p["_source"]["price_details"][counter]["margin"], 2)
#                     counter+=1
#                 p_list.append(p["_source"])
#             except:
#                 pass
#
#         msg = {'is_store_active': is_store_active,
#                'is_success': True,
#                'message': ['Products found'],
#                'response_data': p_list}
#         if not p_list:
#             msg = {'is_store_active': is_store_active,
#                    'is_success': False,
#                    'message': ['Sorry! No product found'],
#                    'response_data': None}
#         return Response(msg,
#                         status=200)


class AutoSuggest(APIView):
    permission_classes = (AllowAny,)

    def search_query(self, keyword):
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        filter_list = [{"term": {"status": True}}, {"term": {"visible": True}}]
        if app_type == '4':
            filter_list.append({"term": {"product_type": "superstore"}})
        else:
            filter_list.append({"term": {"product_type": "grocery"}})
            filter_list.append({"range": {"available": {"gt": 0}}})
        query = {"bool": {"filter": filter_list}}
        q = {
            "match": {
                "name": {"query": keyword, "fuzziness": "AUTO", "operator": "or", "minimum_should_match": "2"}
            }
        }
        filter_list.append(q)
        return query

    def get(self, request, *args, **kwargs):
        search_keyword = request.GET.get('keyword')
        shop_id = request.GET.get('shop_id')
        offset = 0
        page_size = 5
        query = self.search_query(search_keyword)
        body = {
            "from": offset,
            "size": page_size,
            "query": query, "_source": {"includes": ["name", "product_images"]}
        }
        index = "all_products"
        if shop_id:
            if Shop.objects.filter(id=shop_id).exists():
                parent_mapping = ParentRetailerMapping.objects.filter(retailer=shop_id, status=True).last()
                if parent_mapping and parent_mapping.parent.shop_type.shop_type == 'sp':
                    index = parent_mapping.parent.id
        products_list = es_search(index=index, body=body)
        p_list = []
        for p in products_list['hits']['hits']:
            p_list.append(p["_source"])
        return Response({"message": ['suggested products'], "response_data": p_list, "is_success": True})


class ProductDetail(APIView):

    def get(self, *args, **kwargs):
        pk = self.kwargs.get('pk')
        msg = {'is_success': False, 'message': [''], 'response_data': None}
        try:
            product = Product.objects.get(id=pk)
        except ObjectDoesNotExist:
            msg['message'] = ["Invalid Product name or ID"]
            return Response(msg, status=status.HTTP_200_OK)

        product_detail = Product.objects.get(id=pk)
        product_detail_serializer = ProductsSearchSerializer(product_detail)
        return Response({"message": [''], "response_data": product_detail_serializer.data, "is_success": True})


class CartCentral(GenericAPIView):
    """
        Get Cart
        Add To Cart
        Search Cart
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    def get(self, request, *args, **kwargs):
        """
            Get Cart
            Inputs:
                shop_id
                app_type (retail-1 or basic-2)
        """
        app_type = request.META.get('HTTP_APP_TYPE', '1')
        # app_type = self.request.GET.get('cart_type', '1')
        if app_type == '1':
            return self.get_retail_cart()
        elif app_type == '2':
            if self.request.GET.get('cart_id'):
                return self.get_basic_cart(request, *args, **kwargs)
            else:
                return self.get_basic_cart_list(request, *args, **kwargs)
        elif app_type == '3':
            return self.get_ecom_cart(request, *args, **kwargs)
        elif app_type == '4':
            return self.get_supermart_cart(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid app_type')

    def post(self, request, *args, **kwargs):
        """
            Add To Cart
            Inputs
                app_type (retail-1 or basic-2)
                cart_product (Product for 'retail', RetailerProduct for 'basic'
                shop_id (Buyer shop id for 'retail', Shop id for selling shop in case of 'basic')
                qty (Quantity of product to be added)
        """
        app_type = request.META.get('HTTP_APP_TYPE', '1')
        # app_type = self.request.data.get('cart_type', '1')
        if app_type == '1':
            return self.retail_add_to_cart()
        elif app_type == '2':
            return self.basic_add_to_cart(request, *args, **kwargs)
        elif app_type == '3':
            return self.ecom_add_to_cart(request, *args, **kwargs)
        elif app_type == '4':
            return self.superstore_add_to_cart(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid app_type')

    def put(self, request, *args, **kwargs):
        """
            Add/Update Item To Basic Cart
            Inputs
                app_type (2)
                product_id
                shop_id
                cart_id
                qty
        """
        app_type = request.META.get('HTTP_APP_TYPE', None)
        # app_type = self.request.data.get('cart_type')
        if app_type == '2':
            return self.basic_add_to_cart(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid app_type')

    @check_pos_shop
    @pos_check_user_permission
    def delete(self, request, *args, **kwargs):
        """
            Update Cart Status To deleted For Basic Cart
        """
        # Check If Cart Exists
        try:
            cart = Cart.objects.get(id=kwargs['pk'], cart_status__in=['active', 'pending'],
                                    seller_shop=kwargs['shop'], cart_type='BASIC')
        except:
            return api_response("Active Cart Not Found")
        Cart.objects.filter(id=cart.id).update(cart_status=Cart.DELETED)
        return api_response('Cancelled Successfully!', None, status.HTTP_200_OK, True)

    def get_retail_cart(self):
        """
            Get Cart
            For cart_type "retail"
        """
        # basic validations for inputs
        initial_validation = self.get_retail_validate()
        if 'error' in initial_validation:
            return api_response([initial_validation['error']], None, status.HTTP_200_OK)
        buyer_shop = initial_validation['buyer_shop']
        seller_shop = initial_validation['seller_shop']
        shop_type = initial_validation['shop_type']
        user = self.request.user

        # If Seller Shop is sp Type
        if shop_type == 'sp':
            # Check if cart exists
            if Cart.objects.filter(last_modified_by=user, buyer_shop=buyer_shop,
                                   cart_status__in=['active', 'pending']).exists():
                cart = Cart.objects.filter(last_modified_by=user, buyer_shop=buyer_shop,
                                           cart_status__in=['active', 'pending']).last()
                # Update offers
                Cart.objects.filter(id=cart.id).update(offers=cart.offers_applied())
                # Filter/Delete cart products that are blocked for audit etc
                cart_products = self.filter_cart_products(cart, seller_shop)
                # Update number of pieces for all products
                self.update_cart_qty_cp(cart, cart_products)
                # Check if products are present in cart
                if cart.rt_cart_list.count() <= 0:
                    return api_response(['Sorry no product added to this cart yet'], None, status.HTTP_200_OK)
                # Delete products without MRP
                self.delete_products_without_mrp(cart)
                # Process response - Product images, MRP check, Serialize - Search and Pagination
                return api_response(['Cart'], self.get_serialize_process_sp(cart, seller_shop, buyer_shop),
                                    status.HTTP_200_OK, True)
            else:
                return api_response(['Sorry no product added to this cart yet'], None, status.HTTP_200_OK)
        # If Seller Shop is gf type
        elif shop_type == 'gf':
            # Check if cart exists
            if GramMappedCart.objects.filter(last_modified_by=user, cart_status__in=['active', 'pending']).exists():
                cart = GramMappedCart.objects.filter(last_modified_by=user,
                                                     cart_status__in=['active', 'pending']).last()
                # Check if products are present in cart
                if cart.rt_cart_list.count() <= 0:
                    return api_response(['Sorry no product added to this cart yet'], None, status.HTTP_200_OK)
                else:
                    # Process response - Serialize
                    return api_response(['Cart'], self.get_serialize_process_gf(cart, seller_shop), status.HTTP_200_OK,
                                        True)
            else:
                return api_response(['Sorry no product added to this cart yet'], None, status.HTTP_200_OK)
        else:
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None,
                                status.HTTP_200_OK)

    @check_pos_shop
    def get_basic_cart(self, request, *args, **kwargs):
        """
            Get Cart
            For cart_type "basic"
        """
        try:
            cart = Cart.objects.get(seller_shop=kwargs['shop'], id=self.request.GET.get('cart_id'),
                                    cart_type='BASIC')
        except ObjectDoesNotExist:
            return api_response("Cart Not Found!")
        # Refresh cart prices
        PosCartCls.refresh_prices(cart.rt_cart_list.all())
        # Refresh - add/remove/update combo, get nearest cart offer over cart value
        next_offer = BasicCartOffers.refresh_offers_cart(cart)
        return api_response('Cart', self.get_serialize_process_basic(cart, next_offer), status.HTTP_200_OK, True)

    @staticmethod
    def get_offer_applied_count_free_type(buyer, coupon_id, expiry_date, created_at):
        carts = Cart.objects.filter(buyer=buyer, created_at__gte=created_at, created_at__lte=expiry_date).filter(
            ~Q(cart_status='active'))
        count = 0
        for cart in carts:
            offers = cart.offers
            if offers:
                for i in offers:
                    if int(coupon_id) == i.get('coupon_id'):
                        count += 1
        return count

    @check_ecom_user_shop
    def get_ecom_cart(self, request, *args, **kwargs):
        """
            Get Cart
            For cart_type "ecom"
        """
        with transaction.atomic():
            try:
                cart = Cart.objects.filter(cart_type='ECOM', buyer=self.request.user, cart_status='active',
                                           seller_shop=kwargs['shop']).last()
                # Empty cart if shop/location changed
                if cart:
                    if cart.seller_shop.id != kwargs['shop'].id:
                        cart.seller_shop = kwargs['shop']
                        cart.save()
                        CartProductMapping.objects.filter(cart=cart).delete()
                        return api_response("No items added in cart yet", {"rt_cart_list": []}, status.HTTP_200_OK,
                                            False)
                else:
                    return api_response("No items added in cart yet", {"rt_cart_list": []}, status.HTTP_200_OK, False)
            except ObjectDoesNotExist:
                return api_response("No items added in cart yet", {"rt_cart_list": []}, status.HTTP_200_OK, False)

            if self.request.GET.get("remove_unavailable") and cart.seller_shop.online_inventory_enabled:
                PosCartCls.out_of_stock_items(cart.rt_cart_list.all(), self.request.GET.get("remove_unavailable"))
            # Refresh cart prices
            PosCartCls.refresh_prices(cart.rt_cart_list.all())
            # Refresh - add/remove/update combo, get nearest cart offer over cart value
            next_offer = BasicCartOffers.refresh_offers_cart(cart)
            # Get Offers Applicable, Verify applied offers, Apply highest discount on cart if auto apply
            offers = BasicCartOffers.refresh_offers_checkout(cart, False, None)
            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'], app_type="ECOM",
                                             use_all=self.request.GET.get('use_rewards', 1))
            offers_list = cart.offers
            for offer in offers_list:
                coupon_id = offer.get('coupon_id')
                if coupon_id:
                    coupon = Coupon.objects.filter(id=coupon_id).last()
                    limit_of_usages_per_customer = coupon.limit_of_usages_per_customer
                    count = self.get_offer_applied_count_free_type(cart.buyer, coupon_id, coupon.expiry_date,
                                                                   coupon.start_date)
                    if limit_of_usages_per_customer and count >= limit_of_usages_per_customer:
                        offers_list.remove(offer)
            cart.offers = offers_list
            cart.save()
            cart_data = self.get_serialize_process_basic(cart, next_offer)
            checkout = CartCheckout()
            checkout_data = checkout.serialize(cart, offers)
            checkout_data.pop('amount_payable', None)
            cart_data.update(checkout_data)
            address = AddressCheckoutSerializer(cart.buyer.ecom_user_address.filter(default=True).last()).data
            cart_data.update({'default_address': address})
            return api_response('Cart', cart_data, status.HTTP_200_OK, True)

    @check_ecom_user_shop
    def get_supermart_cart(self, request, *args, **kwargs):
        """
            Get cart api
            for cart type : superstore
        """
        with transaction.atomic():
            try:
                cart = Cart.objects.get(cart_type='SUPERSTORE', buyer=self.request.user, cart_status='active',
                                        seller_shop=kwargs['shop'])
            except Cart.DoesNotExist:
                return api_response("No items added in cart yet", {"cart_product_list": []}, status.HTTP_200_OK, False)
            except Cart.MultipleObjectsReturned:
                cart = Cart.objects.filter(cart_type='SUPERSTORE', buyer=self.request.user, cart_status='active',
                                           seller_shop=kwargs['shop']).last()
            shop = kwargs['shop']
            parent_shop = shop.get_shop_parent
            if not parent_shop:
                return api_response("Shop is not mapped with parent shop", {"cart_product_list": []},
                                    status.HTTP_200_OK, False)

            # Refresh cart prices
            PosCartCls.refresh_prices(cart.rt_cart_list.all(), parent_shop.id)
            # Refresh - add/remove/update combo, get nearest cart offer over cart value
            next_offer = BasicCartOffers.refresh_offers_cart(cart)
            # Get Offers Applicable, Verify applied offers, Apply highest discount on cart if auto apply
            offers = BasicCartOffers.refresh_offers_checkout(cart, False, None)
            # Refresh redeem reward

            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, 0, kwargs['shop'], app_type="SUPERSTORE",
                                             use_all=self.request.GET.get('use_rewards', 1))
            offers_list = cart.offers
            for offer in offers_list:
                coupon_id = offer.get('coupon_id')
                if coupon_id:
                    coupon = Coupon.objects.filter(id=coupon_id).last()
                    limit_of_usages_per_customer = coupon.limit_of_usages_per_customer
                    count = self.get_offer_applied_count_free_type(cart.buyer, coupon_id, coupon.expiry_date,
                                                                   coupon.start_date)
                    if limit_of_usages_per_customer and count >= limit_of_usages_per_customer:
                        offers_list.remove(offer)
            cart.offers = offers_list
            cart.save()
            checkout = CartCheckout()
            cart_data = checkout.serialize(cart, offers)
            cart_data.pop('amount_payable', None)
            cart_data.update(SuperStoreCartSerializer(cart, context={'parent_shop_id': parent_shop.id}).data)
            address = AddressCheckoutSerializer(cart.buyer.ecom_user_address.filter(default=True).last()).data
            cart_data.update({'default_address': address})
            return api_response('Cart', cart_data, status.HTTP_200_OK, True)

    @check_pos_shop
    def get_basic_cart_list(self, request, *args, **kwargs):
        """
            List active carts for seller shop
        """
        search_text = self.request.GET.get('search_text')
        carts = Cart.objects.select_related('buyer').prefetch_related('rt_cart_list').filter(seller_shop=kwargs['shop'],
                                                                                             cart_status__in=['active',
                                                                                                              'pending'],
                                                                                             cart_type='BASIC').order_by(
            '-modified_at')
        if search_text:
            carts = carts.filter(Q(cart_no__icontains=search_text) |
                                 Q(buyer__first_name__icontains=search_text) |
                                 Q(buyer__phone_number__icontains=search_text))

        objects = self.pagination_class().paginate_queryset(carts, self.request)
        if objects:
            open_orders = BasicCartListSerializer(objects, many=True)
            return api_response("Open Orders", open_orders.data, status.HTTP_200_OK, True)
        else:
            return api_response("No Open Orders Found", None, status.HTTP_200_OK, True)

    def get_retail_validate(self):
        """
            Get Cart
            Input validation for cart type 'retail'
        """
        shop_id = self.request.GET.get('shop_id')
        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        return {'buyer_shop': parent_mapping.retailer, 'seller_shop': parent_mapping.parent,
                'shop_type': parent_mapping.parent.shop_type.shop_type}

    @staticmethod
    def filter_cart_products(cart, seller_shop):
        """
            Filter/Delete cart products that are blocked for audit etc
        """
        cart_products = CartProductMapping.objects.select_related('cart_product').filter(cart=cart)
        cart_product_to_be_deleted = []
        # check and delete if product blocked for audit
        for p in cart_products:
            is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product, seller_shop)
            if is_blocked_for_audit:
                cart_product_to_be_deleted.append(p.id)
        if len(cart_product_to_be_deleted) > 0:
            CartProductMapping.objects.filter(id__in=cart_product_to_be_deleted).delete()
            cart_products = CartProductMapping.objects.select_related('cart_product').filter(cart=cart)
        return cart_products

    @staticmethod
    def update_cart_qty_cp(cart, cart_products):
        """
            Update number of pieces for all products in cart
        """
        for cart_product in cart_products:
            item_qty = CartProductMapping.objects.filter(cart=cart,
                                                         cart_product=cart_product.cart_product).last().qty
            updated_no_of_pieces = (item_qty * int(cart_product.cart_product.product_inner_case_size))
            try:
                if cart_product.cart_product.product_type == 1:
                    cp_product = cart_product.cart_product.product_ref
                else:
                    cp_product = cart_product.cart_product
                cost_price = ProductGRNCostPriceMapping.objects.get(product=cp_product)
                cost_price = cost_price.cost_price
            except ProductGRNCostPriceMapping.DoesNotExist:
                cost_price = None
            CartProductMapping.objects.filter(cart=cart, cart_product=cart_product.cart_product).update(
                no_of_pieces=updated_no_of_pieces, 
                cost_price=cost_price)

    @staticmethod
    def delivery_message(shop_type):
        """
            Get Cart
            Delivery message
        """
        date_time_now = datetime.now()
        day = date_time_now.strftime("%A")
        time = date_time_now.strftime("%H")

        if int(time) < 17 and not (day == 'Saturday'):
            return str('Order now and get by {}.Min Order amt Rs {}.'.format(
                (date_time_now + timedelta(days=1)).strftime('%A'), str(shop_type.shop_min_amount)))
        elif (day == 'Friday'):
            return str('Order now and get by {}.Min Order amt Rs {}.'.format(
                (date_time_now + timedelta(days=3)).strftime('%A'), str(shop_type.shop_min_amount)))
        else:
            return str('Order now and get by {}.Min Order amt Rs {}.'.format(
                (date_time_now + timedelta(days=2)).strftime('%A'), str(shop_type.shop_min_amount)))

    @staticmethod
    def delete_products_without_mrp(cart):
        """
            Delete products without MRP in cart
        """
        for i in Cart.objects.get(id=cart.id).rt_cart_list.all():
            if not i.cart_product.getMRP(cart.seller_shop.id, cart.buyer_shop.id):
                CartProductMapping.objects.filter(cart__id=cart.id, cart_product__id=i.cart_product.id).delete()

    def get_serialize_process_sp(self, cart, seller_shop, buyer_shop):
        """
           Get Cart
           Cart type retail - sp
           Serialize and Modify Cart - Parent Product Image Check, MRP Check
        """
        serializer = CartSerializer(Cart.objects.get(id=cart.id),
                                    context={'parent_mapping_id': seller_shop.id, 'buyer_shop_id': buyer_shop.id,
                                             'search_text': self.request.GET.get('search_text', ''),
                                             'delivery_message': self.delivery_message(seller_shop.shop_type),
                                             'request': self.request})
        for i in serializer.data['rt_cart_list']:
            # check if product has to use it's parent product image
            if not i['cart_product']['product_pro_image']:
                product = Product.objects.get(id=i['cart_product']['id'])
                if product.use_parent_image:
                    for im in product.parent_product.parent_product_pro_image.all():
                        parent_image_serializer = ParentProductImageSerializer(im)
                        i['cart_product']['product_pro_image'].append(parent_image_serializer.data)
            # remove products without mrp
            if not i['cart_product']['price_details']['mrp']:
                i['qty'] = 0
                CartProductMapping.objects.filter(cart__id=i['cart']['id'],
                                                  cart_product__id=i['cart_product']['id']).delete()
        return serializer.data

    def get_serialize_process_gf(self, cart, seller_shop=''):
        """
           Get Cart
           Cart type retail - gf
           Serialize
        """
        serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id),
                                              context={'parent_mapping_id': seller_shop.id,
                                                       'delivery_message': self.delivery_message(
                                                           seller_shop.shop_type)})
        return serializer.data

    def get_serialize_process_basic(self, cart, next_offer):
        """
           Get Cart
           Cart type basic
           Serialize
        """
        cart = Cart.objects.prefetch_related('rt_cart_list').get(id=cart.id)
        data = BasicCartSerializer(cart, context={'search_text': self.request.GET.get('search_text', ''),
                                                  'request': self.request}).data
        data['next_offer'] = next_offer
        return data

    def retail_add_to_cart(self):
        """
            Add To Cart
            For cart type 'retail'
        """
        # basic validations for inputs
        initial_validation = self.post_retail_validate()
        if 'error' in initial_validation:
            return api_response([initial_validation['error']], None, status.HTTP_200_OK)
        buyer_shop = initial_validation['buyer_shop']
        seller_shop = initial_validation['seller_shop']
        product = initial_validation['product']
        shop_type = initial_validation['shop_type']
        qty = initial_validation['quantity']

        # If Seller Shop is sp Type
        if shop_type == 'sp':
            # Update or create cart for user and shop
            cart = self.post_update_retail_sp_cart(seller_shop, buyer_shop)
            # check for product capping
            proceed = self.retail_capping_check(product, seller_shop, buyer_shop, qty, cart)
            if not proceed['is_success']:
                return api_response([proceed['message']], proceed['data'], status.HTTP_200_OK)
            elif proceed['quantity_check']:
                # check for product available quantity and add to cart
                cart_map = self.retail_quantity_check(seller_shop, product, cart, qty)
            # Check if products are present in cart
            if cart.rt_cart_list.count() <= 0:
                return api_response(['Sorry no product added to this cart yet'], None, status.HTTP_200_OK)
            # process and return response
            return api_response(['Added To Cart'],
                                self.post_serialize_process_sp(cart, seller_shop, buyer_shop, product),
                                status.HTTP_200_OK, True)
        # If Seller Shop is gf type
        elif shop_type == 'gf':
            # Update or create cart for user
            cart = self.post_update_retail_gm_cart()
            # check quantity and add to cart
            if int(qty) == 0:
                delete_cart_mapping(cart, product, 'retail_gf')
            else:
                cart_mapping, _ = GramMappedCartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                cart_mapping.qty = qty
                cart_mapping.save()
            # Check if products are present in cart
            if cart.rt_cart_list.count() <= 0:
                return api_response(['Sorry no product added to this cart yet'], None, status.HTTP_200_OK)
            # process and return response
            return api_response(['Added To Cart'], self.post_serialize_process_gf(cart, seller_shop),
                                status.HTTP_200_OK, True)
        else:
            return api_response(['Sorry shop is not associated with any Gramfactory or any SP'], None,
                                status.HTTP_200_OK)

    @check_pos_shop
    @pos_check_permission_delivery_person
    @PosAddToCart.validate_request_body
    def basic_add_to_cart(self, request, *args, **kwargs):
        """
            Add To Cart
            For cart type 'basic'
        """
        with transaction.atomic():
            product, new_product_info, qty, cart, shop, create_new_product = kwargs['product'], \
                                                                             kwargs['new_product_info'], kwargs[
                                                                                 'quantity'], kwargs['cart'], kwargs[
                                                                                 'shop'], kwargs['create_new_product']
            # Update or create cart for shop
            cart = self.post_update_basic_cart(shop, cart)
            # Create product if not existing
            if create_new_product:
                if product is not None:
                    delete_cart_mapping(cart, product, 'basic')
                product = self.pos_cart_product_create(shop.id, new_product_info, cart.id)
            # Check if product has to be removed
            if not qty > 0:
                delete_cart_mapping(cart, product, 'basic')
            else:
                # Check if price needs to be updated and return selling price
                selling_price = self.get_basic_cart_product_price(product, cart.cart_no)
                # Check if mrp needs to be updated and return mrp
                product_mrp = self.get_basic_cart_product_mrp(product, cart.cart_no)
                # Add quantity to cart
                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, retailer_product=product,
                                                                           product_type=1)
                cart_mapping.selling_price = selling_price
                cart_mapping.qty = qty
                cart_mapping.no_of_pieces = qty
                cart_mapping.qty_conversion_unit_id = kwargs['conversion_unit_id']
                cart_mapping.save()
            # serialize and return response
            return api_response('Added To Cart', self.post_serialize_process_basic(cart), status.HTTP_200_OK, True)

    @check_ecom_user_shop
    @PosAddToCart.validate_request_body_ecom
    def ecom_add_to_cart(self, request, *args, **kwargs):
        """
            Add To Cart
            For cart type 'ECOM'
        """
        if not kwargs['shop'].online_inventory_enabled:
            return api_response("Franchise Shop Is Not Online Enabled!")
        with transaction.atomic():
            # basic validations for inputs
            shop, product, qty = kwargs['shop'], kwargs['product'], kwargs['quantity']
            # Update or create cart for user for shop
            cart = self.post_update_ecom_cart(shop)
            # Check if product has to be removed
            if int(qty) == 0:
                delete_cart_mapping(cart, product, 'ecom')
            else:
                # Add quantity to cart
                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
                                                                           retailer_product=product,
                                                                           product_type=1)
                cart_mapping.selling_price = product.online_price
                cart_mapping.qty = qty
                cart_mapping.no_of_pieces = int(qty)
                cart_mapping.qty_conversion_unit_id = kwargs['conversion_unit_id']
                cart_mapping.save()
            # serialize and return response
            if not CartProductMapping.objects.filter(cart=cart).exists():
                return api_response("No items added in cart yet", {"rt_cart_list": []}, status.HTTP_200_OK, False)
            return api_response('Added To Cart', self.post_serialize_process_basic(cart), status.HTTP_200_OK, True)

    # @check_ecom_user_shop
    @PosAddToCart.validate_request_body_superstore
    def superstore_add_to_cart(self, request, *args, **kwargs):
        """
            Add to cart
            Type (Super Store)
        """
        with transaction.atomic():
            shop = kwargs['shop']
            product, qty = kwargs['product'], kwargs['quantity']
            cart = self.post_update_superstore_cart(shop)
            if qty == 0:
                delete_cart_mapping(cart, product, 'superstore')
            else:
                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
                                                                           cart_product=product)
                cart_mapping.selling_price = kwargs['selling_price']
                cart_mapping.qty = qty
                cart_mapping.no_of_pieces = int(qty)
                cart_mapping.save()
            if cart.rt_cart_list.filter(product_type=1).count() == 0:
                return api_response("No items added in cart yet", {"cart_product_list": []}, status.HTTP_200_OK, False)
            return api_response('Added To Cart', SuperStoreCartSerializer(cart, context={
                'parent_shop_id': kwargs['parent_shop_id']}).data, status.HTTP_200_OK, True)

    def pos_cart_product_create(self, shop_id, product_info, cart_id):

        if product_info['ean'] and (not product_info['linked_pid'] or product_info['linked_pid'] == ''):
            try:
                pid = Product.objects.filter(product_ean_code__startswith=product_info['ean']).last()
                if pid:
                    product_info['linked_pid'] = getattr(pid, 'id')
                    product_info['type'] = 2
            except:
                pass

        product = RetailerProductCls.create_retailer_product(shop_id, product_info['name'], product_info['mrp'],
                                                             product_info['sp'], product_info['linked_pid'],
                                                             product_info['type'], product_info['name'],
                                                             product_info['ean'], self.request.user, 'cart', 'packet',
                                                             None, cart_id)
        PosInventoryCls.stock_inventory(product.id, PosInventoryState.NEW, PosInventoryState.AVAILABLE, 0,
                                        self.request.user, product.sku, PosInventoryChange.STOCK_ADD)
        return product

    def post_retail_validate(self):
        """
            Add To Cart
            Input validation for cart type 'retail'
        """
        qty = self.request.data.get('qty')
        shop_id = self.request.data.get('shop_id')
        # Added Quantity check
        try:
            if qty is None or qty == '' or int(qty) < 0:
                return {'error': "Qty missing/invalid!"}
        except:
            return {'error': "Qty invalid!"}

        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        try:
            product = Product.objects.get(id=self.request.data.get('cart_product'))
        except ObjectDoesNotExist:
            return {'error': "Product Not Found!"}
        # Check if the product is blocked for audit
        is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(product, parent_mapping.parent)
        if is_blocked_for_audit:
            return {'error': ERROR_MESSAGES['4019'].format(product)}
        # Check if product is packing material
        if is_product_not_eligible(product.id):
            return {'error': "Product Is Not Eligible To Order"}
        return {'product': product, 'buyer_shop': parent_mapping.retailer, 'seller_shop': parent_mapping.parent,
                'quantity': qty, 'shop_type': parent_mapping.parent.shop_type.shop_type}

    def post_update_retail_sp_cart(self, seller_shop, buyer_shop):
        """
            Create or update/add product to retail sp Cart
        """
        user = self.request.user
        if Cart.objects.filter(last_modified_by=user, buyer_shop=buyer_shop,
                               cart_status__in=['active', 'pending']).exists():
            cart = Cart.objects.filter(last_modified_by=user, buyer_shop=buyer_shop,
                                       cart_status__in=['active', 'pending']).last()
            cart.cart_type = 'RETAIL'
            cart.approval_status = False
            cart.cart_status = 'active'
            cart.seller_shop = seller_shop
            cart.buyer_shop = buyer_shop
            cart.save()
        else:
            cart = Cart(last_modified_by=user, cart_status='active', cart_type='RETAIL')
            cart.approval_status = False
            cart.seller_shop = seller_shop
            cart.buyer_shop = buyer_shop
            cart.save()
        return cart

    def post_update_retail_gm_cart(self):
        """
            Create or update/add product to retail gm Cart
        """
        user = self.request.user
        if GramMappedCart.objects.filter(last_modified_by=user, cart_status__in=['active', 'pending']).exists():
            cart = GramMappedCart.objects.filter(last_modified_by=user,
                                                 cart_status__in=['active', 'pending']).last()
            cart.cart_status = 'active'
            cart.save()
        else:
            cart = GramMappedCart(last_modified_by=user, cart_status='active')
            cart.save()
        return cart

    def post_update_basic_cart(self, seller_shop, cart=None):
        """
            Create or update/add product to retail basic Cart
        """
        user = self.request.user

        if cart:
            cart.last_modified_by = user
            cart.save()
        else:
            cart = Cart(last_modified_by=user, cart_status='active', cart_type='BASIC',
                        seller_shop=seller_shop)
            cart.approval_status = False
            cart.save()
        return cart

    def post_update_ecom_cart(self, seller_shop):
        """
            Create or update/add product to ecom Cart
        """
        user = self.request.user
        cart = Cart.objects.select_for_update().filter(cart_type='ECOM', buyer=user, cart_status='active',
                                                       seller_shop=seller_shop).last()
        if cart is None:
            cart, _ = Cart.objects.select_for_update().get_or_create(cart_type='ECOM', buyer=user, cart_status='active',
                                                                     seller_shop=seller_shop)
        if cart.seller_shop and cart.seller_shop.id != seller_shop.id:
            CartProductMapping.objects.filter(cart=cart).delete()
        cart.seller_shop = seller_shop
        cart.save()
        return cart

    def post_update_superstore_cart(self, seller_shop):
        """
            Create or update/add product to super store cart
        """
        user = self.request.user
        cart = Cart.objects.select_for_update().filter(cart_type='SUPERSTORE',
                                                       buyer=user,
                                                       cart_status='active',
                                                       seller_shop=seller_shop).last()
        if cart is None:
            cart, _ = Cart.objects.select_for_update().get_or_create(cart_type='SUPERSTORE',
                                                                     buyer=user,
                                                                     cart_status='active',
                                                                     seller_shop=seller_shop)
        if cart.seller_shop and cart.seller_shop.id != seller_shop.id:
            CartProductMapping.objects.filter(cart=cart).delete()
        cart.seller_shop = seller_shop
        cart.save()
        return cart

    @staticmethod
    def retail_ordered_quantity(capping, product, buyer_shop):
        """
            Get ordered quantity for buyer shop in case of retail cart to check capping
        """
        ordered_qty = 0
        capping_start_date, capping_end_date = check_date_range(capping)
        # get all orders for buyer shop
        if capping_start_date.date() == capping_end_date.date():
            capping_range_orders = Order.objects.filter(buyer_shop=buyer_shop,
                                                        created_at__gte=capping_start_date,
                                                        ).exclude(order_status='CANCELLED')
        else:
            capping_range_orders = Order.objects.filter(buyer_shop=buyer_shop,
                                                        created_at__gte=capping_start_date,
                                                        created_at__lte=capping_end_date
                                                        ).exclude(order_status='CANCELLED')
        if capping_range_orders:
            # filters orders for the product and add ordered quantity
            for order in capping_range_orders:
                if order.ordered_cart.rt_cart_list.filter(cart_product=product).exists():
                    ordered_qty += order.ordered_cart.rt_cart_list.filter(cart_product=product).last().qty
        return ordered_qty

    @staticmethod
    def retail_quantity_check(seller_shop, product, cart, qty):
        """
            Add To Cart
            Check available quantity of product for adding to retail cart
        """
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        shop_products_dict = get_stock(seller_shop, type_normal, [product.id])
        cart_mapping, created = CartProductMapping.objects.get_or_create(cart=cart,
                                                                         cart_product=product)
        cart_mapping.qty = qty
        available_qty = shop_products_dict.get(int(product.id), 0) // int(
            cart_mapping.cart_product.product_inner_case_size)
        if int(qty) <= available_qty:
            cart_mapping.no_of_pieces = int(qty) * int(product.product_inner_case_size)
            cart_mapping.capping_error_msg = ''
            cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(int(available_qty))
            cart_mapping.save()
        else:
            cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(int(available_qty))
            cart_mapping.save()
        return cart_mapping

    def retail_capping_check(self, product, seller_shop, buyer_shop, qty, cart):
        """
            Add To Cart
            check if capping is applicable to retail cart product
        """
        capping = product.get_current_shop_capping(seller_shop, buyer_shop)
        # If there is quantity limit on product order for buyer and seller shop
        if capping:
            # get already ordered quantity for product
            ordered_qty = self.retail_ordered_quantity(capping, product, buyer_shop)
            # if ordered qty does not exceed capping qty, qty can be added full or partial
            if capping.capping_qty > ordered_qty:
                return self.retail_capping_remaining(capping.capping_qty, ordered_qty, qty, cart, product, buyer_shop,
                                                     seller_shop)
            else:
                # no product qty can be added further
                return self.retail_capping_exhausted(cart, product, buyer_shop, seller_shop)
        else:
            # no quantity limit on product order for buyer and seller shop
            if int(qty) == 0:
                delete_cart_mapping(cart, product)
            else:
                return {'is_success': True, 'quantity_check': True}
        return {'is_success': True, 'quantity_check': False}

    def retail_capping_remaining(self, capping_qty, ordered_qty, qty, cart, product, buyer_shop, seller_shop):
        """
            Add To Cart
            Capping - When Full or partial quantity can be added to cart
        """
        # Full provided quantity can be added to cart
        if (capping_qty - ordered_qty) >= int(qty):
            if int(qty) == 0:
                delete_cart_mapping(cart, product)
            else:
                return {'is_success': True, 'quantity_check': True}
        else:
            # Only partial qty can be added
            serializer = CartSerializer(Cart.objects.get(id=cart.id), context={
                'parent_mapping_id': seller_shop.id, 'buyer_shop_id': buyer_shop.id})
            if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
                        capping_qty - ordered_qty)]
                cart_mapping.save()
            else:
                return {'is_success': False, 'message': 'The Purchase Limit of the Product is %s #%s' % (
                    capping_qty - ordered_qty, product.id), 'data': serializer.data}
        return {'is_success': True, 'quantity_check': False}

    def retail_capping_exhausted(self, cart, product, buyer_shop, seller_shop):
        delete_cart_mapping(cart, product)
        serializer = CartSerializer(Cart.objects.get(id=cart.id), context={
            'parent_mapping_id': seller_shop.id, 'buyer_shop_id': buyer_shop.id})
        return {'is_success': False, 'message': 'You have already exceeded the purchase limit of'
                                                ' this product #%s' % product.id, 'data': serializer.data}

    def get_basic_cart_product_price(self, product, cart_no):
        """
            Check if retail product price needs to be changed on checkout
            price_change - 1 (change for all), 2 (change for current cart only)
        """
        # Check If Price Change
        price_change = self.request.data.get('price_change')
        selling_price = None
        if price_change in [1, 2]:
            selling_price = self.request.data.get('selling_price')
            if price_change == 1:
                RetailerProductCls.update_price(product.id, selling_price, 'active', self.request.user, 'cart', cart_no)
        elif product.offer_price and product.offer_start_date <= datetime_date.today() <= product.offer_end_date:
            selling_price = product.offer_price
        return selling_price if selling_price else product.selling_price

    def get_basic_cart_product_mrp(self, product, cart_no):
        """
            Check if retail product mrp needs to be changed on checkout
            mrp_change - 1 (change for all), 0 don't change
        """
        # Check If MRP Change
        mrp_change = int(self.request.data.get('mrp_change')) if self.request.data.get('mrp_change') else 0
        product_mrp = None
        if mrp_change == 1:
            product_mrp = self.request.data.get('product_mrp')
            RetailerProductCls.update_mrp(product.id, product_mrp, self.request.user, 'cart', cart_no)
        return product_mrp if product_mrp else product.mrp

    def post_serialize_process_sp(self, cart, seller_shop='', buyer_shop='', product=''):
        """
            Add To Cart
            Serialize and Modify Cart - MRP Check - retail sp cart
        """
        serializer = CartSerializer(Cart.objects.get(id=cart.id), context={'parent_mapping_id': seller_shop.id,
                                                                           'buyer_shop_id': buyer_shop.id})
        for i in serializer.data['rt_cart_list']:
            if not i['cart_product']['price_details']['mrp']:
                delete_cart_mapping(cart, product)
        return serializer.data

    def post_serialize_process_gf(self, cart, seller_shop=''):
        """
            Add To Cart
            Serialize retail Gram Cart
        """
        return GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id),
                                        context={'parent_mapping_id': seller_shop.id}).data

    def post_serialize_process_basic(self, cart):
        """
            Add To Cart
            Serialize basic cart
        """
        cart = Cart.objects.prefetch_related('rt_cart_list').get(id=cart.id)
        data = BasicCartSerializer(cart).data
        # Get nearest cart offer over cart value
        data['next_offer'] = BasicCartOffers.get_cart_nearest_offer(cart, cart.rt_cart_list.all())
        return data

    def serialize_product(self, product):
        return RetailerProductResponseSerializer(product).data


class UserView(APIView):
    """
        User Details
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
            Get Customer Details - POS Shop
            :param request: phone_number
        """
        # check phone_number
        phone_no = self.request.GET.get('phone_number')
        if not phone_no:
            return api_response("Please enter phone number")
        if not re.match(r'^[6-9]\d{9}$', phone_no):
            return api_response("Please enter a valid phone number")

        data, msg = [], 'Customer Does Not Exists'
        orders = Order.objects.filter(seller_shop=kwargs['shop'])
        customer = User.objects.filter(id__in=Subquery(orders.values('buyer_id'))).filter(phone_number=phone_no).last()
        if customer:
            data, msg = PosUserSerializer(customer).data, 'Customer Detail Success'
        return api_response(msg, data, status.HTTP_200_OK, True)


class CartUserView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        # Validate number
        serializer = BasicCartUserViewSerializer(data=self.request.GET)
        if not serializer.is_valid():
            return api_response(serializer_error(serializer))

        # Validate cart id
        initial_validation = self.cart_id_validate(kwargs['pk'], kwargs['shop'])
        if 'error' in initial_validation:
            extra_params = {'error_code': initial_validation['error_code']} if initial_validation['error_code'] else {}
            return api_response(initial_validation['error'], None, status.HTTP_406_NOT_ACCEPTABLE, False, extra_params)
        cart = initial_validation['cart']

        # Create / update customer
        customer = update_customer_pos_cart(self.request.GET.get('phone_number'), cart.seller_shop.id,
                                            self.request.user)

        # add customer to cart
        cart.buyer = customer
        cart.last_modified_by = self.request.user
        cart.save()

        # Reset redeem points on cart
        RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'])

        # Serialize
        data = PosUserSerializer(customer).data
        # Reward detail for customer
        data['reward_detail'] = RewardCls.reward_detail_cart(cart, 0)
        return api_response('Customer Detail Success', data, status.HTTP_200_OK, True)

    @check_pos_shop
    @pos_check_permission_delivery_person
    def put(self, request, *args, **kwargs):
        # Validate number
        serializer = BasicCartUserViewSerializer(data=self.request.data)
        if not serializer.is_valid():
            return api_response(serializer_error(serializer))

        # Validate cart id
        initial_validation = self.cart_id_validate(kwargs['pk'], kwargs['shop'])
        if 'error' in initial_validation:
            extra_params = {'error_code': initial_validation['error_code']} if initial_validation['error_code'] else {}
            return api_response(initial_validation['error'], None, status.HTTP_406_NOT_ACCEPTABLE, False, extra_params)
        cart = initial_validation['cart']

        # Create / update customer
        serializer_data = serializer.data
        customer = update_customer_pos_cart(serializer_data['phone_number'], cart.seller_shop.id, self.request.user,
                                            None, None, None, serializer_data['is_mlm'],
                                            serializer_data['referral_code'])

        # add customer to cart
        cart.buyer = customer
        cart.last_modified_by = self.request.user
        cart.save()

        # Reset redeem points on cart
        RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'])

        # Serialize
        data = PosUserSerializer(customer).data
        # Reward detail for customer
        data['reward_detail'] = RewardCls.reward_detail_cart(cart, 0)
        return api_response('Customer Detail Success', data, status.HTTP_200_OK, True)

    def cart_id_validate(self, cart_id, shop):
        """
            Cart Customer Get Validate
        """
        # Check cart
        cart = Cart.objects.filter(id=cart_id, seller_shop=shop, cart_type='BASIC').last()
        if not cart:
            return {'error': "Cart Doesn't Exist!", 'error_code': None}
        elif cart.cart_status == Cart.ORDERED:
            return {'error': "Order already placed on this cart!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status == Cart.DELETED:
            return {'error': "This cart was deleted!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status not in [Cart.ACTIVE, Cart.PENDING]:
            return {'error': "Active Cart Doesn't Exist!", 'error_code': None}
        return {'cart': cart}


class CartCheckout(APIView):
    """
        Checkout after items added
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
            Checkout
            Apply Offer
        """
        app_type = request.META.get('HTTP_APP_TYPE', '1')
        # POS
        if app_type == '2':
            return self.post_pos_cart_checkout(request, *args, **kwargs)
        # ECOM
        elif app_type == '3':
            return self.post_ecom_cart_checkout(request, *args, **kwargs)

        elif app_type == '4':
            return self.super_store_checkout(request, *args, **kwargs)

        else:
            return api_response('Please provide a valid app_type')

    @check_ecom_user_shop
    def super_store_checkout(self, request, *args, **kwargs):
        """
            Ecom Checkout
            Inputs
            coupon_id
        """
        try:
            cart = Cart.objects.get(cart_type='SUPERSTORE', buyer=self.request.user, cart_status='active',
                                    seller_shop=kwargs['shop'])
        except ObjectDoesNotExist:
            return api_response("No items added in cart yet")
        except Cart.MultipleObjectsReturned:
            cart = Cart.objects.filter(cart_type='SUPERSTORE', buyer=self.request.user, cart_status='active',
                                       seller_shop=kwargs['shop']).last()
        if not self.request.data.get('coupon_id'):
            return api_response("Invalid request")
        with transaction.atomic():
            # Refresh redeem reward
            use_reward_this_month = RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'], app_type="ECOM",
                                                                     use_all=self.request.GET.get('use_rewards', 1))
            # Get offers available now and apply coupon if applicable
            offers = BasicCartOffers.refresh_offers_checkout(cart, False, self.request.data.get('coupon_id'))
            data = self.serialize(cart)

            data['redeem_points_message'] = use_reward_this_month
            time = datetime.now().strftime("%H:%M:%S")
            time = datetime.strptime(time, "%H:%M:%S").time()
            fofo_config = get_config_fofo_shops(kwargs['shop'].id)
            delivery_time = str(fofo_config.get('delivery_time')) + " " + 'min' if fofo_config.get('delivery_time',
                                                                                                   None) else None

            if fofo_config.get('open_time', None) and fofo_config.get('close_time', None) and not (
                    fofo_config['open_time'] < time < fofo_config['close_time']):
                delivery_time = "Your order will be deliverd tomorrow"

            data['estimate_delivery_time'] = delivery_time

            if 'error' in offers:
                return api_response(offers['error'], None, offers['code'])
            if offers['applied']:
                return api_response('Applied Successfully', data, status.HTTP_200_OK, True)
            else:
                return api_response('Not Applicable', data, status.HTTP_200_OK)

    @check_pos_shop
    def post_pos_cart_checkout(self, request, *args, **kwargs):
        """
            POS Checkout
            Inputs
            cart_id
            coupon_id
            spot_discount
            is_percentage (spot discount type)
        """
        # Input validation
        initial_validation = self.post_basic_validate(kwargs['shop'])
        if 'error' in initial_validation:
            return api_response(initial_validation['error'])

        cart = initial_validation['cart']
        # Check spot discount
        spot_discount = self.request.data.get('spot_discount')
        with transaction.atomic():
            # Refresh redeem reward
            redeem_points_message = RewardCls.checkout_redeem_points(cart, cart.redeem_points, kwargs['shop'])
            if spot_discount:
                offers = BasicCartOffers.apply_spot_discount(cart, spot_discount,
                                                             self.request.data.get('is_percentage'))
            else:
                # Get offers available now and apply coupon if applicable
                offers = BasicCartOffers.refresh_offers_checkout(cart, False, self.request.data.get('coupon_id'))
            if 'error' in offers:
                return api_response(offers['error'], None, offers['code'])
            if offers['applied']:
                data = self.serialize(cart, app_type=kwargs.get('app_type', None))
                data.update({"redeem_points_message": redeem_points_message})
                return api_response('Applied Successfully', data, status.HTTP_200_OK, True)
            else:
                data = self.serialize(cart)
                data.update({"redeem_points_message": redeem_points_message})
                return api_response('Not Applicable', data, status.HTTP_200_OK)

    @check_ecom_user_shop
    def post_ecom_cart_checkout(self, request, *args, **kwargs):
        """
            Ecom Checkout
            Inputs
            coupon_id
        """
        try:
            cart = Cart.objects.get(cart_type='ECOM', buyer=self.request.user, seller_shop=kwargs['shop'],
                                    cart_status='active')
        except ObjectDoesNotExist:
            return api_response("No items added in cart yet")
        if not self.request.data.get('coupon_id'):
            return api_response("Invalid request")
        with transaction.atomic():
            # Refresh redeem reward
            use_reward_this_month = RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'], app_type="ECOM",
                                                                     use_all=self.request.GET.get('use_rewards', 1))
            # Get offers available now and apply coupon if applicable
            offers = BasicCartOffers.refresh_offers_checkout(cart, False, self.request.data.get('coupon_id'))
            data = self.serialize(cart)

            data['redeem_points_message'] = use_reward_this_month
            time = datetime.now().strftime("%H:%M:%S")
            time = datetime.strptime(time, "%H:%M:%S").time()
            fofo_config = get_config_fofo_shops(kwargs['shop'].id)
            delivery_time = str(fofo_config.get('delivery_time')) + " " + 'min' if fofo_config.get('delivery_time',
                                                                                                   None) else None

            if fofo_config.get('open_time', None) and fofo_config.get('close_time', None) and not (
                    fofo_config['open_time'] < time < fofo_config['close_time']):
                delivery_time = "Your order will be deliverd tomorrow"

            data['estimate_delivery_time'] = delivery_time

            if 'error' in offers:
                return api_response(offers['error'], None, offers['code'])
            if offers['applied']:
                return api_response('Applied Successfully', data, status.HTTP_200_OK, True)
            else:
                return api_response('Not Applicable', data, status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        """
            Get Checkout Amount Info, Offers Applied-Applicable
        """
        app_type = request.META.get('HTTP_APP_TYPE', '1')
        # POS
        if app_type == '2':
            return self.get_pos_cart_checkout(request, *args, **kwargs)
        elif app_type == '3':
            return self.get_ecom_cart_checkout(request, *args, **kwargs)
        elif app_type == '4':
            return self.get_superstore_cart_checkout(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid app_type')

    @check_pos_shop
    def get_pos_cart_checkout(self, request, *args, **kwargs):
        """
            POS cart checkout
        """
        cart_id = self.request.GET.get('cart_id')
        try:
            cart = Cart.objects.get(pk=cart_id, seller_shop=kwargs['shop'], cart_status__in=['active', 'pending'],
                                    cart_type='BASIC')
        except ObjectDoesNotExist:
            return api_response("Cart Does Not Exist / Already Closed")
        with transaction.atomic():
            redeem_points = self.request.GET.get('redeem_points')
            # Auto apply highest applicable discount
            auto_apply = self.request.GET.get('auto_apply') if not redeem_points else False
            # Get Offers Applicable, Verify applied offers, Apply highest discount on cart if auto apply
            offers = BasicCartOffers.refresh_offers_checkout(cart, auto_apply, None)
            # Redeem pep Coins on order
            redeem_points = redeem_points if redeem_points else cart.redeem_points
            # Refresh redeem reward
            redeem_points_message = RewardCls.checkout_redeem_points(cart, int(redeem_points), kwargs['shop'])
            app_type = kwargs['app_type']
            data = self.serialize(cart, offers, app_type)
            data.update({"redeem_points_message": redeem_points_message if redeem_points_message else ""})

            return api_response("Cart Checkout", data, status.HTTP_200_OK, True)

    @check_ecom_user_shop
    def get_ecom_cart_checkout(self, request, *args, **kwargs):
        """
            ECOM cart checkout
        """
        try:
            cart = Cart.objects.filter(cart_type='ECOM', buyer=self.request.user, seller_shop=kwargs['shop'],
                                       cart_status='active').last()
        except ObjectDoesNotExist:
            return api_response("No items added in cart yet")

        with transaction.atomic():
            # Get Offers Applicable, Verify applied offers, Apply highest discount on cart if auto apply
            offers = BasicCartOffers.refresh_offers_checkout(cart, False, None)
            # Refresh redeem reward
            use_reward_this_month = RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'], app_type="ECOM",
                                                                     use_all=self.request.GET.get('use_rewards', 1))
            data = self.serialize(cart, offers)
            address = AddressCheckoutSerializer(cart.buyer.ecom_user_address.filter(default=True).last()).data
            data.update({'default_address': address})
            delivery_time = get_config_fofo_shops(kwargs['shop'])
            time = datetime.now().strftime("%H:%M:%S")
            time = datetime.strptime(time, "%H:%M:%S").time()
            fofo_config = get_config_fofo_shops(kwargs['shop'].id)
            delivery_time = str(fofo_config.get('delivery_time')) + " " + 'min' if fofo_config.get('delivery_time',
                                                                                                   None) else None

            if fofo_config.get('open_time', None) and fofo_config.get('close_time', None) and not (
                    fofo_config['open_time'] < time < fofo_config['close_time']):
                delivery_time = "Your order will be deliverd tomorrow"
            data['estimate_delivery_time'] = delivery_time
            data.update({'saving': round(data['total_mrp'] - data['amount_payable'], 2)})
            data.update({"redeem_points_message": use_reward_this_month if use_reward_this_month else ""})
            return api_response("Cart Checkout", data, status.HTTP_200_OK, True)

    @check_ecom_user_shop
    def get_superstore_cart_checkout(self, request, *args, **kwargs):
        try:
            cart = Cart.objects.filter(cart_type='SUPERSTORE',
                                       buyer=self.request.user,
                                       seller_shop=kwargs['shop'],
                                       cart_status='active').last()
        except ObjectDoesNotExist:
            return api_response("No items added in cart yet")
        parent_shop = kwargs['shop'].get_shop_parent
        PosCartCls.refresh_prices(cart.rt_cart_list.all(), parent_shop_id=parent_shop.id)
        order_amount = cart.order_amount_after_discount
        min_order_value = GlobalConfig.objects.get(key='min_order_value_super_store').value
        if order_amount < min_order_value:
            return api_response(
                "A minimum total purchase amount of {} is required to checkout.".format(min_order_value),
                None, status.HTTP_200_OK, False)
        with transaction.atomic():
            offers = BasicCartOffers.refresh_offers_checkout(cart, False, None)
            use_reward_this_month = RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'],
                                                                     app_type="SUPERSTORE",
                                                                     use_all=self.request.GET.get('use_rewards', 1))
            data = self.serialize(cart, offers)
            address = AddressCheckoutSerializer(cart.buyer.ecom_user_address.filter(default=True).last()).data
            data.update({'default_address': address})
            delivery_buffer = get_config("superstore_delivery_buffer", 7)
            delivery_date_expected = (datetime.now() + timedelta(delivery_buffer)).date()
            delivery_time = delivery_date_expected
            data['estimate_delivery_time'] = delivery_time
            data.update({'saving': round(data['total_mrp'] - data['amount_payable'], 2)})
            data.update({"redeem_points_message": use_reward_this_month if use_reward_this_month else ""})
            return api_response("Cart Checkout", data, status.HTTP_200_OK, True)

    def delete(self, request, *args, **kwargs):
        """
            Checkout
            Delete any applied cart offers
        """
        app_type = request.META.get('HTTP_APP_TYPE', '1')
        # POS
        if app_type == '2':
            return self.delete_pos_offer(request, *args, **kwargs)
        elif app_type == '3':
            return self.delete_ecom_offer(request, *args, **kwargs)
        elif app_type == '4':
            return self.delete_super_store_offer(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid app_type')


    @check_ecom_user_shop
    def delete_super_store_offer(self, request, *args, **kwargs):
        """
            Checkout
            Delete any applied cart offers
        """
        try:
            cart = Cart.objects.filter(cart_type='SUPERSTORE',
                                       buyer=self.request.user,
                                       seller_shop=kwargs['shop'],
                                       cart_status='active').last()
        except ObjectDoesNotExist:
            return api_response("No items added in cart yet")
        RewardCls.checkout_redeem_points(cart, 0,shop=kwargs['shop'], app_type="SUPERSTORE", use_all=self.request.GET.get('use_rewards', 1))
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        for product_map in cart_products:
            cart_value += product_map.selling_price * product_map.qty
        with transaction.atomic():
            offers_list = BasicCartOffers.update_cart_offer(cart.offers, cart_value)
            cart.offers = offers_list
            cart.save()
            return api_response("Removed Offer From Cart Successfully", self.serialize(cart, None,
                                                                                       request.META.get('HTTP_APP_TYPE',
                                                                                                        '1')),
                                status.HTTP_200_OK, True)


    @check_pos_shop
    def delete_pos_offer(self, request, *args, **kwargs):
        try:
            cart = Cart.objects.get(pk=kwargs['pk'], seller_shop=kwargs['shop'], cart_status__in=['active', 'pending'],
                                    cart_type='BASIC')
        except ObjectDoesNotExist:
            return api_response("Cart Does Not Exist / Already Closed")
        if self.request.GET.get('redeem_points'):
            redeem_points = self.request.GET.get('redeem_points')
            redeem_points = redeem_points if redeem_points else cart.redeem_points
            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, int(redeem_points), shop=kwargs['shop'])
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        for product_map in cart_products:
            cart_value += product_map.selling_price * product_map.qty
        with transaction.atomic():
            offers_list = BasicCartOffers.update_cart_offer(cart.offers, cart_value)
            cart.offers = offers_list
            cart.save()
            return api_response("Removed Offer From Cart Successfully", self.serialize(cart, None,
                                                                                       request.META.get('HTTP_APP_TYPE',
                                                                                                        '1')),
                                status.HTTP_200_OK, True)

    @check_ecom_user_shop
    def delete_ecom_offer(self, request, *args, **kwargs):
        """
            Checkout
            Delete any applied cart offers
        """
        try:
            cart = Cart.objects.get(cart_type='ECOM', buyer=self.request.user, seller_shop=kwargs['shop'],
                                    cart_status='active')
        except ObjectDoesNotExist:
            return api_response("No items added in cart yet")
        RewardCls.checkout_redeem_points(cart, 0, shop=kwargs['shop'], app_type="ECOM",
                                         use_all=self.request.GET.get('use_rewards', 1))
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        for product_map in cart_products:
            cart_value += product_map.selling_price * product_map.qty
        with transaction.atomic():
            offers_list = BasicCartOffers.update_cart_offer(cart.offers, cart_value)
            cart.offers = offers_list
            cart.save()
            return api_response("Removed Offer From Cart Successfully", self.serialize(cart, None,
                                                                                       request.META.get('HTTP_APP_TYPE',
                                                                                                        '1')),
                                status.HTTP_200_OK, True)

    def post_basic_validate(self, shop):
        """
            Add cart offer in checkout
            Input validation
        """
        cart_id = self.request.data.get('cart_id')
        try:
            cart = Cart.objects.get(pk=cart_id, seller_shop=shop, cart_status__in=['active', 'pending'],
                                    cart_type='BASIC')
        except ObjectDoesNotExist:
            return {'error': "Cart Does Not Exist / Already Closed"}
        if not self.request.data.get('coupon_id') and not self.request.data.get('spot_discount'):
            return {'error': "Please Provide Coupon Id/Spot Discount"}
        if self.request.data.get('coupon_id') and self.request.data.get('spot_discount'):
            return {'error': "Please Provide Only One Of Coupon Id, Spot Discount"}
        if self.request.data.get('spot_discount') and self.request.data.get('is_percentage') not in [0, 1]:
            return {'error': "Please Provide A Valid Spot Discount Type"}
        return {'cart': cart}

    def serialize(self, cart, offers=None, app_type=None):
        """
            Checkout serializer
            Payment Info plus Offers
        """
        serializer = CheckoutSerializer(Cart.objects.prefetch_related('rt_cart_list').get(pk=cart.id),
                                        context={'app_type': app_type})
        response = serializer.data
        if offers:
            response['available_offers'] = offers['total_offers']
            if offers['spot_discount']:
                response['spot_discount'] = offers['spot_discount']
        response['key_p'] = str(config('PAYU_KEY'))
        return response


# class AddToCart(APIView):
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def post(self, request):
#         cart_product = self.request.POST.get('cart_product')
#         qty = self.request.POST.get('qty')
#         shop_id = self.request.POST.get('shop_id')
#         msg = {'is_success': False, 'message': ['Sorry no any mapping with any shop!'], 'response_data': None}
#
#         if Shop.objects.filter(id=shop_id).exists():
#             # get Product
#             try:
#                 product = Product.objects.get(id=cart_product)
#             except ObjectDoesNotExist:
#                 msg['message'] = ["Product not Found"]
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             if checkNotShopAndMapping(shop_id):
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             parent_mapping = getShopMapping(shop_id)
#             if parent_mapping is None:
#                 return Response(msg, status=status.HTTP_200_OK)
#             if qty is None or qty == '':
#                 msg['message'] = ["Qty not Found"]
#                 return Response(msg, status=status.HTTP_200_OK)
#             # Check if product blocked for audit
#             is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(
#                                                                                 Product.objects.get(id=cart_product),
#                                                                                 parent_mapping.parent)
#             if is_blocked_for_audit:
#                 msg['message'] = [ERROR_MESSAGES['4019'].format(Product.objects.get(id=cart_product))]
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             if is_product_not_eligible(cart_product):
#                 msg['message'] = ["Product Not Eligible To Order"]
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             #  if shop mapped with SP
#             # available = get_stock(parent_mapping.parent).filter(sku__id=cart_product, quantity__gt=0).values(
#             #     'sku__id').annotate(quantity=Sum('quantity'))
#             #
#             # shop_products_dict = collections.defaultdict(lambda: 0,
#             #                                              {g['sku__id']: int(g['quantity']) for g in available})
#             type_normal = InventoryType.objects.filter(inventory_type='normal').last()
#             available = get_stock(parent_mapping.parent, type_normal, [cart_product])
#             shop_products_dict = available
#             if parent_mapping.parent.shop_type.shop_type == 'sp':
#                 ordered_qty = 0
#                 product = Product.objects.get(id=cart_product)
#                 # to check capping is exist or not for warehouse and product with status active
#                 capping = product.get_current_shop_capping(parent_mapping.parent, parent_mapping.retailer)
#                 if Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
#                                        cart_status__in=['active', 'pending']).exists():
#                     cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
#                                                cart_status__in=['active', 'pending']).last()
#                     cart.cart_type = 'RETAIL'
#                     cart.approval_status = False
#                     cart.cart_status = 'active'
#                     cart.seller_shop = parent_mapping.parent
#                     cart.buyer_shop = parent_mapping.retailer
#                     cart.save()
#                 else:
#                     cart = Cart(last_modified_by=self.request.user, cart_status='active')
#                     cart.cart_type = 'RETAIL'
#                     cart.approval_status = False
#                     cart.seller_shop = parent_mapping.parent
#                     cart.buyer_shop = parent_mapping.retailer
#                     cart.save()
#
#                 if capping:
#                     # to get the start and end date according to capping type
#                     start_date, end_date = check_date_range(capping)
#                     capping_start_date = start_date
#                     capping_end_date = end_date
#                     if capping_start_date.date() == capping_end_date.date():
#                         capping_range_orders = Order.objects.filter(buyer_shop=parent_mapping.retailer,
#                                                                     created_at__gte=capping_start_date.date(),
#                                                                     ).exclude(order_status='CANCELLED')
#                     else:
#                         capping_range_orders = Order.objects.filter(buyer_shop=parent_mapping.retailer,
#                                                                     created_at__gte=capping_start_date,
#                                                                     created_at__lte=capping_end_date).exclude(
#                             order_status='CANCELLED')
#                     if capping_range_orders:
#                         for order in capping_range_orders:
#                             if order.ordered_cart.rt_cart_list.filter(cart_product=product).exists():
#                                 ordered_qty += order.ordered_cart.rt_cart_list.filter(cart_product=product).last().qty
#                     if capping.capping_qty > ordered_qty:
#                         if (capping.capping_qty - ordered_qty) >= int(qty):
#                             if int(qty) == 0:
#                                 if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
#                                     CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
#
#                             else:
#                                 cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
#                                                                                            cart_product=product)
#                                 cart_mapping.qty = qty
#                                 available_qty = shop_products_dict[int(cart_product)] // int(
#                                     cart_mapping.cart_product.product_inner_case_size)
#                                 if int(qty) <= available_qty:
#                                     cart_mapping.no_of_pieces = int(qty) * int(product.product_inner_case_size)
#                                     cart_mapping.capping_error_msg = ''
#                                     cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(
#                                         int(available_qty))
#                                     cart_mapping.save()
#                                 else:
#                                     cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(
#                                         int(available_qty))
#                                     cart_mapping.save()
#                         else:
#                             serializer = CartSerializer(Cart.objects.get(id=cart.id),
#                                                         context={'parent_mapping_id': parent_mapping.parent.id,
#                                                                  'buyer_shop_id': shop_id})
#                             if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
#                                 cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
#                                                                                            cart_product=product)
#                                 if (capping.capping_qty - ordered_qty) > 0:
#                                     cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
#                                             capping.capping_qty - ordered_qty)]
#                                 else:
#                                     cart_mapping.capping_error_msg = ['You have already exceeded the purchase limit of this product']
#                                 cart_mapping.save()
#                             else:
#                                 msg = {'is_success': True, 'message': ['The Purchase Limit of the Product is %s #%s' % (
#                                     capping.capping_qty - ordered_qty, cart_product)], 'response_data': serializer.data}
#                                 return Response(msg, status=status.HTTP_200_OK)
#
#                     else:
#                         if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
#                             cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
#                             if (capping.capping_qty - ordered_qty) > 0:
#                                 if (capping.capping_qty - ordered_qty) < 0:
#                                     cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
#                                             0)]
#                                 else:
#                                     cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
#                                             capping.capping_qty - ordered_qty)]
#                             else:
#                                 cart_mapping.capping_error_msg = ['You have already exceeded the purchase limit of this product']
#                                 CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
#                             # cart_mapping.save()
#                         else:
#                             serializer = CartSerializer(Cart.objects.get(id=cart.id),
#                                                         context={'parent_mapping_id': parent_mapping.parent.id,
#                                                                  'buyer_shop_id': shop_id})
#                             if (capping.capping_qty - ordered_qty) < 0:
#                                 msg = {'is_success': True, 'message': ['You have already exceeded the purchase limit of this product #%s' % (
#                                     cart_product)], 'response_data': serializer.data}
#                             else:
#                                 msg = {'is_success': True, 'message': ['You have already exceeded the purchase limit of this product #%s' % (
#                                     cart_product)], 'response_data': serializer.data}
#                             return Response(msg, status=status.HTTP_200_OK)
#                 else:
#                     if int(qty) == 0:
#                         if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
#                             CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
#
#                     else:
#                         cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
#                         available_qty = shop_products_dict.get(int(cart_product),0) // int(
#                             cart_mapping.cart_product.product_inner_case_size)
#                         cart_mapping.qty = qty
#                         if int(qty) <= available_qty:
#                             cart_mapping.no_of_pieces = int(qty) * int(product.product_inner_case_size)
#                             cart_mapping.capping_error_msg = ''
#                             cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(int(available_qty))
#                             cart_mapping.save()
#                         else:
#                             cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(int(available_qty))
#                             cart_mapping.save()
#
#                 if cart.rt_cart_list.count() <= 0:
#                     msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
#                            'response_data': None}
#                 else:
#                     serializer = CartSerializer(Cart.objects.get(id=cart.id),
#                                                 context={'parent_mapping_id': parent_mapping.parent.id,
#                                                          'buyer_shop_id': shop_id})
#                     for i in serializer.data['rt_cart_list']:
#                         if i['cart_product']['price_details']['mrp'] == False:
#                             CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
#                             msg = {'is_success': True, 'message': ['Data added to cart'],
#                                    'response_data': serializer.data}
#                         else:
#                             msg = {'is_success': True, 'message': ['Data added to cart'],
#                                    'response_data': serializer.data}
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             #  if shop mapped with gf
#             elif parent_mapping.parent.shop_type.shop_type == 'gf':
#                 if GramMappedCart.objects.filter(last_modified_by=self.request.user,
#                                                  cart_status__in=['active', 'pending']).exists():
#                     cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
#                                                          cart_status__in=['active', 'pending']).last()
#                     cart.cart_status = 'active'
#                     cart.save()
#                 else:
#                     cart = GramMappedCart(last_modified_by=self.request.user, cart_status='active')
#                     cart.save()
#
#                 if int(qty) == 0:
#                     if GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
#                         GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
#
#                 else:
#                     cart_mapping, _ = GramMappedCartProductMapping.objects.get_or_create(cart=cart,
#                                                                                          cart_product=product)
#                     cart_mapping.qty = qty
#                     cart_mapping.save()
#
#                 if cart.rt_cart_list.count() <= 0:
#                     msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
#                            'response_data': None}
#                 else:
#                     serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id),
#                                                           context={'parent_mapping_id': parent_mapping.parent.id})
#
#                     msg = {'is_success': True, 'message': ['Data added to cart'], 'response_data': serializer.data}
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             else:
#                 msg = {'is_success': False,
#                        'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
#                        'response_data': None}
#                 return Response(msg, status=status.HTTP_200_OK)
#
#
#         else:
#             return Response(msg, status=status.HTTP_200_OK)
#
#     def sp_mapping_cart(self, qty, product):
#         pass
#
#     def gf_mapping_cart(self, qty, product):
#         pass


# class CartDetail(APIView):
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def delivery_message(self, shop_type):
#         date_time_now = datetime.now()
#         day = date_time_now.strftime("%A")
#         time = date_time_now.strftime("%H")
#
#         if int(time) < 17 and not (day == 'Saturday'):
#             return str('Order now and get by {}.Min Order amt Rs {}.'.format(
#                 (date_time_now + timedelta(days=1)).strftime('%A'), str(shop_type.shop_min_amount)))
#         elif (day == 'Friday'):
#             return str('Order now and get by {}.Min Order amt Rs {}.'.format(
#                 (date_time_now + timedelta(days=3)).strftime('%A'), str(shop_type.shop_min_amount)))
#         else:
#             return str('Order now and get by {}.Min Order amt Rs {}.'.format(
#                 (date_time_now + timedelta(days=2)).strftime('%A'), str(shop_type.shop_min_amount)))
#
#     def get(self, request, *args, **kwargs):
#         shop_id = self.request.GET.get('shop_id')
#         msg = {'is_success': False, 'message': ['Sorry shop or shop mapping not found'], 'response_data': None}
#
#         if checkNotShopAndMapping(shop_id):
#             return Response(msg, status=status.HTTP_200_OK)
#
#         parent_mapping = getShopMapping(shop_id)
#         if parent_mapping is None:
#             return Response(msg, status=status.HTTP_200_OK)
#
#         # if shop mapped with sp
#         if parent_mapping.parent.shop_type.shop_type == 'sp':
#             if Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
#                                    cart_status__in=['active', 'pending']).exists():
#                 cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
#                                            cart_status__in=['active', 'pending']).last()
#                 Cart.objects.filter(id=cart.id).update(offers=cart.offers_applied())
#                 cart_products = CartProductMapping.objects.select_related(
#                     'cart_product'
#                 ).filter(
#                     cart=cart
#                 )
#
#                 # Check and remove if any product blocked for audit
#                 cart_product_to_be_deleted = []
#                 for p in cart_products:
#                     is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
#                                                                                             parent_mapping.parent)
#                     if is_blocked_for_audit:
#                         cart_product_to_be_deleted.append(p.id)
#                 if len(cart_product_to_be_deleted) > 0:
#                     CartProductMapping.objects.filter(id__in=cart_product_to_be_deleted).delete()
#                     cart_products = CartProductMapping.objects.select_related('cart_product').filter(cart=cart)
#
#                 # available = get_stock(parent_mapping.parent).filter(sku__id__in=cart_products.values('cart_product'),
#                 #                                                     quantity__gt=0).values('sku__id').annotate(
#                 #     quantity=Sum('quantity'))
#                 # shop_products_dict = collections.defaultdict(lambda: 0,
#                 #                                              {g['sku__id']: int(g['quantity']) for g in available})
#
#                 for cart_product in cart_products:
#                     item_qty = CartProductMapping.objects.filter(cart=cart,
#                                                                  cart_product=cart_product.cart_product).last().qty
#                     updated_no_of_pieces = (item_qty * int(cart_product.cart_product.product_inner_case_size))
#                     CartProductMapping.objects.filter(cart=cart, cart_product=cart_product.cart_product).update(
#                         no_of_pieces=updated_no_of_pieces)
#                 if cart.rt_cart_list.count() <= 0:
#                     msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
#                            'response_data': None}
#                 else:
#                     for i in Cart.objects.get(id=cart.id).rt_cart_list.all():
#                         if i.cart_product.getMRP(cart.seller_shop.id, cart.buyer_shop.id) == False:
#                             CartProductMapping.objects.filter(cart__id=cart.id,
#                                                               cart_product__id=i.cart_product.id).delete()
#
#
#                     serializer = CartSerializer(
#                         Cart.objects.get(id=cart.id),
#                         context={'parent_mapping_id': parent_mapping.parent.id,
#                                  'buyer_shop_id': shop_id,
#                                  'delivery_message': self.delivery_message(parent_mapping.parent.shop_type)}
#                     )
#                     for i in serializer.data['rt_cart_list']:
#                         if not i['cart_product']['product_pro_image']:
#                             product = Product.objects.get(id=i['cart_product']['id'])
#                             if product.use_parent_image:
#                                 for im in product.parent_product.parent_product_pro_image.all():
#                                     parent_image_serializer = ParentProductImageSerializer(im)
#                                     i['cart_product']['product_pro_image'].append(parent_image_serializer.data)
#
#                         if i['cart_product']['price_details']['mrp'] == False:
#                             i['qty'] = 0
#                             CartProductMapping.objects.filter(cart__id=i['cart']['id'],
#                                                               cart_product__id=i['cart_product']['id']).delete()
#                             msg = {
#                                 'is_success': True,
#                                 'message': [''],
#                                 'response_data': serializer.data
#                             }
#                         else:
#                             msg = {
#                                 'is_success': True,
#                                 'message': [''],
#                                 'response_data': serializer.data
#                             }
#
#                 return Response(msg, status=status.HTTP_200_OK)
#             else:
#                 msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
#                        'response_data': None}
#                 return Response(msg, status=status.HTTP_200_OK)
#
#         # if shop mapped with gf
#         elif parent_mapping.parent.shop_type.shop_type == 'gf':
#             if GramMappedCart.objects.filter(last_modified_by=self.request.user,
#                                              cart_status__in=['active', 'pending']).exists():
#                 cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
#                                                      cart_status__in=['active', 'pending']).last()
#                 if cart.rt_cart_list.count() <= 0:
#                     msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
#                            'response_data': None}
#                 else:
#                     serializer = GramMappedCartSerializer(
#                         GramMappedCart.objects.get(id=cart.id),
#                         context={'parent_mapping_id': parent_mapping.parent.id,
#                                  'delivery_message': self.delivery_message(parent_mapping.parent.shop_type)}
#                     )
#                     msg = {'is_success': True, 'message': [
#                         ''], 'response_data': serializer.data}
#                 return Response(msg, status=status.HTTP_200_OK)
#             else:
#                 msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
#                        'response_data': None}
#                 return Response(msg, status=status.HTTP_200_OK)
#
#         else:
#             msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
#                    'response_data': None}
#             return Response(msg, status=status.HTTP_200_OK)


def order_pickup_genrate_invioce(request, order):
    if order.ordered_cart.cart_type != 'ECOM':
        return api_response("Invalid action")
    # if order.order_status != Order.PICKUP_CREATED:
    #     return api_response("This order is not picked yet or is already out for delivery")
    try:
        delivery_person = User.objects.get(id=request.user.id)
    except:
        return api_response("Please select a delivery person")
    order.order_status = Order.OUT_FOR_DELIVERY
    order.delivery_person = delivery_person
    ###### trip me save created
    order.save()
    shipment = OrderedProduct.objects.filter(order=order).last()
    shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
    shipment.save()
    shipment.shipment_status = 'OUT_FOR_DELIVERY'
    shipment.save()
    if shipment.pos_trips.filter(trip_type='ECOM').exists():
        pos_trip = shipment.pos_trips.filter(trip_type='ECOM').last()
    else:
        pos_trip = PosTrip.objects.create(trip_type='ECOM',
                                          shipment=shipment)
    pos_trip.trip_start_at = datetime.now()
    pos_trip.save()
    # Inventory move from ordered to picked
    ordered_products = ShipmentProducts.objects.filter(ordered_product=shipment)
    for product_map in ordered_products:
        product_id = product_map.retailer_product_id
        if product_map.shipped_qty > 0:
            PosInventoryCls.order_inventory(product_id, PosInventoryState.ORDERED,
                                            PosInventoryState.SHIPPED,
                                            product_map.shipped_qty,
                                            request.user, order.order_no, PosInventoryChange.SHIPPED)
        ordered_p = CartProductMapping.objects.get(cart=order.ordered_cart,
                                                   retailer_product=product_map.retailer_product,
                                                   product_type=product_map.product_type)
        if ordered_p.qty - product_map.shipped_qty > 0:
            PosInventoryCls.order_inventory(product_id, PosInventoryState.ORDERED,
                                            PosInventoryState.AVAILABLE,
                                            ordered_p.qty - product_map.shipped_qty,
                                            request.user, order.order_no, PosInventoryChange.SHIPPED)
    pdf_generation_retailer(request, order.id)


def order_shipment(request, data, *args, **kwargs):
    shop = kwargs['shop']
    serializer = EcomShipmentSerializer(data=data, context={'shop': shop})
    if serializer.is_valid():
        with transaction.atomic():
            data = serializer.validated_data
            products_info, order_id = data['products'], data['order_id']
            order = Order.objects.filter(pk=order_id, seller_shop=shop,
                                         order_status__in=['ordered', Order.PICKUP_CREATED],
                                         ordered_cart__cart_type='ECOM').last()
            # Create shipment
            shipment = OrderedProduct.objects.filter(order=order).last()
            if not shipment:
                shipment = OrderedProduct(order=order)
                shipment.save()
            for product_map in products_info:
                product_id, qty, product_type = product_map['product_id'], product_map['picked_qty'], product_map[
                    'product_type']
                ordered_product_mapping, _ = ShipmentProducts.objects.get_or_create(ordered_product=shipment,
                                                                                    retailer_product_id=product_id,
                                                                                    product_type=product_type)
                ordered_product_mapping.shipped_qty = qty
                ordered_product_mapping.picked_pieces = qty
                ordered_product_mapping.selling_price = product_map['selling_price']
                ordered_product_mapping.save()
                # Item Batch
                batch = OrderedProductBatch.objects.filter(ordered_product_mapping=ordered_product_mapping).last()
                if not batch:
                    OrderedProductBatch.objects.create(ordered_product_mapping=ordered_product_mapping,
                                                       pickup_quantity=qty, quantity=qty, delivered_qty=qty)
                else:
                    batch.pickup_quantity = qty
                    batch.quantity = qty
                    batch.delivered_qty = qty
                    batch.save()

            order.order_status = Order.PICKUP_CREATED
            order.ordered_by = request.user
            order.save()
            return True
    else:
        return False


class ReservedOrder(generics.ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        shop_id = self.request.POST.get('shop_id')
        msg = {'is_success': False,
               'message': ['No any product available in this cart'],
               'response_data': None, 'is_shop_time_entered': False}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if not parent_mapping:
            return Response(msg, status=status.HTTP_200_OK)

        parent_shop_type = parent_mapping.parent.shop_type.shop_type
        # if shop mapped with sp
        if parent_shop_type == 'sp':
            ordered_qty = 0
            item_qty = 0
            updated_no_of_pieces = 0
            cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
                                       cart_status__in=['active', 'pending'])
            if cart.exists():
                cart = cart.last()
                Cart.objects.filter(id=cart.id).update(offers=cart.offers_applied())
                cart_products = CartProductMapping.objects.select_related(
                    'cart_product'
                ).filter(
                    cart=cart
                )

                # Check and remove if any product blocked for audit
                # Check and remove if product quantity is not valid
                for p in cart_products:
                    is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
                                                                                            parent_mapping.parent)
                    if is_blocked_for_audit or p.qty <= 0:
                        info_logger.info(f"ReservedOrder | Delete product from cart | cart {cart.cart_no} | "
                                         f"product {p.cart_product.product_sku} | audit blocked {is_blocked_for_audit} | "
                                         f"cart qty {p.qty}")
                        p.delete()

                # Check if products available in cart
                if cart_products.count() <= 0:
                    msg = {'is_success': False,
                           'message': ['No product is available in cart'],
                           'response_data': None,
                           'is_shop_time_entered': False}
                    return Response(msg, status=status.HTTP_200_OK)

                cart_products.update(qty_error_msg='')
                cart_products.update(capping_error_msg='')
                cart_product_ids = cart_products.values('cart_product')
                # shop_products_available = get_stock(parent_mapping.parent).filter(sku__id__in=cart_product_ids,
                #                                                                   quantity__gt=0).values(
                #     'sku__id').annotate(quantity=Sum('quantity'))
                type_normal = InventoryType.objects.filter(inventory_type='normal').last()
                shop_products_available = get_stock(parent_mapping.parent, type_normal, cart_product_ids)
                shop_products_dict = shop_products_available

                products_available = {}
                products_unavailable = []
                for cart_product in cart_products:
                    item_qty = CartProductMapping.objects.filter(cart=cart,
                                                                 cart_product=cart_product.cart_product).last().qty
                    updated_no_of_pieces = (item_qty * int(cart_product.cart_product.product_inner_case_size))
                    CartProductMapping.objects.filter(cart=cart, cart_product=cart_product.cart_product).update(
                        no_of_pieces=updated_no_of_pieces)
                    coupon_usage_count = 0
                    self.update_coupon_usage(cart, cart_product, parent_mapping)
                    product_availability = shop_products_dict.get(cart_product.cart_product.id, 0)

                    ordered_amount = (
                            int(cart_product.qty) *
                            int(cart_product.cart_product.product_inner_case_size))

                    product_qty = int(cart_product.qty)

                    if product_availability >= ordered_amount:
                        products_available[cart_product.cart_product.id] = ordered_amount
                    else:
                        cart_product.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(
                            int(product_availability) // int(
                                cart_product.product_inner_case_size))  # TODO: Needs to be improved
                        cart_product.save()
                        products_unavailable.append(cart_product.id)
                    # to check capping is exist or not for warehouse and product with status active
                    capping = cart_product.cart_product.get_current_shop_capping(parent_mapping.parent,
                                                                                 parent_mapping.retailer)
                    if capping:
                        cart_products = cart_product.cart_product
                        msg = capping_check(capping, parent_mapping, cart_products, product_qty, ordered_qty)
                        if msg[0] is False:
                            serializer = CartSerializer(cart, context={
                                'parent_mapping_id': parent_mapping.parent.id,
                                'buyer_shop_id': shop_id})
                            msg = {'is_success': True,
                                   'message': msg[1], 'response_data': serializer.data}
                            return Response(msg, status=status.HTTP_200_OK)
                    else:
                        pass

                if products_unavailable:
                    serializer = CartSerializer(
                        cart,
                        context={
                            'parent_mapping_id': parent_mapping.parent.id,
                            'buyer_shop_id': shop_id
                        })
                    for i in serializer.data['rt_cart_list']:
                        if i['cart_product']['product_mrp'] == False:
                            i['qty'] = 0
                            i['cart_product']['product_mrp'] = 0
                            CartProductMapping.objects.filter(cart__id=i['cart']['id'],
                                                              cart_product__id=i['cart_product']['id']).delete()
                            msg = {
                                'is_success': True,
                                'message': [''],
                                'response_data': serializer.data,
                                'is_shop_time_entered': False}
                        else:
                            msg = {
                                'is_success': True,
                                'message': [''],
                                'response_data': serializer.data,
                                'is_shop_time_entered': False}

                    return Response(msg, status=status.HTTP_200_OK)
                else:
                    reserved_args = json.dumps({
                        'shop_id': parent_mapping.parent.id,
                        'transaction_id': cart.cart_no,
                        'products': products_available,
                        'transaction_type': 'reserved'
                    })
                    OrderManagement.create_reserved_order(reserved_args)
            serializer = CartSerializer(cart, context={
                'parent_mapping_id': parent_mapping.parent.id,
                'buyer_shop_id': shop_id})

            for i in serializer.data['rt_cart_list']:
                if i['cart_product']['price_details']['mrp'] == False:
                    i['qty'] = 0
                    i['cart_product']['product_mrp'] = 0
                    CartProductMapping.objects.filter(cart__id=i['cart']['id'],
                                                      cart_product__id=i['cart_product']['id']).delete()
                    msg = {
                        'is_success': True,
                        'message': [''],
                        'response_data': serializer.data,
                        'is_shop_time_entered': hasattr(parent_mapping.retailer, 'shop_timing'),
                    }
                else:
                    msg = {
                        'is_success': True,
                        'message': [''],
                        'response_data': serializer.data,
                        'is_shop_time_entered': hasattr(parent_mapping.retailer, 'shop_timing'),
                    }

            return Response(msg, status=status.HTTP_200_OK)
        else:
            msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                   'response_data': None, 'is_shop_time_entered': False}
            return Response(msg, status=status.HTTP_200_OK)

    def update_coupon_usage(self, cart, cart_product, retailer_shop):
        if cart.offers:
            array = list(filter(lambda d: d['sub_type'] in 'discount_on_product', cart.offers))
            if len(array) is 0:
                pass
            else:
                for i in array:
                    if cart_product.cart_product.id == i['item_id']:
                        customer_coupon_usage = CusotmerCouponUsage(coupon_id=i['coupon_id'], cart=cart)
                        customer_coupon_usage.shop = retailer_shop
                        customer_coupon_usage.product = cart_product.cart_product
                        customer_coupon_usage.times_used += 1
                        customer_coupon_usage.save()
        elif cart.cart_offers:
            product_offer = cart.cart_offers.filter(cart_item=cart_product, sub_type=CartOffers.DISCOUNT_ON_PRODUCT).last()
            if product_offer:
                customer_coupon_usage = CusotmerCouponUsage(coupon_id=product_offer.coupon_id, cart=cart)
                customer_coupon_usage.shop = retailer_shop
                customer_coupon_usage.product = cart_product.cart_product
                customer_coupon_usage.times_used += 1
                customer_coupon_usage.save()

    # def sp_mapping_order_reserve(self):
    #     pass
    # def gf_mapping_order_reserve(self):
    #     pass


class OrderPaymentStatus(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    """
        allowed updates to order status
    """

    def put(self, request, *args, **kwargs):
        """
            allowed updates to order status
        """
        app_type = self.request.META.get('HTTP_APP_TYPE', '3')
        if app_type == '3':
            return self.put_ecom_payment_status(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    @check_pos_shop
    def put_ecom_payment_status(self, request, *args, **kwargs):
        """
            Update ecom order status
        """
        with transaction.atomic():
            # Check if order exists
            try:
                order = Order.objects.select_for_update().get(pk=kwargs['pk'],
                                                              seller_shop=kwargs['shop'],
                                                              ordered_cart__cart_type__in=['ECOM'])
            except ObjectDoesNotExist:
                return api_response('Order Not Found!')

            payment_status = self.request.data.get('payment_status')
            if payment_status not in [0, 1]:
                return api_response("Please Provide A Valid Status To Update Order")

            if order.order_status == Order.PAYMENT_PENDING:
                pass


class OrderCentral(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
            Get Order Details
            Inputs
            app_type
            order_id
        """
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        # app_type = request.GET.get('cart_type', '1')
        if app_type == '1':
            return self.get_retail_order()
        elif app_type == '2':
            return self.get_basic_order(request, *args, **kwargs)
        elif app_type == '3':
            return self.get_ecom_order(request, *args, **kwargs)
        elif app_type == '4':
            return self.get_superstore_order(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    def put(self, request, *args, **kwargs):
        """
            allowed updates to order status
        """
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        # app_type = request.data.get('cart_type', '1')
        if app_type == '1':

            # return self.put_retail_order(kwargs['pk'])
            return api_response(["Sorry! Order cannot be cancelled from the APP"])

        elif app_type == '2':
            return self.put_basic_order(request, *args, **kwargs)
        elif app_type == '3':
            return self.put_ecom_order(request, *args, **kwargs)
        elif app_type == '4':
            return self.put_superstore_order(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    @check_pos_shop
    def put_basic_order(self, request, *args, **kwargs):
        """
            Update pos/ecom order
        """
        response = None
        with transaction.atomic():
            # Check if order exists
            try:
                order = Order.objects.select_for_update().get(pk=kwargs['pk'],
                                                              seller_shop=kwargs['shop'],
                                                              ordered_cart__cart_type__in=['BASIC', 'ECOM'])
            except ObjectDoesNotExist:
                return api_response('Order Not Found!')
            # check input status validity
            allowed_updates = [Order.CANCELLED, Order.OUT_FOR_DELIVERY, Order.DELIVERED, Order.CLOSED]
            order_status = self.request.data.get('status')
            if order_status not in allowed_updates:
                return api_response("Please Provide A Valid Status To Update Order")
            # CANCEL ORDER
            if order_status == Order.CANCELLED:
                user_type = PosShopUserMapping.objects.filter(shop=kwargs['shop'], user=self.request.user). \
                    last().user_type
                flag = False
                if user_type == 'manager':
                    flag = True
                elif user_type == 'store_manager':
                    flag = True
                # elif user_type == 'cashier':
                #     flag = True
                if not flag:
                    return api_response('You are not authorised to make this change!')

                cart_products = CartProductMapping.objects.filter(cart=order.ordered_cart)
                if order.ordered_cart.cart_type == 'BASIC':
                    # Unprocessed orders can be cancelled
                    # if order.order_status != Order.ORDERED:
                    #     return api_response('This order cannot be cancelled!')

                    # # cancel shipment pos order
                    # ordered_product = OrderedProduct.objects.filter(order=order).last()
                    # ordered_product.shipment_status = 'CANCELLED'
                    # ordered_product.last_modified_by = self.request.user
                    # ordered_product.save()
                    # # Update inventory
                    # for cp in cart_products:
                    #     PosInventoryCls.order_inventory(cp.retailer_product.id, PosInventoryState.SHIPPED,
                    #                                     PosInventoryState.AVAILABLE, cp.qty, self.request.user,
                    #                                     order.order_no, PosInventoryChange.CANCELLED)
                    return api_response('Offline Orders cannot be cancelled from pos app.')
                else:
                    # delivered orders can not be cancelled
                    if order.order_status == Order.DELIVERED:
                        return api_response('This order cannot be cancelled!')

                    # Update inventory
                    for cp in cart_products:
                        PosInventoryCls.order_inventory(cp.retailer_product.id, PosInventoryState.ORDERED,
                                                        PosInventoryState.AVAILABLE, cp.qty, self.request.user,
                                                        order.order_no, PosInventoryChange.CANCELLED)

                # update order status
                order.cancellation_reason = request.data.get('cancellation_reason')
                # print(order)
                order.order_status = order_status
                order.last_modified_by = self.request.user
                order.save()
                try:
                    trxn_id = order.ordered_cart
                    payment_datails = PosPayment.objects.filter(order=order.id, transaction_id=trxn_id,
                                                                payment_type__type='online',
                                                                order__ordered_cart__cart_type='ECOM').first()
                    if payment_datails:
                        refund_amount = payment_datails.amount
                        payment_id = payment_datails.payment_id
                        response = send_request_refund(payment_id, refund_amount)
                        request_id = response.get('request_id')
                        if response.get('status'):
                            request_id = response.get('request_id')
                            payment_datails.is_refund = True
                            payment_datails.refund_status = 'queued'
                            payment_datails.request_id = request_id
                            payment_datails.refund_amount = refund_amount
                            payment_datails.save()
                except  Exception as e:
                    pass
                # Refund redeemed loyalty points
                # Deduct loyalty points awarded on order
                points_credit, points_debit, net_points = RewardCls.adjust_points_on_return_cancel(
                    order.ordered_cart.redeem_points, order.buyer, order.order_no, 'order_cancel_credit',
                    'order_cancel_debit', self.request.user, 0, order.order_no)
                order_number = order.order_no
                shop_name = order.seller_shop.shop_name
                phone_number = order.buyer.phone_number
                # whatsapp api call for order cancellation
                whatsapp_order_cancel.delay(order_number, shop_name, phone_number, points_credit, points_debit,
                                            net_points)
            # Generate invoice
            elif order_status == Order.OUT_FOR_DELIVERY:
                if order.ordered_cart.cart_type != 'ECOM':
                    return api_response("Invalid action")
                if order.order_status != Order.PICKUP_CREATED:
                    return api_response("This order is not picked yet or is already out for delivery")
                try:
                    delivery_person = User.objects.get(id=self.request.data.get('delivery_person'))
                except:
                    return api_response("Please select a delivery person")
                order.order_status = Order.OUT_FOR_DELIVERY
                order.delivery_person = delivery_person
                ###### trip me save created
                order.save()
                shipment = OrderedProduct.objects.filter(order=order).last()
                shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
                shipment.save()
                shipment.shipment_status = 'OUT_FOR_DELIVERY'
                shipment.save()
                if shipment.pos_trips.filter(trip_type='ECOM').exists():
                    pos_trip = shipment.pos_trips.filter(trip_type='ECOM').last()
                else:
                    pos_trip = PosTrip.objects.create(trip_type='ECOM',
                                                      shipment=shipment)
                pos_trip.trip_start_at = datetime.now()
                pos_trip.save()
                # Inventory move from ordered to picked
                ordered_products = ShipmentProducts.objects.filter(ordered_product=shipment)
                for product_map in ordered_products:
                    product_id = product_map.retailer_product_id
                    if product_map.shipped_qty > 0:
                        PosInventoryCls.order_inventory(product_id, PosInventoryState.ORDERED,
                                                        PosInventoryState.SHIPPED,
                                                        product_map.shipped_qty,
                                                        self.request.user, order.order_no, PosInventoryChange.SHIPPED)
                    ordered_p = CartProductMapping.objects.get(cart=order.ordered_cart,
                                                               retailer_product=product_map.retailer_product,
                                                               product_type=product_map.product_type)
                    if ordered_p.qty - product_map.shipped_qty > 0:
                        PosInventoryCls.order_inventory(product_id, PosInventoryState.ORDERED,
                                                        PosInventoryState.AVAILABLE,
                                                        ordered_p.qty - product_map.shipped_qty,
                                                        self.request.user, order.order_no, PosInventoryChange.SHIPPED)
                pdf_generation_retailer(request, order.id)

                # Send Dispatch Push Notification to ECOMM USER
                info_logger.info("Sending Dispatch notifications to Ecom users......")
                message_title = "Order Update!"
                message_body = "Your order has been dispatched & will be delivered to you soon."
                send_notification_ecom_user(order, message_title, message_body)
            # Delivered/Closed
            else:
                if order.delivery_option == '1':
                    data = {'order_id': order.id,
                            'products': []}
                    for i in CartProductMapping.objects.filter(cart=order.ordered_cart, product_type=1):
                        data['products'].append({'product_id': i.retailer_product_id,
                                                 'picked_qty': i.qty})
                    order_shipment(request, data, *args, **kwargs)
                    order_pickup_genrate_invioce(request, order)
                elif order.order_status not in [Order.OUT_FOR_DELIVERY, Order.DELIVERED]:
                    return api_response("Invalid Order update")
                order.order_status = order_status
                order.last_modified_by = self.request.user
                if order.order_status == Order.DELIVERED:
                    coupon_point_update(order, self.request.user)
                if order_status == Order.DELIVERED:
                    shop = kwargs['shop']
                    if ReferralCode.is_marketing_user(order.buyer):
                        order.points_added = order_loyalty_points_credit(order.order_amount, order.buyer.id,
                                                                         order.order_no,
                                                                         'order_credit', 'order_indirect_credit',
                                                                         self.request.user.id, order.seller_shop,
                                                                         app_type="ECOM")
                order.save()
                if order_status == Order.DELIVERED:
                    whatsapp_order_delivered(order.order_no, shop.shop_name, order.buyer.phone_number,
                                             order.points_added, shop.enable_loyalty_points)
                try:
                    shipment = OrderedProduct.objects.filter(order=order).last()
                    shipment.shipment_status = order_status
                    shipment.save()
                    shipment.rt_order_product_order_product_mapping.update(delivered_qty=F('shipped_qty'))
                    if shipment.pos_trips.filter(trip_type='ECOM').exists():
                        pos_trip = shipment.pos_trips.filter(trip_type='ECOM').last()
                    else:
                        pos_trip = PosTrip.objects.create(trip_type='ECOM',
                                                          shipment=shipment)
                    pos_trip.trip_end_at = datetime.now()
                    pos_trip.save()
                except:
                    pass

        return api_response("Order updated successfully!", response, status.HTTP_200_OK, True)

    @check_ecom_user
    def put_ecom_order(self, request, *args, **kwargs):
        """
            Customer Cancel ecom order
        """
        with transaction.atomic():
            # Check if order exists
            try:
                order = Order.objects.select_for_update().get(pk=kwargs['pk'], ordered_cart__cart_type='ECOM',
                                                              buyer=self.request.user)
            except ObjectDoesNotExist:
                return api_response('Order Not Found!')

            # Unprocessed orders can be cancelled
            if order.order_status != Order.ORDERED:
                return api_response('This order cannot be cancelled!')

            cart_products = CartProductMapping.objects.filter(cart=order.ordered_cart)
            # Update inventory
            for cp in cart_products:
                PosInventoryCls.order_inventory(cp.retailer_product.id, PosInventoryState.ORDERED,
                                                PosInventoryState.AVAILABLE, cp.qty, self.request.user,
                                                order.order_no, PosInventoryChange.CANCELLED)

            # update order status
            order.order_status = Order.CANCELLED
            order.last_modified_by = self.request.user
            order.save()
            # Refund redeemed loyalty points
            # Deduct loyalty points awarded on order
            points_credit, points_debit, net_points = RewardCls.adjust_points_on_return_cancel(
                order.ordered_cart.redeem_points, order.buyer, order.order_no, 'order_cancel_credit',
                'order_cancel_debit', self.request.user, 0, order.order_no)
            order_number = order.order_no
            shop_name = order.seller_shop.shop_name
            phone_number = order.buyer.phone_number
            # whatsapp api call for order cancellation
            whatsapp_order_cancel.delay(order_number, shop_name, phone_number, points_credit, points_debit,
                                        net_points)
            response = None
            try:
                trxn_id = order.ordered_cart
                payment_datails = PosPayment.objects.filter(order=order.id, transaction_id=trxn_id,
                                                            payment_type__type='online',
                                                            order__ordered_cart__cart_type='ECOM').first()
                if payment_datails:
                    refund_amount = payment_datails.amount
                    payment_id = payment_datails.payment_id
                    response = send_request_refund(payment_id, refund_amount)
                    request_id = response.get('request_id')
                    if response.get('status'):
                        request_id = response.get('request_id')
                        payment_datails.is_refund = True
                        payment_datails.refund_status = 'queued'
                        payment_datails.request_id = request_id
                        payment_datails.refund_amount = refund_amount
                        payment_datails.save()
            except Exception as e:
                pass
        return api_response("Order cancelled successfully!", response, status.HTTP_200_OK, True)

    @check_pos_shop
    def put_superstore_order(self, request, *args, **kwargs):
        """
            update status for super store type orders
        """
        with transaction.atomic():
            response = None
            try:
                order_product_mapping = OrderedProductMapping.objects.select_for_update().get(pk=kwargs['pk'],
                                                                                              ordered_product__order__seller_shop=
                                                                                              kwargs['shop'],
                                                                                              ordered_product__order__ordered_cart__cart_type='SUPERSTORE')
                shipment = order_product_mapping.ordered_product
            except OrderedProductMapping.DoesNotExist:
                return api_response("Order not found")

            order_status = self.request.data.get('status')
            allowed_status = [OrderedProduct.OUT_FOR_DELIVERY, OrderedProduct.DELIVERED, ReturnOrder.RETURN_REQUESTED,
                              ReturnOrder.RETURN_INITIATED, ReturnOrder.CUSTOMER_ITEM_PICKED]
            if order_status not in allowed_status:
                return api_response("Please Provide valid status for order updation")
            if order_status == OrderedProduct.OUT_FOR_DELIVERY:
                retail_delivery_check = True
                if shipment.order.delivery_option == '1':
                    return api_response("Self pick up orders cannot be marked as out for delivered")

                if not retail_delivery_check:
                    return api_response(
                        "Order cannot be marked as out for delivery as product is not delivered to your shop.")
                try:
                    delivery_person = User.objects.get(id=self.request.data.get('delivery_person'))
                except:
                    return api_response("Please select a delivery person")

                shipment.delivery_person = delivery_person
                # invoice no generation
                shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
                shipment.save()
                shipment.shipment_status = order_status
                shipment.save()
                if shipment.pos_trips.filter(trip_type='SUPERSTORE').exists():
                    pos_trip = shipment.pos_trips.filter(trip_type='SUPERSTORE').last()
                else:
                    pos_trip = PosTrip.objects.create(trip_type='SUPERSTORE',
                                                      shipment=shipment)
                pos_trip.trip_start_at = datetime.now()
                pos_trip.save()
                sms_out_for_delivery(shipment.order.buyer.first_name, shipment.order.buyer.phone_number)
                # Send Dispatch Push Notification to ECOMM USER
                info_logger.info("Sending Dispatch notifications to Ecom users......")
                message_title = "Order Update!"
                message_body = "Your order has been dispatched & will be delivered to you soon."
                send_notification_ecom_user(shipment.order, message_title, message_body)
            elif order_status == OrderedProduct.DELIVERED:
                if shipment.order.delivery_option == '1':
                    shipment.shipment_status = order_status
                    shipment.save()
                    order_product_mapping.delivered_qty = order_product_mapping.shipped_qty
                    order_product_mapping.save()
                    if shipment.pos_trips.filter(trip_type='SUPERSTORE').exists():
                        pos_trip = shipment.pos_trips.filter(trip_type='SUPERSTORE').last()
                    else:
                        pos_trip = PosTrip.objects.create(trip_type='SUPERSTORE',
                                                          shipment=shipment)
                    pos_trip.trip_start_at = datetime.now()
                    pos_trip.trip_end_at = datetime.now()
                    pos_trip.save()
                else:
                    shipment.shipment_status = order_status
                    shipment.save()
                    order_product_mapping.delivered_qty = order_product_mapping.shipped_qty
                    order_product_mapping.save()
                    if shipment.pos_trips.filter(trip_type='SUPERSTORE').exists():
                        pos_trip = shipment.pos_trips.filter(trip_type='SUPERSTORE').last()
                    else:
                        pos_trip = PosTrip.objects.create(trip_type='SUPERSTORE',
                                                          shipment=shipment)
                    pos_trip.trip_end_at = datetime.now()
                    pos_trip.save()
                    order = shipment.order
                    order.order_status = 'delivered'
                    order.save()
                    sms_order_delivered(shipment.order.buyer.first_name, shipment.order.buyer.phone_number)
            elif order_status == ReturnOrder.RETURN_REQUESTED:
                if not shipment.shipment_status == OrderedProduct.DELIVERED:
                    return api_response('Products can only be returned after they are delivered.')
                if shipment.is_returned:
                    return api_response('A return has already been requested for the product.')
                pos_trip = shipment.pos_trips.filter(trip_type='SUPERSTORE').last()
                if pos_trip:
                    return_period_offset = get_config('superstore_order_return_window_buffer', 72)
                    return_window = pos_trip.trip_end_at + timedelta(hours=return_period_offset)
                    if return_window < datetime.now():
                        return api_response("Return window is over you cannot return the item now.")
                else:
                    return api_response("Return window is over you cannot return the item now.")
                return_reason = request.data.get('return_reason')
                if not return_reason:
                    return api_response('Please provide a reason for return.')
                other_return_reason = request.data.get('other_return_reason')
                if return_reason == ReturnOrder.OTHER and not other_return_reason:
                    return api_response('Please provide a brief reason for return.')
                return_pickup_method = request.data.get('return_method')
                if not return_pickup_method:
                    return api_response('Please provide a pick up method for return.')
                return_qty = int(request.data.get('return_qty'))
                if not return_qty:
                    return api_response('Please provide return quantity of the item.')
                if return_qty > order_product_mapping.delivered_qty:
                    return api_response('Return quantity cannot be more than delivered quantity')
                images = request.data.getlist('return_images', None)
                return_order = self.create_return_order(shipment,
                                                        order_product_mapping,
                                                        return_reason,
                                                        other_return_reason,
                                                        return_pickup_method,
                                                        kwargs['shop'],
                                                        return_qty,
                                                        images=images)
                if return_pickup_method == ReturnOrder.DROP_AT_STORE:
                    address = shipment.order.seller_shop.shop_name_address_mapping.filter(
                        address_type='shipping').last()
                    shop_name = shipment.order.seller_shop.shop_name
                    return_item_drop(shipment.order.buyer.first_name, shipment.order.buyer.phone_number, address, shop_name)
                else:
                    return_item_home_pickup(shipment.order.buyer.first_name, shipment.order.buyer.phone_number)
                shipment.is_returned = True
                shipment.save()
                return api_response("Return requested successfully", response, status.HTTP_200_OK, True)
            elif order_status == ReturnOrder.RETURN_INITIATED:
                try:
                    return_order = ReturnOrder.objects.select_for_update().get(
                        shipment=shipment,
                        seller_shop=kwargs['shop'],
                        buyer=self.request.user,
                        return_status=ReturnOrder.RETURN_REQUESTED
                    )
                    if not return_order.return_status == ReturnOrder.RETURN_REQUESTED:
                        return api_response("Pick up can only be assigned for return requested order")
                    if not return_order.return_pickup_method == ReturnOrder.HOME_PICKUP:
                        return api_response("Pick up for order can only be assigned for home pickup")
                    try:
                        return_pickup_person = User.objects.get(id=self.request.data.get('return_pickup_person'))
                    except:
                        return api_response("Please select a Pick up person")
                    return_order.return_status = ReturnOrder.RETURN_INITIATED
                    return_order.return_item_pickup_person = return_pickup_person
                    return_order.save()
                    info_logger.info("Sending Order Return notifications to Ecom users......")
                    message_title = "Return Update!"
                    message_body = "Our logistic partner will contact you shortly, please keep the parcel ready to return."
                    send_notification_ecom_user(return_order, message_title, message_body)
                    return api_response("Pick up person assigned", None, status.HTTP_200_OK, True)
                except ReturnOrder.DoesNotExist:
                    return api_response("Return Order not Found")
            elif order_status == ReturnOrder.CUSTOMER_ITEM_PICKED:
                try:
                    return_order = ReturnOrder.objects.select_for_update().get(
                        shipment=shipment,
                        seller_shop=kwargs['shop'],
                        buyer=self.request.user
                    )
                    if return_order.return_status == ReturnOrder.CUSTOMER_ITEM_PICKED:
                        return api_response("Return order is already picked up.")
                    if return_order.return_pickup_method == ReturnOrder.HOME_PICKUP and \
                            not return_order.return_status == ReturnOrder.RETURN_INITIATED:
                        return api_response("Pick up boy not assigned for home pick up.")
                    return_order.return_status = ReturnOrder.CUSTOMER_ITEM_PICKED
                    return_order.save()
                    self.create_retailer_side_return_order(shipment, order_product_mapping, return_order)
                    return api_response("Return product picked up", None, status.HTTP_200_OK, True)
                except ReturnOrder.DoesNotExist:
                    return api_response("Return Order not found")

            return api_response("Order updated successfully!", response, status.HTTP_200_OK, True)

    def put_retail_order(self, pk):
        """
            Cancel retailer order
        """
        return api_response(["Sorry! Order cannot be cancelled from the APP"])
        try:
            order = Order.objects.get(buyer_shop__shop_owner=self.request.user, pk=pk)
        except ObjectDoesNotExist:
            return api_response(['Order is not associated with the current user'])
        if order.order_status == 'CANCELLED':
            return api_response(["This order is already cancelled!"])
        if order.order_status == Order.COMPLETED:
            return api_response(['Sorry! This order cannot be cancelled'])
        order.order_status = Order.CANCELLED
        order.last_modified_by = self.request.user
        order.save()
        return api_response(["Order Cancelled Successfully!"], None, status.HTTP_200_OK, True)

    def post(self, request, *args, **kwargs):
        """
            Place Order
            Inputs
            cart_id
            app_type (retail-1 or basic-2)
                retail
                    shop_id (Buyer shop id)
                    billing_address_id
                    shipping_address_id
                    total_tax_amount
                basic
                    shop_id (Seller shop id)
        """
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        # app_type = self.request.data.get('cart_type', '1')
        if app_type == '1':
            return self.post_retail_order()
        elif app_type == '2':
            return self.post_pos_order(request, *args, **kwargs)
        elif app_type == '3':
            return self.post_ecom_order(request, *args, **kwargs)
        elif app_type == '4':
            return self.post_superstore_order(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    def get_retail_order(self):
        """
            Get Order
            For retail cart
        """
        # basic validations for inputs
        initial_validation = self.get_retail_validate()
        if 'error' in initial_validation:
            return api_response([initial_validation['error']], None, status.HTTP_200_OK)
        parent_mapping = initial_validation['parent_mapping']
        shop_type = initial_validation['shop_type']
        order = initial_validation['order']
        if shop_type == 'sp':
            return api_response(['Order'], self.get_serialize_process_sp(order, parent_mapping), status.HTTP_200_OK,
                                True)
        elif shop_type == 'gf':
            return api_response(['Order'], self.get_serialize_process_gf(order, parent_mapping), status.HTTP_200_OK,
                                True)
        else:
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None,
                                status.HTTP_200_OK)

    @check_pos_shop
    def get_basic_order(self, request, *args, **kwargs):
        """
            Get Order
            For Basic Cart
        """
        order = Order.objects.filter(pk=self.request.GET.get('order_id'), seller_shop=kwargs['shop']).last()
        if order:
            if order.ordered_cart.cart_type == 'BASIC':
                return api_response('Order', self.get_serialize_process_basic(order), status.HTTP_200_OK, True,
                                    extra_params={"key_p": str(config('PAYU_KEY'))})
            elif order.ordered_cart.cart_type == 'ECOM':
                return api_response('Order', self.get_serialize_process_pos_ecom(order), status.HTTP_200_OK, True,
                                    extra_params={"key_p": str(config('PAYU_KEY'))})
        return api_response("Order not found")

    @check_ecom_user
    def get_ecom_order(self, request, *args, **kwargs):
        """
            Get Order
            For Basic Cart
        """
        try:
            order = Order.objects.get(pk=self.request.GET.get('order_id'),
                                      buyer=self.request.user, ordered_cart__cart_type='ECOM')
        except ObjectDoesNotExist:
            return api_response("Order Not Found!")

        return api_response('Order', self.get_serialize_process_pos_ecom(order), status.HTTP_200_OK, True,
                            extra_params={"key_p": str(config('PAYU_KEY')), }
                            )

    @check_ecom_user
    def get_superstore_order(self, request, *args, **kwargs):
        """
            Get Order
            For SuperStore Cart
        """
        try:
            order = OrderedProductMapping.objects.get(pk=self.request.GET.get('product_mapping_id'),
                                                      ordered_product__order__ordered_cart__cart_type='SUPERSTORE')
        except OrderedProductMapping.DoesNotExist:
            return api_response("Order Not Found!")

        return api_response('Order', self.get_serialize_process_superstore(order), status.HTTP_200_OK, True,
                            extra_params={"key_p": str(config('PAYU_KEY')), }
                            )

    def post_retail_order(self):
        """
            Place Order
            For retail cart
        """
        # basic validations for inputs
        initial_validation = self.post_retail_validate()
        if 'error' in initial_validation:
            return api_response([initial_validation['error']], None, status.HTTP_200_OK)
        parent_mapping = initial_validation['parent_mapping']
        shop_type = initial_validation['shop_type']
        billing_address = initial_validation['billing_add']
        shipping_address = initial_validation['shipping_add']

        user = self.request.user
        cart_id = self.request.data.get('cart_id')

        # If Seller Shop is sp Type
        if shop_type == 'sp':
            with transaction.atomic():
                # Check If Cart Exists
                if Cart.objects.filter(last_modified_by=user, buyer_shop=parent_mapping.retailer,
                                       id=cart_id).exists():
                    cart = Cart.objects.get(last_modified_by=user, buyer_shop=parent_mapping.retailer,
                                            id=cart_id)
                    # Check and Remove if any product is blocked for audit
                    self.remove_audit_products(cart, parent_mapping)
                    # Check products mrp and update cart mapping accordingly to ordered
                    cart_resp = self.update_cart_retail_sp(cart, parent_mapping)
                    if not cart_resp['is_success']:
                        return api_response([cart_resp['message']], None, status.HTTP_200_OK)
                    # Check capping
                    order_capping_check = self.retail_capping_check(cart, parent_mapping)
                    if not order_capping_check['is_success']:
                        return api_response([order_capping_check['message']], None, status.HTTP_200_OK)
                    # Get Order Reserved data and process order
                    order_reserve_obj = self.get_reserve_retail_sp(cart, parent_mapping)
                    if order_reserve_obj:
                        # Create Order
                        order = self.create_retail_order_sp(cart, parent_mapping, billing_address, shipping_address)
                        # Release blocking
                        if self.update_ordered_reserve_sp(cart, parent_mapping, order) is False:
                            order.delete()
                            return api_response(['No item in this cart.'], None, status.HTTP_200_OK)
                        # Serialize and return response
                        return api_response(['Ordered Successfully!'],
                                            self.post_serialize_process_sp(order, parent_mapping), status.HTTP_200_OK,
                                            True)
                    # Order reserve not found
                    else:
                        return api_response(['Sorry! your session has timed out.'], None, status.HTTP_200_OK)
        # If Seller Shop is sp Type
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            # Check If Cart Exists
            if GramMappedCart.objects.filter(last_modified_by=user, id=cart_id).exists():
                cart = GramMappedCart.objects.get(last_modified_by=user, id=cart_id)
                # Update cart to ordered
                self.update_cart_retail_gf(cart)
                if GramOrderedProductReserved.objects.filter(cart=cart).exists():
                    # Create order
                    order = self.create_retail_order_gf(cart, parent_mapping, billing_address, shipping_address)
                    # Update picklist with order
                    self.picklist_update_gf(cart, order)
                    # Update reserve to ordered
                    self.update_ordered_reserve_gf(cart)
                    # Serialize and return response
                    return api_response(['Ordered Successfully!'],
                                        self.post_serialize_process_gf(order, parent_mapping), status.HTTP_200_OK, True)
                else:
                    return api_response(['Available Quantity Is None'], None, status.HTTP_200_OK)
        # Shop type neither sp nor gf
        else:
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None,
                                status.HTTP_200_OK)

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post_pos_order(self, request, *args, **kwargs):
        """
            Place Order
            For basic cart
        """
        shop = kwargs['shop']
        self.shop = shop
        with transaction.atomic():
            # basic validations for inputs
            initial_validation = self.post_basic_validate(shop)
            if 'error' in initial_validation:
                e_code = initial_validation['error_code'] if 'error_code' in initial_validation else None
                extra_params = {'error_code': e_code} if e_code else {}
                return api_response(initial_validation['error'], None, status.HTTP_406_NOT_ACCEPTABLE, False,
                                    extra_params)
            elif 'api_response' in initial_validation:
                return initial_validation['api_response']
            cart = initial_validation['cart']
            payments = initial_validation['payments']
            transaction_id = self.request.data.get('transaction_id', None)

            # Update Cart To Ordered
            self.update_cart_basic(cart)
            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, cart.redeem_points, shop=kwargs['shop'])
            order = self.create_basic_order(cart, shop)
            self.auto_process_order(order, payments, 'pos', transaction_id)
            obj = Order.objects.get(id=order.id)
            obj.order_amount = round(obj.order_amount)
            obj.save()
            shipment = self.auto_process_pos_order(order)
            if shipment.shipment_status == 'FULLY_DELIVERED_AND_VERIFIED':
                coupon_point_update(order, self.request.user)
            if ReferralCode.is_marketing_user(order.buyer) and str(order.buyer.phone_number) != '9999999999':
                order.points_added = order_loyalty_points_credit(order.order_amount, order.buyer.id, order.order_no,
                                                                 'order_credit', 'order_indirect_credit',
                                                                 self.request.user.id, order.seller_shop,
                                                                 app_type="POS")

            return api_response('Ordered Successfully!', BasicOrderListSerializer(Order.objects.get(id=order.id)).data,
                                status.HTTP_200_OK, True)

    @check_pos_shop
    @transaction.atomic
    def post_ecom_order(self, request, *args, **kwargs):
        """
            Place Order
            For ecom cart
        """
        shop = kwargs['shop']
        self.shop = shop
        if not shop.online_inventory_enabled:
            return api_response("Franchise Shop Is Not Online Enabled!")

        if not self.request.data.get('address_id'):
            return api_response("Please select an address to place order")
        try:
            address = EcomAddress.objects.get(id=self.request.data.get('address_id'), user=self.request.user)
        except:
            return api_response("Invalid Address Id")

        if address.pincode != shop.shop_name_address_mapping.filter(
                address_type='shipping').last().pincode_link.pincode:
            return api_response("This Shop is not serviceable at your delivery address")

        cart = Cart.objects.filter(cart_type='ECOM', buyer=self.request.user, seller_shop=shop,
                                   cart_status='active').last()

        if not cart:
            return api_response("Please add items to proceed to order")

        try:
            payment_type_id = PaymentType.objects.get(id=self.request.data.get('payment_type', 4)).id
        except:
            return api_response("Invalid Payment Method")

        if not payment_type_id == 4:
            if not self.request.data.get('payment_status'):
                return api_response("Please provide online payment status.")
            if not any(self.request.data.get('payment_status') in i for i in PosPayment.PAYMENT_STATUS):
                return api_response("Please provide valid online payment status")

        # Minimum Order Value
        # order_config = GlobalConfig.objects.filter(key='ecom_minimum_order_amount').last()
        # order_config = get_config_fofo_shop('Minimum order value', shop.id)
        fofo_config = get_config_fofo_shops(shop)
        order_config = get_config_fofo_shop('Minimum_Order_Value', shop.id)
        # order_config = fofo_config.get('min_order_value',None)
        # order_config = order_config if order_config else GlobalConfig.objects.filter(key='ecom_minimum_order_amount').last().value
        if order_config is not None:
            order_amount = cart.order_amount_after_discount
            if order_amount < order_config:
                return api_response(
                    "A minimum total purchase amount of {} is required to checkout.".format(order_config),
                    None, status.HTTP_200_OK, False)

        # Check day order count
        order_config = GlobalConfig.objects.filter(key='ecom_order_count').last()
        if order_config.value is not None:
            order_count = Order.objects.filter(ecom_address_order__isnull=False, created_at__date=datetime.today(),
                                               seller_shop=shop,
                                               ordered_cart__cart_type='ECOM').exclude(
                order_status='CANCELLED').distinct().count()
            if order_count >= order_config.value:
                return api_response('Because of the current surge in orders, we are not taking any more orders for '
                                    'today. We will start taking orders again tomorrow. We regret the inconvenience '
                                    'caused to you')

        # check inventory
        cart_products = cart.rt_cart_list.all()
        cart_products = PosCartCls.refresh_prices(cart_products)
        if shop.online_inventory_enabled:
            out_of_stock_items = PosCartCls.out_of_stock_items(cart_products,
                                                               self.request.data.get("remove_unavailable"))
            if out_of_stock_items:
                return api_response("Few items in your cart are not available.", out_of_stock_items, status.HTTP_200_OK,
                                    False, {'error_code': error_code.OUT_OF_STOCK_ITEMS})

        if not CartProductMapping.objects.filter(cart=cart).exists():
            return api_response("No items added to cart yet")

        # check for product is_deleted
        deleted_product = PosCartCls.product_deleled(cart_products, self.request.data.get("remove_deleted"))
        if deleted_product:
            return api_response("Few items in your cart are not available.", deleted_product, status.HTTP_200_OK,
                                False, {'error_code': error_code.OUT_OF_STOCK_ITEMS})

        delivery_option = request.data.get('delivery_option', None)

        # Update Cart To Ordered
        get_response = self.update_cart_ecom(self.shop, cart)
        if get_response:
            return api_response(get_response)
        # Refresh redeem reward
        else:
            use_all = 1 if int(cart.redeem_points) != 0 else 0
            RewardCls.checkout_redeem_points(cart, cart.redeem_points, shop, app_type="ECOM", use_all=use_all)

            order = self.create_basic_order(cart, shop, address, payment_type_id, delivery_option)
            payments = [
                {
                    "payment_type": payment_type_id,
                    "amount": round(order.order_amount),
                    "transaction_id": "",
                    "payment_status": self.request.data.get('payment_status', None),
                    "payment_mode": self.request.data.get('payment_mode', None)
                }
            ]
            self.auto_process_order(order, payments, 'ecom', transaction_id='', shop=shop)
            self.auto_process_ecom_order(order)
            try:
                push_service = FCMNotification(api_key=config('FCM_SERVER_KEY'))
                devices = Device.objects.filter(user__in=shop.pos_shop.all().values('user__id'),
                                                is_active=True).distinct('reg_id')
                info_logger.info("Sending order placed notifications to POS users......")
                for device in devices:
                    registration_id = device.reg_id
                    message_title = f"{shop.shop_name} - Order Alert !!"
                    message_body = f"Hello, You received a new Order of Rs {int(order.order_amount)}"
                    result = push_service.notify_single_device(registration_id=registration_id,
                                                               message_title=message_title,
                                                               message_body=message_body)
                    info_logger.info(result)

                # Send Order placed Push Notification to ECOMM USER
                info_logger.info("Sending Order Placed notifications to Ecom users......")
                message_title = "Great choice!"
                message_body = "Your order has been accepted!"
                send_notification_ecom_user(order, message_title, message_body)

            except Exception as e:
                info_logger.info(e)
            if shop.enable_loyalty_points:
                msg = 'Ordered Successfully, Pep Coins will be credited after delivery!'
            else:
                msg = 'Ordered Successfully!'
            return api_response(msg, BasicOrderListSerializer(Order.objects.get(id=order.id)).data,
                                status.HTTP_200_OK, True)

    @check_ecom_user_shop
    @transaction.atomic
    def post_superstore_order(self, request, *args, **kwargs):
        shop = kwargs['shop']
        if not self.request.data.get('address_id'):
            return api_response("Please select an address to place order")
        try:
            address = EcomAddress.objects.get(id=self.request.data.get('address_id'), user=self.request.user)
        except:
            return api_response("Please provide a valid address.")

        if address.pincode != shop.shop_name_address_mapping.filter(
                address_type='shipping').last().pincode_link.pincode:
            return api_response("This Shop is not serviceable at your delivery address.")

        cart = Cart.objects.filter(cart_type='SUPERSTORE', buyer=self.request.user, seller_shop=shop,
                                   cart_status='active').last()

        if not cart:
            return api_response('Please add items in your cart to place an order.')
        parent_shop = shop.get_shop_parent
        PosCartCls.refresh_prices(cart.rt_cart_list.all(), parent_shop_id=parent_shop.id)
        order_amount = cart.order_amount_after_discount
        min_order_value = GlobalConfig.objects.get(key='min_order_value_super_store').value
        if order_amount < min_order_value:
            return api_response(
                "A minimum total purchase amount of {} is required to checkout.".format(min_order_value),
                None, status.HTTP_200_OK, False)
        # set_payment_option
        try:
            payment_type_id = PaymentType.objects.get(id=self.request.data.get('payment_type', 4)).id
        except PaymentType.DoesNotExist:
            return api_response("Please select a valid payment method.")

        # get delivery option
        delivery_option = request.data.get('delivery_option', None)
        if delivery_option == 1:
            address = shop.shop_name_address_mapping.filter(
                address_type='shipping').last()
            if not address:
                return api_response("Shipping address not present for this shop. Contact shop manager.")

        err = self.update_cart_superstore(shop, cart)
        if err:
            return api_response(err)
        else:
            use_all = 1 if int(cart.redeem_points) != 0 else 0
            RewardCls.checkout_redeem_points(cart, cart.redeem_points, shop, app_type='SUPERSTORE', use_all=None)
            order = self.create_basic_order(cart, shop, address, payment_type_id, delivery_option)
            payments = [
                {
                    "payment_type": payment_type_id,
                    "amount": round(order.order_amount),
                    "transaction_id": "",
                    "payment_status": self.request.data.get('payment_status', None),
                    "payment_mode": self.request.data.get('payment_mode', None)
                }
            ]
            self.auto_process_order(order, payments, 'superstore')
            self.process_superstore_order(order)
            sms_order_placed(order.buyer.first_name, order.buyer.phone_number)

            # Send Order placed Push Notification to ECOMM USER
            info_logger.info("Sending Order Placed notifications to Ecom users......")
            message_title = "Great choice!"
            message_body = "Your order has been accepted!"
            send_notification_ecom_user(order, message_title, message_body)
            sendemailforsuperstoreorder(order)

            msg = 'Ordered Successfully!'
            return api_response(msg, BasicOrderListSerializer(Order.objects.get(id=order.id)).data,
                                status.HTTP_200_OK, True)

    def get_retail_validate(self):
        """
            Get Order
            Input validation for cart type 'retail'
        """
        shop_id = self.request.GET.get('shop_id')
        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        shop_type = parent_mapping.parent.shop_type.shop_type
        # Check if order exists
        order = None
        try:
            if shop_type == 'sp':
                order = Order.objects.get(pk=self.request.GET.get('order_id'))
            elif shop_type == 'gf':
                order = GramMappedOrder.objects.get(pk=self.request.GET.get('order_id'))
        except ObjectDoesNotExist:
            return {'error': 'Order Not Found!'}
        return {'parent_mapping': parent_mapping, 'shop_type': shop_type, 'order': order}

    def post_retail_validate(self):
        """
            Place Order
            Input validation for cart type 'retail'
        """
        # Check if buyer shop exists
        shop_id = self.request.data.get('shop_id')
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        # Get billing address
        billing_address_id = self.request.data.get('billing_address_id')
        try:
            billing_address = Address.objects.get(id=billing_address_id)
        except ObjectDoesNotExist:
            return {'error': "Billing address not found"}
        # Get shipping address
        shipping_address_id = self.request.data.get('shipping_address_id')
        try:
            shipping_address = Address.objects.get(id=shipping_address_id)
        except ObjectDoesNotExist:
            return {'error': "Shipping address not found"}
        # Check day order count
        b_shop = parent_mapping.retailer
        b_shop_type, b_shop_sub_type = b_shop.shop_type.shop_type, b_shop.shop_type.shop_sub_type
        config_key = None
        if b_shop_type == 'r':
            config_key = 'retailer_order_count'
        elif b_shop_type == 'f' and str(b_shop_sub_type) in ['fofo', 'foco']:
            config_key = str(b_shop_sub_type) + '_order_count'
        order_config = GlobalConfig.objects.filter(key=config_key).last()
        if order_config.value is not None:
            qs = Order.objects.filter(buyer_shop__shop_type=b_shop.shop_type, created_at__date=datetime.today()
                                      ).exclude(order_status='CANCELLED')
            if (b_shop_type == 'r' and not qs.count() < order_config.value) or (b_shop_type == 'f' and qs.filter(
                    buyer_shop__shop_type__shop_sub_type=b_shop_sub_type).count() < order_config.value):
                return {'error': 'Because of the current surge in orders, we are not taking any more orders for today. '
                                 'We will start taking orders again tomorrow. We regret the inconvenience caused to you'}

        return {'parent_mapping': parent_mapping, 'shop_type': parent_mapping.parent.shop_type.shop_type,
                'billing_add': billing_address, 'shipping_add': shipping_address}

    def post_basic_validate(self, shop):
        """
            Place Order
            Input validation for cart type 'basic'
        """
        # Check Billing Address
        if not shop.shop_name_address_mapping.filter(address_type='billing').exists():
            return {'error': "Shop Billing Address Doesn't Exist!"}
        # Check if cart exists
        cart_id = self.request.data.get('cart_id')
        cart = Cart.objects.select_for_update().filter(id=cart_id, seller_shop=shop, cart_type='BASIC').last()
        if not cart:
            return {'error': "Cart Doesn't Exist!"}
        elif cart.cart_status == Cart.ORDERED:
            return {'error': "Order already placed on this cart!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status == Cart.DELETED:
            return {'error': "This cart was deleted!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status not in [Cart.ACTIVE, Cart.PENDING]:
            return {'error': "Active Cart Doesn't Exist!"}
        # check buyer
        if not cart.buyer:
            if int(self.request.data.get('use_default_buyer', 0)) != 1:
                return {'error': "Buyer not found in cart!"}
        # Check if products available in cart
        cart_products = CartProductMapping.objects.select_related('retailer_product').filter(cart=cart, product_type=1)
        if cart_products.count() <= 0:
            return {'error': 'No product is available in cart'}
        # check for product is_deleted
        deleted_product = PosCartCls.product_deleled(cart_products, self.request.data.get("remove_deleted"))
        if deleted_product:
            # return {'error': 'Few items in your cart are not available.'}
            return {'api_response': api_response("Few items in your cart are not available.", deleted_product,
                                                 status.HTTP_200_OK,
                                                 False, {'error_code': error_code.OUT_OF_STOCK_ITEMS})}

        # check for discounted product availability
        if not self.discounted_product_in_stock(cart_products):
            return {'error': 'Some of the products are not in stock'}

        # Check Payment Types
        payments = self.request.data.get('payment')
        if type(payments) != list:
            return {'error': "Invalid payment format"}
        amount = 0
        cash_only = True
        for payment_method in payments:
            if 'payment_type' not in payment_method or 'amount' not in payment_method:
                return {'error': "Invalid payment format"}
            try:
                pt = PaymentType.objects.get(id=payment_method['payment_type'])
            except:
                return {'error': "Invalid Payment Type"}
            cash_only = False if pt.type != 'cash' else cash_only
            try:
                curr_amount = float(payment_method['amount'])
                if curr_amount <= 0:
                    return {'error': "Payment Amount should be greater than zero"}
                amount += curr_amount
            except:
                return {'error': "Invalid Payment Amount"}
            if "transaction_id" not in payment_method:
                payment_method['transaction_id'] = ""
            if "payment_status" not in payment_method:
                payment_method['payment_status'] = None
            if "payment_mode" not in payment_method:
                payment_method['payment_mode'] = None
        if not cash_only:
            if round(amount) != round(cart.order_amount):
                return {'error': "Total payment amount should be equal to order amount"}
        elif amount > (int(cart.order_amount) + 5) or amount < (int(cart.order_amount) - 5):
            return {'error': "Cash payment amount should be close to order amount. Please check."}

        if int(self.request.data.get('use_default_buyer', 0)) != 1:
            email = self.request.data.get('email')
            if email:
                try:
                    validators.validate_email(email)
                except:
                    return {'error': "Please provide a valid customer email"}
        return {'cart': cart, 'payments': payments}

    def retail_capping_check(self, cart, parent_mapping):
        """
            Place Order
            For retail cart
            Check capping before placing order
        """
        ordered_qty = 0
        for cart_product in cart.rt_cart_list.all():
            # to check if capping exists for warehouse and product with status active
            capping = cart_product.cart_product.get_current_shop_capping(parent_mapping.parent, parent_mapping.retailer)
            product_qty = int(cart_product.qty)
            if capping:
                cart_products = cart_product.cart_product
                msg = capping_check(capping, parent_mapping, cart_products, product_qty, ordered_qty)
                if msg[0] is False:
                    return {'is_success': False, 'message': msg[1]}
        return {'is_success': True}

    def update_cart_retail_sp(self, cart, parent_mapping):
        """
            Place Order
            For retail cart
            Check product price and change cart status to ordered
        """
        order_items = []
        # check selling price
        for i in cart.rt_cart_list.all():
            order_items.append(i.get_cart_product_price(cart.seller_shop, cart.buyer_shop))
        if len(order_items) == 0:
            CartProductMapping.objects.filter(cart__id=cart.id, cart_product_price=None).delete()
            for cart_price in cart.rt_cart_list.all():
                cart_price.cart_product_price = None
                cart_price.save()
            return {'is_success': False,
                    'message': "Some products in cart arenâ€™t available anymore, please update cart"
                               " and remove product from cart upon revisiting it"}
        else:
            cart.offers = cart.offers_applied()
            cart.cart_status = 'ordered'
            cart.buyer_shop = parent_mapping.retailer
            cart.seller_shop = parent_mapping.parent
            cart.save()
            return {'is_success': True}

    def update_cart_retail_gf(self, cart):
        """
            Place order
            Update cart to ordered
            For retail cart gf type shop
        """
        cart.cart_status = 'ordered'
        cart.save()

    def update_cart_basic(self, cart):
        """
            Place order
            Update cart to ordered
            For basic cart
        """
        if int(self.request.data.get('use_default_buyer', 0)) == 1 or cart.buyer.phone_number == '9999999999':
            phone, email, name, is_whatsapp = '9999999999', None, None, None
        else:
            phone = cart.buyer.phone_number
            email = self.request.data.get('email')
            name = self.request.data.get('name')
            is_whatsapp = self.request.data.get('is_whatsapp')
        # Check Customer - Update Or Create
        customer = update_customer_pos_cart(phone, cart.seller_shop.id, self.request.user, email, name, is_whatsapp)
        # Update customer as buyer in cart
        cart.buyer = customer
        cart.cart_status = 'ordered'
        cart.last_modified_by = self.request.user
        cart.save()

    def update_cart_ecom(self, seller_shop, cart):
        """
            Place order
            Update cart to ordered
            For ecom cart
        """
        updated_cart = Cart.objects.filter(cart_type='ECOM', buyer=self.request.user, seller_shop=seller_shop,
                                           cart_status='active').last()

        if not updated_cart:
            return "Please add items to proceed to order"
        cart.cart_status = 'ordered'
        cart.last_modified_by = self.request.user
        cart.save()

    def update_cart_superstore(self, seller_shop, cart):
        """
            Place order
            Update cart to ordered
            For ecom cart
        """
        updated_cart = Cart.objects.filter(cart_type='SUPERSTORE',
                                           buyer=self.request.user,
                                           seller_shop=seller_shop,
                                           cart_status='active').last()

        if not updated_cart:
            return "Please add items to proceed to order"
        cart.cart_status = 'ordered'
        cart.last_modified_by = self.request.user
        cart.save()

    def create_retail_order_sp(self, cart, parent_mapping, billing_address, shipping_address):
        """
            Place Order
            Create Order for retail sp type seller shop
        """
        user = self.request.user
        order, _ = Order.objects.get_or_create(last_modified_by=user, ordered_by=user, ordered_cart=cart)

        order.billing_address = billing_address
        order.shipping_address = shipping_address
        order.buyer_shop = parent_mapping.retailer
        order.seller_shop = parent_mapping.parent
        order.total_tax_amount = float(self.request.data.get('total_tax_amount', 0))
        order.order_status = Order.ORDERED
        order.save()
        return order

    def create_retail_order_gf(self, cart, parent_mapping, billing_address, shipping_address):
        """
            Place Order
            Create Order for retail gf type seller shop
        """
        user = self.request.user
        order, _ = GramMappedOrder.objects.get_or_create(last_modified_by=user,
                                                         ordered_by=user, ordered_cart=cart,
                                                         order_no=cart.order_id)

        order.billing_address = billing_address
        order.shipping_address = shipping_address
        order.buyer_shop = parent_mapping.retailer
        order.seller_shop = parent_mapping.parent
        order.order_status = 'ordered'
        order.save()
        return order

    def create_basic_order(self, cart, shop, address=None, payment_id=None, delivery_option=None):
        user = self.request.user
        order, _ = Order.objects.get_or_create(last_modified_by=user, ordered_by=user, ordered_cart=cart)
        order.buyer = cart.buyer
        order.seller_shop = shop
        order.received_by = cart.buyer
        order.order_app_type = Order.POS_WALKIN
        # order.total_tax_amount = float(self.request.data.get('total_tax_amount', 0))
        order.order_status = Order.ORDERED
        if cart.cart_type == 'ECOM':
            order.order_app_type = Order.POS_ECOMM
            if payment_id and str(PaymentType.objects.get(id=payment_id).type).lower() != 'cod':
                if self.request.data.get('payment_status') == 'payment_pending':
                    order.order_status = Order.PAYMENT_PENDING
                elif self.request.data.get('payment_status') == 'payment_failed':
                    order.order_status = Order.PAYMENT_FAILED
            order.delivery_option = delivery_option
            fofo_config = get_config_fofo_shops(shop)
            time = datetime.now().strftime("%H:%M:%S")
            time = datetime.strptime(time, "%H:%M:%S").time()
            msg = fofo_config.get('delivery_time', None)
            if msg:
                msg = str(msg) + " " + "min"
            if delivery_option and delivery_option == '1':
                msg = None
            if fofo_config.get('open_time', None) and fofo_config.get('close_time', None) and not (
                    fofo_config['open_time'] < time and fofo_config['close_time'] > time):
                msg = "Your order will be delivered tomorrow"
                if delivery_option and delivery_option == '1':
                    msg = "Please pickup your order tomorrow"

            order.estimate_delivery_time = msg
            order.latitude = self.request.data.get('latitude', None)
            order.longitude = self.request.data.get('longitude', None)

        elif cart.cart_type == 'SUPERSTORE':
            order.order_app_type = Order.POS_SUPERSTORE
            if payment_id and str(PaymentType.objects.get(id=payment_id).type).lower() != 'cod':
                if self.request.data.get('payment_status') == 'payment_pending':
                    order.order_status = Order.PAYMENT_PENDING
                elif self.request.data.get('payment_status') == 'payment_failed':
                    order.order_status = Order.PAYMENT_FAILED
            order.delivery_option = delivery_option
            delivery_buffer = get_config("superstore_delivery_buffer", 7)
            delivery_date_expected = (datetime.now() + timedelta(delivery_buffer)).date()
            order.estimate_delivery_time = delivery_date_expected
            order.latitude = self.request.data.get('latitude', None)
            order.longitude = self.request.data.get('longitude', None)

        order.save()

        if address:
            EcomOrderAddress.objects.get_or_create(order=order, address=address.address,
                                                   contact_name=address.contact_name,
                                                   contact_number=address.contact_number, latitude=address.latitude,
                                                   longitude=address.longitude, pincode=address.pincode,
                                                   state=address.state, city=address.city)
        return order

    def create_return_order(self, shipment, order_product_mapping, return_reason,
                            other_return_reason, return_pickup_method, shop, return_qty, images=None):
        user = self.request.user
        return_order, _ = ReturnOrder.objects.get_or_create(last_modified_by=user,
                                                            buyer=user,
                                                            shipment=shipment,
                                                            return_type=ReturnOrder.SUPERSTORE,
                                                            return_status=ReturnOrder.RETURN_REQUESTED)
        return_order.return_reason = return_reason
        return_order.seller_shop = shop
        return_order.return_pickup_method = return_pickup_method
        return_order.other_return_reason = other_return_reason
        return_order.save()
        return_order_product, _ = ReturnOrderProduct.objects.get_or_create(
            return_order=return_order,
            product=order_product_mapping.product,
            return_qty=return_qty,
            return_price=order_product_mapping.selling_price
        )
        if images:
            for image in images:
                ReturnOrderProductImage.objects.create(
                    return_order_product=return_order_product,
                    return_image=image
                )

    def update_ordered_reserve_sp(self, cart, parent_mapping, order):
        """
            Place Order
            For retail cart
            Release blocking once order is created
        """
        for ordered_reserve in OrderedProductReserved.objects.filter(cart=cart,
                                                                     reserve_status=OrderedProductReserved.RESERVED):
            ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
            ordered_reserve.order_product_reserved.save()
            ordered_reserve.reserve_status = OrderedProductReserved.ORDERED
            ordered_reserve.save()
        sku_id = [i.cart_product.id for i in cart.rt_cart_list.all()]
        reserved_args = json.dumps({
            'shop_id': parent_mapping.parent.id,
            'transaction_id': cart.cart_no,
            'transaction_type': 'ordered',
            'order_status': order.order_status,
            'order_number': order.order_no
        })
        order_result = OrderManagement.release_blocking_from_order(reserved_args, sku_id)
        return False if order_result is False else True

    @staticmethod
    def remove_audit_products(cart, parent_mapping):
        """
            Place Order
            Remove products with ongoing audit in shop
            For retail cart
        """
        for p in cart.rt_cart_list.all():
            is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
                                                                                    parent_mapping.parent)
            if is_blocked_for_audit:
                p.delete()

    @staticmethod
    def get_reserve_retail_sp(cart, parent_mapping):
        """
            Get Order Reserve For retail sp cart
        """
        return OrderReserveRelease.objects.filter(warehouse=parent_mapping.retailer.get_shop_parent.id,
                                                  transaction_id=cart.cart_no,
                                                  warehouse_internal_inventory_release=None).last()

    @staticmethod
    def picklist_update_gf(cart, order):
        """
            Place Order
            Update picklist with order after order creation for retail gf
        """
        pick_list = PickList.objects.get(cart=cart)
        pick_list.order = order
        pick_list.status = True
        pick_list.save()

    @staticmethod
    def update_ordered_reserve_gf(cart):
        """
            Place Order
            Update order reserve for retail gf type shop as order is created
        """
        for ordered_reserve in GramOrderedProductReserved.objects.filter(cart=cart):
            ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
            ordered_reserve.order_product_reserved.save()
            ordered_reserve.reserve_status = 'ordered'
            ordered_reserve.save()

    def get_serialize_process_sp(self, order, parent_mapping):
        """
           Get Order
           Cart type retail - sp
        """
        serializer = OrderDetailSerializer(order, context={'parent_mapping_id': parent_mapping.parent.id,
                                                           'current_url': self.request.get_host(),
                                                           'buyer_shop_id': parent_mapping.retailer.id})
        return serializer.data

    def get_serialize_process_gf(self, order, parent_mapping):
        """
           Get Order
           Cart type retail - gf
        """
        serializer = GramMappedOrderSerializer(order, context={'parent_mapping_id': parent_mapping.parent.id,
                                                               'current_url': self.request.get_host()})
        return serializer.data

    def get_serialize_process_basic(self, order):
        """
           Get Order
           Cart type basic
        """
        if int(self.request.GET.get('summary', 0)) == 1:
            return BasicOrderDetailSerializer(order).data
        return BasicOrderSerializer(order).data

    def get_serialize_process_pos_ecom(self, order):
        """
           Get Order
           Cart type Ecom
        """
        if int(self.request.GET.get('summary', 0)) == 1:
            return PosEcomOrderDetailSerializer(order).data
        return BasicOrderSerializer(order).data

    def get_serialize_process_superstore(self, order_product_mapping):
        return SuperStoreOrderDetailSerializer(order_product_mapping).data

    def post_serialize_process_sp(self, order, parent_mapping):
        """
            Place Order
            Serialize retail order for sp shop
        """
        serializer = OrderSerializer(Order.objects.get(pk=order.id),
                                     context={'parent_mapping_id': parent_mapping.parent.id,
                                              'buyer_shop_id': parent_mapping.retailer.id,
                                              'current_url': self.request.get_host()})
        return serializer.data

    def post_serialize_process_gf(self, order, parent_mapping):
        """
            Place Order
            Serialize retail order for gf shop
        """
        serializer = GramMappedOrderSerializer(order, context={'parent_mapping_id': parent_mapping.parent.id,
                                                               'current_url': self.request.get_host()})
        return serializer.data

    def post_serialize_process_basic(self, order):
        """
            Place Order
            Serialize retail order for sp shop
        """
        serializer = BasicOrderSerializer(Order.objects.get(pk=order.id),
                                          context={'current_url': self.request.get_host()})
        response = serializer.data
        return response

    def auto_process_order(self, order, payments, app_type='pos', transaction_id='', shop=None):
        """
            Auto process add payment, shipment, invoice for retailer and customer
        """
        # Redeem loyalty points
        redeem_factor = order.ordered_cart.redeem_factor
        redeem_points = order.ordered_cart.redeem_points
        if redeem_points:
            RewardCls.redeem_points_on_order(redeem_points, redeem_factor, order.buyer, self.request.user,
                                             order.order_no, shop)
        # Loyalty points credit
        # shops_str = GlobalConfig.objects.get(key=app_type + '_loyalty_shop_ids').value
        # shops_str = str(shops_str) if shops_str else ''
        # if shops_str == 'all' or (shops_str and str(order.seller_shop.id) in shops_str.split(',')):
        # Add free products
        if app_type != 'superstore':
            offers = order.ordered_cart.offers
            product_qty_map = {}
            if offers:
                for offer in offers:
                    if offer['type'] == 'combo':
                        qty = offer['free_item_qty_added']
                        product_qty_map[offer['free_item_id']] = product_qty_map[offer['free_item_id']] + qty if \
                            offer['free_item_id'] in product_qty_map else qty
                    if offer['type'] == 'free_product':
                        qty = offer['free_item_qty']
                        product_qty_map[offer['free_item_id']] = product_qty_map[offer['free_item_id']] + qty if \
                            offer['free_item_id'] in product_qty_map else qty

                for product_id in product_qty_map:
                    cart_map, _ = CartProductMapping.objects.get_or_create(cart=order.ordered_cart,
                                                                           retailer_product_id=product_id,
                                                                           product_type=0)
                    cart_map.selling_price = 0
                    cart_map.qty = product_qty_map[product_id]
                    cart_map.no_of_pieces = product_qty_map[product_id]
                    cart_map.save()
        else:
            pass
        # Create payment
        for payment in payments:
            PosPayment.objects.get_or_create(
                order=order,
                payment_type_id=payment['payment_type'],
                transaction_id=payment['transaction_id'],
                paid_by=order.buyer,
                processed_by=self.request.user,
                amount=payment['amount'],
                payment_status=payment['payment_status'],
                payment_mode=payment['payment_mode']
            )

    def auto_process_pos_order(self, order):
        # Create shipment
        shipment = OrderedProduct(order=order)
        shipment.save()
        # Create Order Items
        cart_products = CartProductMapping.objects.filter(cart_id=order.ordered_cart.id
                                                          ).values('retailer_product', 'qty', 'product_type',
                                                                   'selling_price')
        for product_map in cart_products:
            product_id = product_map['retailer_product']
            qty = product_map['qty']
            # Order Item
            ordered_product_mapping = ShipmentProducts.objects.create(ordered_product=shipment,
                                                                      retailer_product_id=product_id,
                                                                      product_type=product_map['product_type'],
                                                                      selling_price=product_map['selling_price'],
                                                                      shipped_qty=qty, picked_pieces=qty,
                                                                      delivered_qty=qty)
            # Order Item Batch
            OrderedProductBatch.objects.create(ordered_product_mapping=ordered_product_mapping, quantity=qty,
                                               pickup_quantity=qty, delivered_qty=qty, ordered_pieces=qty)
            PosInventoryCls.order_inventory(product_id, PosInventoryState.AVAILABLE, PosInventoryState.ORDERED, qty,
                                            self.request.user, order.order_no, PosInventoryChange.ORDERED)
            PosInventoryCls.order_inventory(product_id, PosInventoryState.ORDERED, PosInventoryState.SHIPPED, qty,
                                            self.request.user, order.order_no, PosInventoryChange.SHIPPED)

            mark_pos_product_online_enabled(product_id)
        # Invoice Number Generate
        shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
        shipment.save()
        # Complete Shipment
        shipment.shipment_status = 'FULLY_DELIVERED_AND_VERIFIED'
        shipment.save()
        try:
            pdf_generation_retailer(self.request, order.id)
        except Exception as e:
            logger.exception(e)
        return shipment

    def auto_process_ecom_order(self, order):

        cart_products = CartProductMapping.objects.filter(cart_id=order.ordered_cart.id
                                                          ).values('retailer_product', 'qty')
        for product_map in cart_products:
            product_id, qty = product_map['retailer_product'], product_map['qty']
            PosInventoryCls.order_inventory(product_id, PosInventoryState.AVAILABLE, PosInventoryState.ORDERED, qty,
                                            self.request.user, order.order_no, PosInventoryChange.ORDERED)

    def process_superstore_order(self, order):
        cart_products = CartProductMapping.objects.filter(cart_id=order.ordered_cart.id
                                                          ).values('cart_product', 'qty', 'product_type',
                                                                   'selling_price')
        for product in cart_products:
            shipment = OrderedProduct(order=order)
            shipment.save()
            shipment_product = ShipmentProducts.objects.create(
                ordered_product=shipment,
                product_id=product['cart_product'],
                product_type=product['product_type'],
                selling_price=product['selling_price'],
                shipped_qty=product['qty']
            )
            OrderedProductBatch.objects.create(ordered_product_mapping=shipment_product,
                                               quantity=product['qty'],
                                               pickup_quantity=product['qty'])
            # Invoice Number Generate
            shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
            shipment.save()

    def discounted_product_in_stock(self, cart_products):
        if cart_products.filter(retailer_product__sku_type=4).exists():
            discounted_cart_products = cart_products.filter(retailer_product__sku_type=4)
            for cp in discounted_cart_products:
                inventory_available = PosInventoryCls.get_available_inventory(cp.retailer_product_id,
                                                                              PosInventoryState.AVAILABLE)
                if inventory_available < cp.no_of_pieces:
                    return False
        return True

    def create_retailer_side_return_order(self, shipment, order_product_mapping, return_order):
        seller_shop = return_order.seller_shop
        parent_shop = seller_shop.get_shop_parent
        retailer_order = shipment.order.ref_order.filter(
            ordered_cart__rt_cart_list__cart_product=order_product_mapping.product).last()
        retailer_shipment = retailer_order.rt_order_order_product.last()
        ret_return_order, _ = ReturnOrder.objects.get_or_create(
            seller_shop=parent_shop,
            buyer_shop=seller_shop,
            return_status=ReturnOrder.RETURN_REQUESTED,
            shipment=retailer_shipment,
            ref_return_order=return_order,
            return_type=ReturnOrder.SUPERSTORE_WAREHOUSE
        )
        return_qty = return_order.return_order_products.last().return_qty
        return_order_product = ReturnOrderProduct.objects.get_or_create(
            return_order=ret_return_order,
            product=order_product_mapping.product,
            return_qty=return_qty,
            return_price=order_product_mapping.selling_price
        )
    # def product_deleled(self, cart_products):
    #     if cart_products.filter(retailer_product__is_deleted=True).exists():
    #         return False
    #     return True


# class CreateOrder(APIView):
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def post(self, request, *args, **kwargs):
#         order_config = GlobalConfig.objects.filter(key='order_count').last()
#         if not Order.objects.filter(created_at__date=datetime.today()).exclude(order_status='CANCELLED').count() < order_config.value:
#             msg = {'is_success': False, 'message': ['Because of the current surge in orders, we are not taking any more orders for today. We will start taking orders again tomorrow. We regret the inconvenience caused to you'], 'response_data': None}
#             return Response(msg, status=status.HTTP_200_OK)
#         else:
#             cart_id = self.request.POST.get('cart_id')
#             billing_address_id = self.request.POST.get('billing_address_id')
#             shipping_address_id = self.request.POST.get('shipping_address_id')
#
#             total_tax_amount = self.request.POST.get('total_tax_amount', 0)
#
#             shop_id = self.request.POST.get('shop_id')
#             msg = {'is_success': False, 'message': ['Have some error in shop or mapping'], 'response_data': None}
#
#             if checkNotShopAndMapping(shop_id):
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             parent_mapping = getShopMapping(shop_id)
#             if parent_mapping is None:
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             shop = getShop(shop_id)
#             if shop is None:
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             # get billing address
#             try:
#                 billing_address = Address.objects.get(id=billing_address_id)
#             except ObjectDoesNotExist:
#                 msg['message'] = ['Billing address not found']
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             # get shipping address
#             try:
#                 shipping_address = Address.objects.get(id=shipping_address_id)
#             except ObjectDoesNotExist:
#                 msg['message'] = ['Shipping address not found']
#                 return Response(msg, status=status.HTTP_200_OK)
#
#             current_url = request.get_host()
#             # if shop mapped with sp
#             if parent_mapping.parent.shop_type.shop_type == 'sp':
#                 ordered_qty = 0
#                 # self.sp_mapping_order_reserve()
#                 with transaction.atomic():
#                     if Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
#                                            id=cart_id).exists():
#                         cart = Cart.objects.get(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
#                                                 id=cart_id)
#                         # Check and remove if any product blocked for audit
#                         for p in cart.rt_cart_list.all():
#                             is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
#                                                                                                     parent_mapping.parent)
#                             if is_blocked_for_audit:
#                                 p.delete()
#
#                         orderitems = []
#                         for i in cart.rt_cart_list.all():
#                             orderitems.append(i.get_cart_product_price(cart.seller_shop, cart.buyer_shop))
#                         if len(orderitems) == 0:
#                             CartProductMapping.objects.filter(cart__id=cart.id, cart_product_price=None).delete()
#                             for cart_price in cart.rt_cart_list.all():
#                                 cart_price.cart_product_price = None
#                                 cart_price.save()
#                             msg['message'] = [
#                                 "Some products in cart arenÃ¢â‚¬â„¢t available anymore, please update cart and remove product from cart upon revisiting it"]
#                             return Response(msg, status=status.HTTP_200_OK)
#                         else:
#                             cart.cart_status = 'ordered'
#                             cart.buyer_shop = shop
#                             cart.seller_shop = parent_mapping.parent
#                             cart.save()
#
#                         for cart_product in cart.rt_cart_list.all():
#                             # to check capping is exist or not for warehouse and product with status active
#                             capping = cart_product.cart_product.get_current_shop_capping(parent_mapping.parent,
#                                                                                          parent_mapping.retailer)
#                             product_qty = int(cart_product.qty)
#                             if capping:
#                                 cart_products = cart_product.cart_product
#                                 msg = capping_check(capping, parent_mapping, cart_products, product_qty, ordered_qty)
#                                 if msg[0] is False:
#                                     msg = {'is_success': True,
#                                            'message': msg[1], 'response_data': None}
#                                     return Response(msg, status=status.HTTP_200_OK)
#                             else:
#                                 pass
#                         order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=shop.get_shop_parent.id,
#                                                                                transaction_id=cart.order_id,
#                                                                                warehouse_internal_inventory_release=None,
#                                                                                ).last()
#
#                         if order_reserve_obj:
#                             order, _ = Order.objects.get_or_create(last_modified_by=request.user, ordered_by=request.user,
#                                                                    ordered_cart=cart, order_no=cart.order_id)
#
#                             order.billing_address = billing_address
#                             order.shipping_address = shipping_address
#                             order.buyer_shop = shop
#                             order.seller_shop = parent_mapping.parent
#                             order.total_tax_amount = float(total_tax_amount)
#                             order.order_status = Order.ORDERED
#                             order.save()
#
#                             # Changes OrderedProductReserved Status
#                             for ordered_reserve in OrderedProductReserved.objects.filter(cart=cart,
#                                                                                          reserve_status=OrderedProductReserved.RESERVED):
#                                 ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
#                                 ordered_reserve.order_product_reserved.save()
#                                 ordered_reserve.reserve_status = OrderedProductReserved.ORDERED
#                                 ordered_reserve.save()
#                             sku_id = [i.cart_product.id for i in cart.rt_cart_list.all()]
#                             reserved_args = json.dumps({
#                                 'shop_id': parent_mapping.parent.id,
#                                 'transaction_id': cart.order_id,
#                                 'transaction_type': 'ordered',
#                                 'order_status': order.order_status
#                             })
#                             order_result = OrderManagement.release_blocking_from_order(reserved_args, sku_id)
#                             if order_result is False:
#                                 order.delete()
#                                 msg = {'is_success': False, 'message': ['No item in this cart.'], 'response_data': None}
#                                 return Response(msg, status=status.HTTP_200_OK)
#                             serializer = OrderSerializer(order,
#                                                          context={'parent_mapping_id': parent_mapping.parent.id,
#                                                                   'buyer_shop_id': shop_id,
#                                                                   'current_url': current_url})
#                             msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
#                             # try:
#                             #     request = jsonpickle.encode(request, unpicklable=False)
#                             #     order = jsonpickle.encode(order, unpicklable=False)
#                             #     pick_list_download.delay(request, order)
#                             # except:
#                             #     msg = {'is_success': False, 'message': ['Pdf is not uploaded for Order'],
#                             #            'response_data': None}
#                             #     return Response(msg, status=status.HTTP_200_OK)
#                         else:
#                             msg = {'is_success': False, 'message': ['Sorry! your session has timed out.'], 'response_data': None}
#                             return Response(msg, status=status.HTTP_200_OK)
#
#                     return Response(msg, status=status.HTTP_200_OK)
#
#
#             # if shop mapped with gf
#             elif parent_mapping.parent.shop_type.shop_type == 'gf':
#                 if GramMappedCart.objects.filter(last_modified_by=self.request.user, id=cart_id).exists():
#                     cart = GramMappedCart.objects.get(last_modified_by=self.request.user, id=cart_id)
#                     cart.cart_status = 'ordered'
#                     cart.save()
#
#                     if GramOrderedProductReserved.objects.filter(cart=cart).exists():
#                         order, _ = GramMappedOrder.objects.get_or_create(last_modified_by=request.user,
#                                                                          ordered_by=request.user, ordered_cart=cart,
#                                                                          order_no=cart.order_id)
#
#                         order.billing_address = billing_address
#                         order.shipping_address = shipping_address
#                         order.buyer_shop = shop
#                         order.seller_shop = parent_mapping.parent
#                         order.order_status = 'ordered'
#                         order.save()
#
#                         pick_list = PickList.objects.get(cart=cart)
#                         pick_list.order = order
#                         pick_list.status = True
#                         pick_list.save()
#
#                         # Remove Data From OrderedProductReserved
#                         for ordered_reserve in GramOrderedProductReserved.objects.filter(cart=cart):
#                             ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
#                             ordered_reserve.order_product_reserved.save()
#                             ordered_reserve.reserve_status = 'ordered'
#                             ordered_reserve.save()
#
#                         serializer = GramMappedOrderSerializer(order,
#                                                                context={'parent_mapping_id': parent_mapping.parent.id,
#                                                                         'current_url': current_url})
#                         msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
#                     else:
#                         msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
#                         return Response(msg, status=status.HTTP_200_OK)
#
#             else:
#                 msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
#                        'response_data': None}
#                 return Response(msg, status=status.HTTP_200_OK)
#             return Response(msg, status=status.HTTP_200_OK)


class OrderListCentral(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    def get(self, request, *args, **kwargs):
        """
            Get Order List
            Inputs
            app_type
            shop_id
        """
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        # app_type = request.GET.get('cart_type', '1')
        if app_type == '1':
            return self.get_retail_order_list()
        elif app_type == '2':
            return self.get_basic_order_list(request, *args, **kwargs)
        elif app_type == '3':
            return self.get_ecom_order_list(request, *args, **kwargs)
        elif app_type == '4':
            return self.get_superstore_order_list(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    def get_retail_order_list(self):
        """
            Get Order
            For retail cart
        """
        # basic validations for inputs
        initial_validation = self.get_retail_validate()
        if 'error' in initial_validation:
            return api_response([initial_validation['error']], None, status.HTTP_200_OK)
        parent_mapping = initial_validation['parent_mapping']
        shop_type = initial_validation['shop_type']
        search_text = self.request.GET.get('search_text')
        order_status = self.request.GET.get('order_status')
        if shop_type == 'sp':
            qs = Order.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
            if order_status:
                qs = qs.filter(order_status=order_status)
            if search_text:
                qs = qs.filter(Q(order_no__icontains=search_text) | Q(ordered_cart__id__icontains=search_text) |
                               Q(buyer__phone_number__icontains=search_text))
            return api_response(['Order'], self.get_serialize_process_sp(qs, parent_mapping), status.HTTP_200_OK, True)
        elif shop_type == 'gf':
            qs = GramMappedOrder.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
            if order_status:
                qs = qs.filter(order_status=order_status)
            if search_text:
                qs = qs.filter(Q(order_no__icontains=search_text) | Q(ordered_cart__id__icontains=search_text))
            return api_response(['Order'], self.get_serialize_process_gf(qs, parent_mapping), status.HTTP_200_OK, True)
        else:
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None,
                                status.HTTP_200_OK)

    def get_retail_validate(self):
        """
            Get Order
            Input validation for cart type 'retail'
        """
        shop_id = self.request.GET.get('shop_id')
        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        shop_type = parent_mapping.parent.shop_type.shop_type
        return {'parent_mapping': parent_mapping, 'shop_type': shop_type}

    @check_pos_shop
    def get_basic_order_list(self, request, *args, **kwargs):
        """
            Get Order
            For Basic Cart as well as
            Ecom Cart
            Cart Type 1 - Basic Cart
            Cart Type 2 - Ecom Cart
        """
        # Search, Paginate, Return Orders
        search_text = self.request.GET.get('search_text')
        order_status = self.request.GET.get('order_status')
        order_type = self.request.GET.get('order_type', 'pos')
        if order_type == 'pos':
            qs = Order.objects.select_related('buyer').filter(seller_shop=kwargs['shop'],
                                                              ordered_cart__cart_type='BASIC')
            if order_status:
                order_status_actual = ORDER_STATUS_MAP.get(int(order_status), None)
                qs = qs.filter(order_status=order_status_actual) if order_status_actual else qs
        elif order_type == 'ecom':
            qs = Order.objects.select_related('buyer').filter(seller_shop=kwargs['shop'],
                                                              ordered_cart__cart_type='ECOM')
            if PosShopUserMapping.objects.get(shop=kwargs['shop'], user=self.request.user).user_type == \
                    'delivery_person' or int(self.request.GET.get('self_assigned', '0')):
                qs = qs.filter(delivery_person=self.request.user)
            if order_status:
                order_status_actual = ONLINE_ORDER_STATUS_MAP.get(int(order_status), None)
                qs = qs.filter(order_status__in=order_status_actual) if order_status_actual else qs
        else:
            return api_response("Invalid cart type")
        if search_text:
            qs = qs.filter(Q(order_no__icontains=search_text) |
                           Q(buyer__first_name__icontains=search_text) |
                           Q(buyer__phone_number__icontains=search_text))
        return api_response('Order', self.get_serialize_process_basic(qs), status.HTTP_200_OK, True,
                            extra_params={"key_p": str(config('PAYU_KEY'))})

    @check_ecom_user
    def get_ecom_order_list(self, request, *args, **kwargs):
        # Search, Paginate, Return Orders
        order_status = self.request.GET.get('order_status')
        qs = Order.objects.filter(ordered_cart__cart_type='ECOM', buyer=self.request.user)

        if order_status:
            order_status_actual = ECOM_ORDER_STATUS_MAP.get(int(order_status), None)
            qs = qs.filter(order_status__in=order_status_actual) if order_status_actual else qs
        search_text = self.request.GET.get('search_text')
        if search_text:
            qs = qs.filter(Q(order_no__icontains=search_text) |
                           Q(ordered_cart__rt_cart_list__retailer_product__name__icontains=search_text))

        return api_response('Order', self.get_serialize_process_ecom(qs), status.HTTP_200_OK, True,
                            extra_params={"key_p": str(config('PAYU_KEY'))})

    @check_ecom_user
    def get_superstore_order_list(self, request, *args, **kwargs):
        shop = self.request.META.get('HTTP_SHOP_ID')
        list_type = self.request.query_params.get('list_type')
        order_status = self.request.GET.get('order_status')
        if list_type == 'pos':
            if not shop:
                return api_response("Provide shop id in api header")
            orders = Order.objects.filter(ordered_cart__cart_type='SUPERSTORE',
                                          seller_shop_id=shop)
            if order_status:
                order_status_actual = ONLINE_ORDER_STATUS_MAP.get(int(order_status), None)
                if order_status == '2':
                    orders = orders.filter(
                        rt_order_order_product__shipment_status__in=[OrderedProduct.DELIVERED]).exclude(
                        rt_order_order_product__is_returned=True
                    )
                elif order_status == '1':
                    orders = orders.filter(order_status__in=order_status_actual).exclude(
                        rt_order_order_product__shipment_status__in=[OrderedProduct.DELIVERED]
                    )
                elif order_status == '3':
                    orders = orders.filter(rt_order_order_product__is_returned=True)
                else:
                    orders = orders.none()
        else:
            orders = Order.objects.filter(ordered_cart__cart_type='SUPERSTORE',
                                          buyer=self.request.user)
            if order_status:
                order_status_actual = ECOM_ORDER_STATUS_MAP.get(int(order_status), None)
                if order_status == '1':
                    orders = orders
                elif order_status == '2':
                    orders = orders.filter(order_status__in=[Order.ORDERED,
                                                             Order.PAYMENT_FAILED,
                                                             Order.PAYMENT_PENDING]).exclude(
                        rt_order_order_product__shipment_status__in=[OrderedProduct.DELIVERED]
                    )
                elif order_status == '3':
                    orders = orders.filter(
                        rt_order_order_product__shipment_status__in=[OrderedProduct.DELIVERED]).exclude(
                        rt_order_order_product__is_returned=True)
                elif order_status == '4':
                    orders = orders.filter(rt_order_order_product__is_returned=True)
                else:
                    orders = orders.none()
        search_text = self.request.GET.get('search_text')
        if search_text:
            orders = orders.filter(Q(order_no__icontains=search_text) |
                                   Q(ordered_cart__rt_cart_list__retailer_product__name__icontains=search_text))
        shipment_products = ShipmentProducts.objects.filter(ordered_product__order__in=orders)
        return api_response('Order Products', self.get_serialize_process_superstore(shipment_products),
                            status.HTTP_200_OK, True,
                            extra_params={"key_p": str(config('PAYU_KEY'))})

    def get_serialize_process_sp(self, order, parent_mapping):
        """
           Get Order
           Cart type retail - sp
        """
        objects = self.pagination_class().paginate_queryset(order, self.request)
        return OrderListSerializer(objects, many=True,
                                   context={'parent_mapping_id': parent_mapping.parent.id,
                                            'current_url': self.request.get_host(),
                                            'buyer_shop_id': parent_mapping.retailer.id}).data

    def get_serialize_process_gf(self, order, parent_mapping):
        """
           Get Order
           Cart type retail - gf
        """
        objects = self.pagination_class().paginate_queryset(order, self.request)
        return GramMappedOrderSerializer(objects, many=True,
                                         context={'parent_mapping_id': parent_mapping.parent.id,
                                                  'current_url': self.request.get_host(),
                                                  'buyer_shop_id': parent_mapping.retailer.id}).data

    def get_serialize_process_basic(self, order):
        """
           Get Order
           Cart type basic
        """
        order = order.order_by('-modified_at')
        objects = self.pagination_class().paginate_queryset(order, self.request)
        return BasicOrderListSerializer(objects, many=True).data

    def get_serialize_process_ecom(self, order):
        """
           Get Order
           Cart type Ecom
        """
        order = order.order_by('-created_at')
        objects = self.pagination_class().paginate_queryset(order, self.request)
        return EcomOrderListSerializer(objects, many=True).data

    def get_serialize_process_superstore(self, ordered_product):
        """
            Get Order
            Cart type superstore
        """
        ordered_products = ordered_product.order_by('-created_at', '-ordered_product__order_id')
        objects = self.pagination_class().paginate_queryset(ordered_products, self.request)
        return SuperStoreOrderListSerializer(objects, many=True).data


class OrderedItemCentralDashBoard(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
            Get Order, Product & User Counts(Overview)
            Inputs
            app_type
            shop_id for retail(Buyer shop id)

        """
        app_type = request.META.get('HTTP_APP_TYPE', '1')
        # app_type = request.GET.get('app_type')
        if app_type == '1':
            return self.get_retail_order_overview()
        elif app_type == '2':
            return self.get_pos_ecom_order_overview(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    @check_pos_shop
    def get_pos_ecom_order_overview(self, request, *args, **kwargs):
        """
            Get Shop Name, Order, Product, & User Counts
            For Basic Cart
        """
        order = self.get_pos_ecom_orders_details(kwargs['shop'])
        return api_response('Dashboard', self.get_serialize_process(order), status.HTTP_200_OK, True)

    def get_pos_ecom_orders_details(self, shop):
        """
          Get Basic Order Overview based on filters
        """
        # products for shop
        products = RetailerProduct.objects.filter(shop=shop)
        ecom_products = products.filter(online_enabled=True)

        # orders for shop
        orders = Order.objects.prefetch_related('rt_return_order').filter(seller_shop=shop).exclude(
            order_status=Order.CANCELLED)
        # pos orders for shop
        pos_orders = orders.filter(order_app_type=Order.POS_WALKIN)
        # ecom orders for shop
        ecom_orders = orders.filter(order_app_type=Order.POS_ECOMM)

        # invoices for shop
        invoices = OrderedProduct.objects.filter(order__seller_shop=shop).filter(
            ~Q(order__ordered_cart__cart_type='ECOM',
               order__rt_payment_retailer_order__payment_type__type__iexact='cod',
               order__order_status=Order.OUT_FOR_DELIVERY)) \
            .exclude(order__order_status=Order.CANCELLED)

        # pos invoices for shop
        pos_invoices = invoices.filter(order__order_app_type=Order.POS_WALKIN)
        # ecom invoices for shop
        ecom_invoices = invoices.filter(order__order_app_type=Order.POS_ECOMM)

        # Return for shop
        returns = OrderReturn.objects.filter(order__seller_shop=shop, status='completed')
        # ECOM Return for shop
        ecom_returns = returns.filter(order__order_app_type=Order.POS_ECOMM)
        # POS Return for shop
        pos_returns = returns.filter(order__order_app_type=Order.POS_WALKIN)

        # Return Invoice for shop
        invoice_returns = CreditNote.objects.filter(order_return__order__seller_shop=shop,
                                                    order_return__status='completed')
        # ECOM Return for shop
        ecom_invoice_returns = invoice_returns.filter(order_return__order__order_app_type=Order.POS_ECOMM)
        # POS Return for shop
        pos_invoice_returns = invoice_returns.filter(order_return__order__order_app_type=Order.POS_WALKIN)

        # order status filter
        order_status = self.request.GET.get('order_status')
        if order_status:
            order_status_actual = ORDER_STATUS_MAP.get(int(order_status), None)
            orders = orders.filter(order_status=order_status_actual) if order_status_actual else orders
            pos_orders = pos_orders.filter(order_status=order_status_actual) if order_status_actual else orders
            ecom_orders = ecom_orders.filter(order_status=order_status_actual) if order_status_actual else orders

            invoices = invoices.filter(order__order_status=order_status_actual) if order_status_actual else invoices
            pos_invoices = pos_invoices.filter(order__order_status=order_status_actual) if \
                order_status_actual else invoices
            ecom_invoices = ecom_invoices.filter(order__order_status=order_status_actual) if \
                order_status_actual else invoices

        # filter for date range
        filters = int(self.request.GET.get('filters')) if self.request.GET.get('filters') else None
        today_date = datetime.today()
        if filters == 1:  # today
            products = products.filter(created_at__date=today_date)
            ecom_products = ecom_products.filter(created_at__date=today_date)
            # orders
            orders = orders.filter(created_at__date=today_date)
            pos_orders = pos_orders.filter(created_at__date=today_date)
            ecom_orders = ecom_orders.filter(created_at__date=today_date)

            # invoice
            invoices = invoices.filter(invoice__created_at__date=today_date)
            pos_invoices = pos_invoices.filter(invoice__created_at__date=today_date)
            ecom_invoices = ecom_invoices.filter(invoice__created_at__date=today_date)

            # orders returns
            returns = returns.filter(modified_at__date=today_date)
            pos_returns = pos_returns.filter(modified_at__date=today_date)
            ecom_returns = ecom_returns.filter(modified_at__date=today_date)

            # invoice returns
            invoice_returns = invoice_returns.filter(created_at__date=today_date)
            pos_invoice_returns = pos_invoice_returns.filter(created_at__date=today_date)
            ecom_invoice_returns = ecom_invoice_returns.filter(created_at__date=today_date)

        elif filters == 2:  # yesterday
            yesterday = today_date - timedelta(days=1)
            products = products.filter(created_at__date=yesterday)
            ecom_products = ecom_products.filter(created_at__date=yesterday)
            # orders
            orders = orders.filter(created_at__date=yesterday)
            pos_orders = pos_orders.filter(created_at__date=yesterday)
            ecom_orders = ecom_orders.filter(created_at__date=yesterday)

            # invoice
            invoices = invoices.filter(invoice__created_at__date=yesterday)
            pos_invoices = pos_invoices.filter(invoice__created_at__date=yesterday)
            ecom_invoices = ecom_invoices.filter(invoice__created_at__date=yesterday)

            # orders returns
            returns = returns.filter(modified_at__date=yesterday)
            pos_returns = pos_returns.filter(modified_at__date=yesterday)
            ecom_returns = ecom_returns.filter(modified_at__date=yesterday)

            # invoice returns
            invoice_returns = invoice_returns.filter(created_at__date=yesterday)
            pos_invoice_returns = pos_invoice_returns.filter(created_at__date=yesterday)
            ecom_invoice_returns = ecom_invoice_returns.filter(created_at__date=yesterday)

        elif filters == 3:  # this week
            products = products.filter(created_at__week=today_date.isocalendar()[1])
            ecom_products = ecom_products.filter(created_at__week=today_date.isocalendar()[1])
            # orders
            orders = orders.filter(created_at__week=today_date.isocalendar()[1])
            pos_orders = pos_orders.filter(created_at__week=today_date.isocalendar()[1])
            ecom_orders = ecom_orders.filter(created_at__week=today_date.isocalendar()[1])

            # invoice
            invoices = invoices.filter(invoice__created_at__week=today_date.isocalendar()[1])
            pos_invoices = pos_invoices.filter(invoice__created_at__week=today_date.isocalendar()[1])
            ecom_invoices = ecom_invoices.filter(invoice__created_at__week=today_date.isocalendar()[1])

            # orders returns
            returns = returns.filter(modified_at__week=today_date.isocalendar()[1])
            pos_returns = pos_returns.filter(modified_at__week=today_date.isocalendar()[1])
            ecom_returns = ecom_returns.filter(modified_at__week=today_date.isocalendar()[1])

            # invoice returns
            invoice_returns = invoice_returns.filter(created_at__week=today_date.isocalendar()[1])
            pos_invoice_returns = pos_invoice_returns.filter(created_at__week=today_date.isocalendar()[1])
            ecom_invoice_returns = ecom_invoice_returns.filter(created_at__week=today_date.isocalendar()[1])

        elif filters == 4:  # last week
            last_week = today_date - timedelta(weeks=1)
            products = products.filter(created_at__week=last_week.isocalendar()[1])
            ecom_products = ecom_products.filter(created_at__week=last_week.isocalendar()[1])
            # orders
            orders = orders.filter(created_at__week=last_week.isocalendar()[1])
            pos_orders = pos_orders.filter(created_at__week=last_week.isocalendar()[1])
            ecom_orders = ecom_orders.filter(created_at__week=last_week.isocalendar()[1])

            # invoice
            invoices = invoices.filter(invoice__created_at__week=last_week.isocalendar()[1])
            pos_invoices = pos_invoices.filter(invoice__created_at__week=last_week.isocalendar()[1])
            ecom_invoices = ecom_invoices.filter(invoice__created_at__week=last_week.isocalendar()[1])

            # orders returns
            returns = returns.filter(modified_at__week=last_week.isocalendar()[1])
            pos_returns = pos_returns.filter(modified_at__week=last_week.isocalendar()[1])
            ecom_returns = ecom_returns.filter(modified_at__week=last_week.isocalendar()[1])

            # invoice returns
            invoice_returns = invoice_returns.filter(created_at__week=last_week.isocalendar()[1])
            pos_invoice_returns = pos_invoice_returns.filter(created_at__week=last_week.isocalendar()[1])
            ecom_invoice_returns = ecom_invoice_returns.filter(created_at__week=last_week.isocalendar()[1])

        elif filters == 5:  # this month
            products = products.filter(created_at__month=today_date.month)
            ecom_products = ecom_products.filter(created_at__month=today_date.month)
            # orders
            orders = orders.filter(created_at__month=today_date.month)
            pos_orders = pos_orders.filter(created_at__month=today_date.month)
            ecom_orders = ecom_orders.filter(created_at__month=today_date.month)

            # invoice
            invoices = invoices.filter(invoice__created_at__month=today_date.month)
            pos_invoices = pos_invoices.filter(invoice__created_at__month=today_date.month)
            ecom_invoices = ecom_invoices.filter(invoice__created_at__month=today_date.month)

            # orders returns
            returns = returns.filter(modified_at__month=today_date.month)
            pos_returns = pos_returns.filter(modified_at__month=today_date.month)
            ecom_returns = ecom_returns.filter(modified_at__month=today_date.month)

            # invoice returns
            invoice_returns = invoice_returns.filter(created_at__month=today_date.month)
            pos_invoice_returns = pos_invoice_returns.filter(created_at__month=today_date.month)
            ecom_invoice_returns = ecom_invoice_returns.filter(created_at__month=today_date.month)

        elif filters == 6:  # last month
            last_month = today_date - timedelta(days=30)
            products = products.filter(created_at__month=last_month.month)
            ecom_products = ecom_products.filter(created_at__month=last_month.month)
            # orders
            orders = orders.filter(created_at__month=last_month.month)
            pos_orders = pos_orders.filter(created_at__month=last_month.month)
            ecom_orders = ecom_orders.filter(created_at__month=last_month.month)

            # invoice
            invoices = invoices.filter(invoice__created_at__month=last_month.month)
            pos_invoices = pos_invoices.filter(invoice__created_at__month=last_month.month)
            ecom_invoices = ecom_invoices.filter(invoice__created_at__month=last_month.month)

            # orders returns
            returns = returns.filter(modified_at__month=last_month.month)
            pos_returns = pos_returns.filter(modified_at__month=last_month.month)
            ecom_returns = ecom_returns.filter(modified_at__month=last_month.month)

            # invoice returns
            invoice_returns = invoice_returns.filter(created_at__month=last_month.month)
            pos_invoice_returns = pos_invoice_returns.filter(created_at__month=last_month.month)
            ecom_invoice_returns = ecom_invoice_returns.filter(created_at__month=last_month.month)

        elif filters == 7:  # this year
            products = products.filter(created_at__year=today_date.year)
            ecom_products = ecom_products.filter(created_at__year=today_date.year)
            # orders
            orders = orders.filter(created_at__year=today_date.year)
            pos_orders = pos_orders.filter(created_at__year=today_date.year)
            ecom_orders = ecom_orders.filter(created_at__year=today_date.year)

            # invoice
            invoices = invoices.filter(invoice__created_at__year=today_date.year)
            pos_invoices = pos_invoices.filter(invoice__created_at__year=today_date.year)
            ecom_invoices = ecom_invoices.filter(invoice__created_at__year=today_date.year)

            # orders returns
            returns = returns.filter(modified_at__year=today_date.year)
            pos_returns = pos_returns.filter(modified_at__year=today_date.year)
            ecom_returns = ecom_returns.filter(modified_at__year=today_date.year)

            # invoice returns
            invoice_returns = invoice_returns.filter(created_at__year=today_date.year)
            pos_invoice_returns = pos_invoice_returns.filter(created_at__year=today_date.year)
            ecom_invoice_returns = ecom_invoice_returns.filter(created_at__year=today_date.year)

        # Ordered Count
        total_ordered_final_amount = orders.aggregate(Sum('order_amount')).get('order_amount__sum')
        total_ordered_final_amount = total_ordered_final_amount if total_ordered_final_amount else 0
        total_refund_amount = returns.aggregate(Sum('refund_amount')).get('refund_amount__sum')

        if total_refund_amount:
            total_ordered_final_amount -= float(total_refund_amount)
        # POS Ordered Count
        pos_total_ordered_final_amount = pos_orders.aggregate(Sum('order_amount')).get('order_amount__sum')
        pos_total_ordered_final_amount = pos_total_ordered_final_amount if pos_total_ordered_final_amount else 0
        pos_total_refund_amount = pos_returns.aggregate(Sum('refund_amount')).get('refund_amount__sum')
        if pos_total_refund_amount:
            pos_total_ordered_final_amount -= float(pos_total_refund_amount)

        # ECOM Ordered Count
        ecom_total_ordered_final_amount = ecom_orders.aggregate(Sum('order_amount')).get('order_amount__sum')
        ecom_total_ordered_final_amount = ecom_total_ordered_final_amount if ecom_total_ordered_final_amount else 0
        ecom_total_refund_amount = ecom_returns.aggregate(Sum('refund_amount')).get('refund_amount__sum')
        if ecom_total_refund_amount:
            ecom_total_ordered_final_amount -= float(ecom_total_refund_amount)

        # POS Invoice Count
        pos_total_invoices_final_amount = 0
        for invoice in pos_invoices:
            pos_total_invoices_final_amount += round_half_down(invoice.invoice_amount_final)
        pos_total_invoice_refund_amount = pos_invoice_returns.aggregate(Sum('order_return__refund_amount')). \
            get('order_return__refund_amount__sum')
        if pos_total_invoice_refund_amount:
            pos_total_invoices_final_amount -= float(pos_total_invoice_refund_amount)

        # ECOM Invoice Count
        ecom_total_invoices_final_amount = 0
        for invoice in ecom_invoices:
            ecom_total_invoices_final_amount += invoice.invoice_amount_final
        ecom_total_invoice_refund_amount = ecom_invoice_returns.aggregate(Sum('order_return__refund_amount')). \
            get('order_return__refund_amount__sum')
        if ecom_total_invoice_refund_amount:
            ecom_total_invoices_final_amount -= float(ecom_total_invoice_refund_amount)

        # Invoice Count
        total_invoices_final_amount = pos_total_invoices_final_amount + ecom_total_invoices_final_amount
        # counts of order for shop_id with total_ordered_final_amount, total_invoices_final_amount  & products
        products_count = products.count()
        ecom_products_count = ecom_products.count()

        order_count = orders.count()
        invoice_count = invoices.count()

        ecom_order_count = ecom_orders.count()
        ecom_invoice_count = ecom_invoices.count()

        pos_order_count = pos_orders.count()
        pos_invoice_count = pos_invoices.count()

        overview = [{"shop_name": shop.shop_name, "orders": order_count, "products": products_count,
                     "ecom_products": ecom_products_count, "revenue": total_ordered_final_amount,
                     "ecom_order_count": ecom_order_count, "pos_order_count": pos_order_count,
                     "ecom_revenue": ecom_total_ordered_final_amount, "pos_revenue": pos_total_ordered_final_amount,
                     "invoices": invoice_count, "ecom_invoice_count": ecom_invoice_count,
                     "pos_invoice_count": pos_invoice_count, "invoice_revenue": total_invoices_final_amount,
                     "ecom_invoice_revenue": ecom_total_invoices_final_amount,
                     "pos_invoice_revenue": pos_total_invoices_final_amount}]
        return overview

    def get_retail_order_overview(self):
        """
            Get Orders, Users & Products Counts
            For retail cart
        """
        # basic validations for inputs
        initial_validation = self.get_retail_list_validate()
        if 'error' in initial_validation:
            return api_response(initial_validation['error'])
        order = initial_validation['order']
        return api_response('Dashboard', self.get_retailer_serialize_process(order), status.HTTP_200_OK, True)

    def get_retail_list_validate(self):
        """
            Get Order
            Input validation for cart type 'retail'
        """
        shop_id = self.request.GET.get('shop_id')
        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        shop_type = parent_mapping.parent.shop_type.shop_type
        # Check if order exists get a count of orders
        order = self.get_retail_orders_count(shop_type, parent_mapping)
        return {'parent_mapping': parent_mapping, 'shop_type': shop_type, 'order': order}

    def get_retail_orders_count(self, shop_type, parent_mapping):
        """
           Get Retail Order Overview based on filters
        """
        filters = self.request.GET.get('filters')
        if filters is None:
            # check if filter parameter is not provided,
            # fetch lifetime order details
            filters = ''
        if filters is not '':
            # check if filter parameter is not none convert it to int
            filters = int(filters)
        order_status = self.request.GET.get('order_status')
        today = datetime.today()

        if shop_type == 'sp':
            orders = Order.objects.filter(buyer_shop=parent_mapping.retailer)
        elif shop_type == 'gf':
            orders = GramMappedOrder.objects.filter(buyer_shop=parent_mapping.retailer)

        if order_status:
            orders = orders.filter(order_status=order_status)

        # filter by order on modified date
        if filters == 1:  # today
            # filter order, total_final_amount on modified date today
            orders = orders.filter(modified_at__date=today)

        elif filters == 2:  # yesterday
            # filter order, total_final_amount on modified date yesterday
            yesterday = today - timedelta(days=1)
            orders = orders.filter(modified_at__date=yesterday)

        elif filters == 3:  # lastweek
            # filter order, total_final_amount on modified date lastweek
            lastweek = today - timedelta(weeks=1)
            orders = orders.filter(modified_at__week=lastweek.isocalendar()[1])

        elif filters == 4:  # lastmonth
            # filter order, total_final_amount on modified date lastmonth
            lastmonth = today - timedelta(days=30)
            orders = orders.filter(modified_at__month=lastmonth.month)

        elif filters == 5:  # lastyear
            # filter order, total_final_amount on modified date lastyear
            lastyear = today - timedelta(days=365)
            orders = orders.filter(modified_at__year=lastyear.year)

        total_final_amount = 0
        for order in orders:
            # total final amount calculation
            total_final_amount += order.order_amount

        # counts of order with total_final_amount for buyer_shop
        orders = orders.count()
        order = [{"shop_name": parent_mapping.retailer.shop_name, "orders": orders,
                  "revenue": total_final_amount}]
        return order

    def get_serialize_process(self, order):
        """
           Get Overview of Orders, Users & Products
           Cart type Basic
        """
        serializer = OrderedDashBoardSerializer(order, many=True).data
        return serializer

    def get_retailer_serialize_process(self, order):
        """
           Get Overview of Orders, Users & Products
           Cart type Retail
        """
        serializer = RetailerOrderedDashBoardSerializer(order, many=True).data
        return serializer


class OrderReturns(APIView):
    """
        Place return for an order
    """

    def get(self, request, *args, **kwargs):
        try:
            order = Order.objects.get(pk=self.request.GET.get('order_id'),
                                      ordered_cart__cart_type__in=['BASIC', 'ECOM'])
        except ObjectDoesNotExist:
            return api_response("Order Not Found!")

        returns = OrderReturn.objects.filter(order=order, status='completed').order_by('-created_at')
        if returns.exists():
            data = dict()
            data['returns'] = OrderReturnGetSerializer(returns, many=True).data
            data['buyer'] = PosUserSerializer(order.buyer).data
            data['seller_shop'] = PosEcomShopSerializer(order.seller_shop).data
            return api_response("Order Returns", data, status.HTTP_200_OK, True)
        else:
            return api_response("No Returns For This Order", None, status.HTTP_200_OK, False)

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post(self, request, *args, **kwargs):
        """
            Returns for any order
            Inputs
            order_id
            return_items - dict - product_id, qty
            refund_amount
        """
        # Input validation
        initial_validation = self.post_validate(kwargs['shop'])
        if 'error' in initial_validation:
            return api_response(initial_validation['error'])
        order = initial_validation['order']
        return_items = initial_validation['return_items']
        return_reason = initial_validation['return_reason']
        ordered_product = initial_validation['ordered_product']
        with transaction.atomic():
            changed_products = []
            # map all products to combo offers in cart
            product_combo_map, cart_free_product = self.get_combo_offers(order)
            # initiate / update return for order
            order_return = self.update_return(order, return_reason)
            # To map free products to their return quantity
            free_returns = {}
            free_qty_product_map = []
            new_cart_value = 0
            # for each purchased product add/remove returns according to quantity provided
            for return_product in return_items:
                product_id = return_product['product_id']
                ordered_product_map = return_product['ordered_product_map']
                return_qty = return_product['return_qty']
                previous_ret_qty = return_product['previous_ret_qty']
                # if return quantity of product is greater than zero
                if return_qty > 0:
                    changed_products += [product_id]
                    self.return_item(order_return, ordered_product_map, return_qty)
                    if product_id in product_combo_map:
                        existing_prod_qty = ordered_product_map.shipped_qty - previous_ret_qty
                        new_prod_qty = ordered_product_map.shipped_qty - (return_qty + previous_ret_qty)
                        for offer in product_combo_map[product_id]:
                            existing_purchased_product_multiple = int(int(existing_prod_qty) / int(offer['item_qty']))
                            purchased_product_multiple = int(int(new_prod_qty) / int(offer['item_qty']))
                            existing_free_item_qty = int(
                                existing_purchased_product_multiple * int(offer['free_item_qty']))
                            new_free_item_qty = int(purchased_product_multiple * int(offer['free_item_qty']))
                            return_free_qty = existing_free_item_qty - new_free_item_qty
                            if return_free_qty > 0:
                                free_qty_product_map.append(
                                    self.get_free_item_map(product_id, offer['free_item_id'], return_free_qty))
                                free_returns = self.get_updated_free_returns(free_returns, offer['free_item_id'],
                                                                             return_free_qty)
                    new_cart_value += (
                                              ordered_product_map.shipped_qty - return_qty - previous_ret_qty) * ordered_product_map.selling_price
                else:
                    ReturnItems.objects.filter(return_id=order_return, ordered_product=ordered_product_map).delete()
                    if product_id in product_combo_map:
                        for offer in product_combo_map[product_id]:
                            free_returns = self.get_updated_free_returns(free_returns, offer['free_item_id'], 0)
                    new_cart_value += (
                                              ordered_product_map.shipped_qty - previous_ret_qty) * ordered_product_map.selling_price
            # check and update refund amount
            self.update_refund_amount(order, new_cart_value, order_return)
            # check if free product offered on order value is still valid
            free_returns, free_qty_product_map = self.check_cart_free_product(cart_free_product, free_returns,
                                                                              new_cart_value, free_qty_product_map)
            self.process_free_products(ordered_product, order_return, free_returns)
            order_return.free_qty_map = free_qty_product_map
            order_return.save()

            # Send Order Return Push Notification to ECOMM USER
            info_logger.info("Sending Order Return notifications to Ecom users......")
            message_title = "Return Update!"
            message_body = "Our logistic partner will contact you shortly, please keep the parcel ready to return."
            send_notification_ecom_user(order, message_title, message_body)

        return api_response("Order Return", BasicOrderSerializer(order, context={'current_url': self.request.get_host(),
                                                                                 'invoice': 1,
                                                                                 'changed_products': changed_products}).data,
                            status.HTTP_200_OK, True)

    def post_validate(self, shop):
        """
            Validate order return creation
        """
        return_items = self.request.data.get('return_items')
        if not return_items or type(return_items) != list:
            return {'error': "Provide return item details"}
        # check if order exists
        order_id = self.request.data.get('order_id')
        try:
            order = Order.objects.prefetch_related('rt_return_order').get(pk=order_id, seller_shop=shop)
            cart_type = order.ordered_cart.cart_type
            if (cart_type == 'BASIC' and order.order_status not in ['ordered', Order.PARTIALLY_RETURNED]) or (
                    cart_type == 'ECOM' and order.order_status not in [Order.DELIVERED, Order.PARTIALLY_RETURNED]):
                return {'error': "Order Not Valid For Return"}
        except ObjectDoesNotExist:
            return {'error': "Order Not Valid For Return"}
        # check return reason is valid
        return_reason = self.request.data.get('return_reason', '')
        if return_reason and return_reason not in dict(OrderReturn.RETURN_REASON):
            return {'error': 'Provide a valid return reason'}
        # Check return item details
        ordered_product = OrderedProduct.objects.filter(order=order).last()
        all_products = ordered_product.rt_order_product_order_product_mapping.filter(product_type=1)
        given_products = []
        for item in return_items:
            given_products += [item['product_id']]
        for prod in all_products:
            if prod.retailer_product_id not in given_products:
                return_items.append({
                    "product_id": int(prod.retailer_product_id),
                    "qty": 0
                })
                # return {'error': 'Please provide details for all purchased products'}
        modified = 0
        return_details = []
        for return_product in return_items:
            product_validate = self.validate_product(ordered_product, return_product, order.order_status)
            if 'error' in product_validate:
                return product_validate
            else:
                if product_validate['return_qty'] > 0:
                    modified = 1
                return_details.append(product_validate)
        if not modified:
            return {'error': 'Please provide Return Info for at least one item'}
        return {'order': order, 'return_reason': return_reason, 'return_items': return_details,
                'ordered_product': ordered_product}

    @staticmethod
    def update_refund_amount(order, new_cart_value, order_return):
        """
            Calculate refund amount
            Without offers applied on order
        """
        # Cart redeem points factor
        redeem_factor = order.ordered_cart.redeem_factor

        # previous returns
        prev_discount_adjusted = 0
        prev_refund_amount = 0
        prev_refund_points = 0
        if order.order_status == Order.PARTIALLY_RETURNED:
            previous_returns = order.rt_return_order.filter(status='completed')
            for ret in previous_returns:
                prev_refund_amount += ret.refund_amount if ret.refund_amount > 0 else 0
                prev_refund_points += ret.refund_points
                prev_discount_adjusted += ret.discount_adjusted
        prev_refund_points_value = round(prev_refund_points / redeem_factor, 2) if prev_refund_points else 0
        prev_refund_total = prev_refund_points_value + prev_refund_amount

        # Order values
        ordered_product = OrderedProduct.objects.filter(order=order).last()
        cart_redeem_points = order.ordered_cart.redeem_points
        redeem_value = round(cart_redeem_points / redeem_factor, 2) if cart_redeem_points else 0
        order_amount = round(ordered_product.invoice_amount_final, 2)
        order_total = round(ordered_product.invoice_amount_total, 2)
        invoice_value = ordered_product.invoice_subtotal
        discount = round(invoice_value - order_total, 2)

        # Current total refund value
        total_refund_value = round(order_total - prev_refund_total - float(new_cart_value), 2)

        if total_refund_value < 0:
            refund_amount = total_refund_value
            refund_points = 0
            discount_adjusted = order_return.return_value
        # Refund cash first, then points
        else:
            discount_adjusted = max(0, discount - prev_discount_adjusted)
            refund_amount = min(round(order_amount - prev_refund_total, 2), total_refund_value)
            refund_amount = max(refund_amount, 0)
            refund_points_value = total_refund_value - refund_amount
            refund_points = int(refund_points_value * redeem_factor)

        order_return.refund_amount = math.floor(refund_amount)
        order_return.refund_points = refund_points
        order_return.discount_adjusted = discount_adjusted
        order_return.save()

    @staticmethod
    def modify_applied_cart_offer(offer, new_cart_value):
        """
            Modify cart discount according to new cart value on returns
        """
        order_offer = {}
        if offer['sub_type'] == 'set_discount' and offer['cart_minimum_value'] <= new_cart_value:
            discount = BasicCartOffers.discount_value(offer, new_cart_value)
            offer['discount_value'] = discount
            order_offer = offer
        if offer['sub_type'] == 'spot_discount' and offer['discount_value'] <= new_cart_value:
            order_offer = offer
        return order_offer

    def check_cart_free_product(self, cart_free_product, free_returns, new_cart_value, free_qty_product_map):
        if cart_free_product:
            return_qty_cart_free_product = 0
            if cart_free_product['cart_minimum_value'] > new_cart_value:
                return_qty_cart_free_product = cart_free_product['free_item_qty']
            free_qty_product_map.append(
                self.get_free_item_map('free_product', cart_free_product['free_item_id'],
                                       return_qty_cart_free_product))
            free_returns = self.get_updated_free_returns(free_returns, cart_free_product['free_item_id'],
                                                         return_qty_cart_free_product)
        return free_returns, free_qty_product_map

    def get_combo_offers(self, order):
        """
            Get combo offers mapping with product purchased
        """
        offers = order.ordered_cart.offers
        product_combo_map = {}
        cart_free_product = {}
        if offers:
            for offer in offers:
                if offer['type'] == 'combo':
                    product_combo_map[offer['item_id']] = product_combo_map[offer['item_id']] + [offer] \
                        if offer['item_id'] in product_combo_map else [offer]
                if offer['type'] == 'free_product' and not ReturnItems.objects.filter(return_id__order=order,
                                                                                      return_id__status='completed',
                                                                                      ordered_product__product_type=0,
                                                                                      ordered_product__retailer_product=
                                                                                      offer['free_item_id']).exists():
                    cart_free_product = offer
        return product_combo_map, cart_free_product

    def get_free_item_map(self, product_id, free_item_id, qty):
        """
            Get purchased product map with free product return
        """
        return {
            'item_id': product_id,
            'free_item_id': free_item_id,
            'free_item_return_qty': qty
        }

    def get_updated_free_returns(self, free_returns, free_item_id, qty):
        """
            update free returns quantity for a free item
        """
        free_returns[free_item_id] = qty + free_returns[free_item_id] if free_item_id in free_returns else qty
        return free_returns

    def return_item(self, order_return, ordered_product_map, return_qty):
        """
            Update return for a product
        """
        return_item, _ = ReturnItems.objects.get_or_create(return_id=order_return,
                                                           ordered_product=ordered_product_map)
        return_item.return_qty = return_qty
        return_item.save()

    def update_return(self, order, return_reason):
        """
            Create/update retun for an order
        """
        order_return = OrderReturn.objects.filter(order=order, status='created').last()
        if not order_return:
            order_return = OrderReturn.objects.create(order=order, status='created')
        order_return.processed_by = self.request.user
        order_return.return_reason = return_reason
        order_return.save()
        return order_return

    def validate_product(self, ordered_product, return_product, order_status):
        """
            Validate return detail - product_id, qty, amt (refund amount) - provided for a product
        """
        # product id
        if 'product_id' not in return_product or 'qty' not in return_product:
            return {'error': "Provide product product_id, qty for each product"}
        product_id = return_product['product_id']
        qty = return_product['qty']
        if qty < 0:
            return {'error': "Provide valid qty for product {}".format(product_id)}
        # ordered product
        try:
            ordered_product_map = ShipmentProducts.objects.get(ordered_product=ordered_product, product_type=1,
                                                               retailer_product_id=product_id)
        except:
            return {'error': "{} is not a purchased product in this order".format(product_id)}

        previous_ret_qty = 0
        if order_status == Order.PARTIALLY_RETURNED:
            previous_ret_qty = ReturnItems.objects.filter(return_id__status='completed',
                                                          ordered_product=ordered_product_map).aggregate(
                qty=Sum('return_qty'))['qty']
            previous_ret_qty = previous_ret_qty if previous_ret_qty else 0

        product = ordered_product_map.retailer_product
        cart_product = CartProductMapping.objects.filter(cart=ordered_product_map.ordered_product.order.ordered_cart,
                                                         retailer_product=product).last()
        if product.product_pack_type == 'loose':
            if cart_product.qty_conversion_unit:
                qty, qty_unit = get_default_qty(cart_product.qty_conversion_unit.unit, product, qty)
            else:
                qty, qty_unit = get_default_qty(MeasurementUnit.objects.get(category=product.measurement_category,
                                                                            default=True).unit, product, qty)

        if qty + previous_ret_qty > ordered_product_map.shipped_qty:
            return {'error': "Product {} - total return qty cannot be greater than sold quantity".format(product.name)}

        return {'ordered_product_map': ordered_product_map, 'return_qty': qty, 'product_id': product_id,
                'previous_ret_qty': previous_ret_qty}

    def process_free_products(self, ordered_product, order_return, free_returns):
        """
            Process return for free products
            ordered_product
            order_return - return created on order
            free_returns - dict containing return free item qty
        """
        for free_product in free_returns:
            ordered_product_map_free = ShipmentProducts.objects.get(
                ordered_product=ordered_product,
                product_type=0,
                retailer_product_id=free_product)
            return_qty = free_returns[free_product]
            if not return_qty:
                ReturnItems.objects.filter(return_id=order_return, ordered_product=ordered_product_map_free).delete()
                continue
            free_return, _ = ReturnItems.objects.get_or_create(return_id=order_return,
                                                               ordered_product=ordered_product_map_free)
            free_return.return_qty = return_qty
            free_return.save()


class OrderReturnsCheckout(APIView):
    """
        Checkout after items return
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    # def post(self, request):
    #     """
    #         Apply Any Available Applicable Offer - Either coupon or spot discount
    #         Inputs
    #         cart_id
    #         coupon_id
    #         spot_discount
    #         is_percentage (spot discount type)
    #     """
    #     initial_validation = self.post_validate()
    #     if 'error' in initial_validation:
    #         return api_response(initial_validation['error'])
    #     order = initial_validation['order']
    #     order_return = initial_validation['order_return']
    #     # initial order amount
    #     received_amount = order.total_final_amount
    #     # refund amount according to any previous offer applied
    #     refund_amount = order_return.refund_amount
    #     applied_offers = order_return.offers
    #     discount_given = 0
    #     if applied_offers:
    #         for offer in applied_offers:
    #             if offer['coupon_type'] == 'cart' and offer['type'] == 'discount' and offer['applied']:
    #                 discount_given += offer['discount_value']
    #     # refund amount without any offer
    #     refund_amount_raw = refund_amount - discount_given
    #     # new order amount when no discount is applied
    #     current_amount = received_amount - refund_amount_raw
    #     # Check spot discount or cart offer
    #     spot_discount = self.request.data.get('spot_discount')
    #     offers_list = dict()
    #     offers_list['applied'] = False
    #     with transaction.atomic():
    #         if spot_discount:
    #             offers = BasicCartOffers.apply_spot_discount_returns(spot_discount, self.request.data.get('is_percentage'),
    #                                                                  current_amount, order_return, refund_amount_raw)
    #         else:
    #             offers = BasicCartOffers.refresh_returns_offers(order, current_amount, order_return, refund_amount_raw,
    #                                                             self.request.data.get('coupon_id'))
    #         if 'error' in offers:
    #             return api_response(offers['error'])
    #         return api_response("Applied Successfully" if offers['applied'] else "Not Applicable", self.serialize(order))

    # def post_validate(self):
    #     """
    #         Validate returns checkout offers apply
    #     """
    #     # check shop
    #     shop_id = get_shop_id_from_token(self.request.user)
    #     if not type(shop_id) == int:
    #         return {"error": shop_id}
    #     # check order
    #     order_id = self.request.data.get('order_id')
    #     try:
    #         order = Order.objects.get(pk=order_id, seller_shop_id=shop_id)
    #     except ObjectDoesNotExist:
    #         return {'error': "Order Does Not Exist"}
    #     # check if return created
    #     try:
    #         order_return = OrderReturn.objects.get(order=order, status='created')
    #     except ObjectDoesNotExist:
    #         return {'error': "Order Return Created Does Not Exist"}
    #     if not self.request.data.get('coupon_id') and not self.request.data.get('spot_discount'):
    #         return {'error': "Provide Coupon Id/Spot Discount"}
    #     if self.request.data.get('coupon_id') and self.request.data.get('spot_discount'):
    #         return {'error': "Provide either of coupon_id or spot_discount"}
    #     if self.request.data.get('spot_discount') and self.request.data.get('is_percentage') not in [0, 1]:
    #         return {'error': "Provide a valid spot discount type"}
    #     return {'order': order, 'order_return': order_return}

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
            Get Return Checkout Amount Info, Offers Applied-Applicable
        """
        # Input validation
        initial_validation = self.get_validate(kwargs['shop'])
        if 'error' in initial_validation:
            return api_response(initial_validation['error'])
        order = initial_validation['order']
        # order_return = initial_validation['order_return']
        # get available offers
        # Get coupons available on cart from es
        # initial order amount
        # received_amount = order.total_final_amount
        # refund amount according to any previous offer applied
        # refund_amount = order_return.refund_amount
        # applied_offers = order_return.offers
        # discount_given = 0
        # if applied_offers:
        #     for offer in applied_offers:
        #         if offer['coupon_type'] == 'cart' and offer['type'] == 'discount' and offer['applied']:
        #             discount_given += offer['discount_value']
        # # refund amount without any offer
        # refund_amount_raw = refund_amount - discount_given
        # # new order amount when no discount is applied
        # current_amount = received_amount - refund_amount_raw
        # with transaction.atomic():
        #     offers = BasicCartOffers.refresh_returns_offers(order, current_amount, order_return, refund_amount_raw)
        #     if 'error' in offers:
        #         return api_response(offers['error'])
        #     return api_response("Return Checkout", self.serialize(order, offers['total_offers'], offers['spot_discount']))
        return api_response("Return Checkout", self.serialize(order), status.HTTP_200_OK, True)

    def get_validate(self, shop):
        """
            Get Return Checkout
            Input validation
        """
        # check order
        order_id = self.request.GET.get('order_id')
        try:
            order = Order.objects.prefetch_related('rt_return_order').get(pk=order_id, seller_shop=shop)
            cart_type = order.ordered_cart.cart_type
            if (cart_type == 'BASIC' and order.order_status not in ['ordered', Order.PARTIALLY_RETURNED]) or (
                    cart_type == 'ECOM' and order.order_status not in [Order.DELIVERED, Order.PARTIALLY_RETURNED]):
                return {'error': "Order Not Valid For Return"}
        except ObjectDoesNotExist:
            return {'error': "Order Not Valid For Return"}
        # check if return created
        try:
            order_return = OrderReturn.objects.get(order=order, status='created')
        except ObjectDoesNotExist:
            return {'error': "Order Return Created Does Not Exist / Already Closed"}
        return {'order': order, 'order_return': order_return}

    # def delete(self, request):
    #     """
    #         Order return checkout
    #         Delete any applied offers
    #     """
    #     # Check shop
    #     shop_id = get_shop_id_from_token(self.request)
    #     if not type(shop_id) == int:
    #         return api_response("Shop Doesn't Exist!")
    #     # check order
    #     order_id = self.request.GET.get('order_id')
    #     try:
    #         order = Order.objects.get(pk=order_id, seller_shop_id=shop_id)
    #     except ObjectDoesNotExist:
    #         return api_response("Order Does Not Exist")
    #     # check if return created
    #     try:
    #         order_return = OrderReturn.objects.get(order=order)
    #     except ObjectDoesNotExist:
    #         return {'error': "Order Return Does Not Exist"}
    #     refund_amount = order_return.refund_amount
    #     applied_offers = order_return.offers
    #     discount_given = 0
    #     if applied_offers:
    #         for offer in applied_offers:
    #             if offer['coupon_type'] == 'cart' and offer['applied']:
    #                 discount_given += float(offer['discount_value'])
    #     refund_amount = refund_amount - discount_given
    #     order_return.offers = []
    #     order_return.refund_amount = refund_amount
    #     order_return.save()
    #     return api_response("Deleted Successfully", [], True)

    def serialize(self, order, offers=None, spot_discount=None):
        """
            Checkout serializer
        """
        serializer = OrderReturnCheckoutSerializer(order)
        response = serializer.data
        # if offers:
        #     response['available_offers'] = offers
        # if spot_discount:
        #     response['spot_discount'] = spot_discount
        return response


class PaymentDataView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_ecom_user_shop
    def get(self, request, *args, **kwargs):
        pass


class CartStockCheckView(APIView):

    @check_ecom_user_shop
    def get(self, request, *args, **kwargs):
        """
            Check stock qty cart
        """
        shop = kwargs['shop']
        if not shop.online_inventory_enabled:
            return api_response("Franchise Shop Is Not Online Enabled!")
        try:
            cart = Cart.objects.prefetch_related('rt_cart_list').filter(cart_type='ECOM', buyer=self.request.user,
                                                                        seller_shop=kwargs['shop'],
                                                                        cart_status='active').last()
        except ObjectDoesNotExist:
            return api_response("Cart Not Found!")

        if not self.request.GET.get('address_id'):
            return api_response("Please select an address to check stock")
        try:
            address = EcomAddress.objects.get(id=int(self.request.GET.get('address_id')), user=self.request.user)
        except:
            return api_response("Invalid Address Id")

        if address.pincode != shop.shop_name_address_mapping.filter(
                address_type='shipping').last().pincode_link.pincode:
            return api_response("This Shop is not serviceable at your delivery address")
        #
        # lattitude,longitude = self.request.GET.get('latitude'),self.request.GET.get('longitude')
        # if lattitude and longitude:
        #     lattitude = float(lattitude)
        #     longitude = float(longitude)
        # shop_lattitude,shop_longitude = get_order_location(shop)
        # order_distance = 0
        # if lattitude and longitude:
        #     order_distance = distance((shop_lattitude, shop_longitude), (lattitude, longitude))
        # delivery_redius = get_config_fofo_shop('Delivery Radius', shop.id)
        # if order_distance != 0 and delivery_redius and order_distance * 1000 > get_config_fofo_shop('Delivery Radius', shop.id):
        #     return api_response("This Shop is not serviceable at your delivery address")
        """"---------------------------------------------validation for fofo shop-----------------------------------------------"""

        time = datetime.now().strftime("%H:%M:%S")
        time = datetime.strptime(time, "%H:%M:%S").time()
        day = datetime.today().date()

        fofo_config = get_config_fofo_shops(shop)
        msg = 'Stock check completed'
        if fofo_config.get('open_time', None) and fofo_config.get('close_time', None) and not (
                fofo_config['open_time'] < time and fofo_config['close_time'] > time):
            msg = "Your Order Will Pick Up Tomorrow"
            # return api_response("Sorry for the inconvenience, order acceptable b/w {} to {}".format(fofo_config['open_time'], fofo_config['close_time']))

        start_off_day = fofo_config.get('working_off_start_date', None)
        end_off_day = fofo_config.get('working_off_end_date', start_off_day)
        if (start_off_day and end_off_day) and (start_off_day <= day and end_off_day >= day):
            return api_response(
                "Sorry for the inconvenience, Shop is non operational on {}".format(datetime.today().date()))
        # Check for changes in cart - price / offers / available inventory
        cart_products = cart.rt_cart_list.all()
        cart_products = PosCartCls.refresh_prices(cart_products)
        # Minimum Order Value
        # order_config = GlobalConfig.objects.filter(key='ecom_minimum_order_amount').last()
        # -------------------------------------------------------------------------------------------------------------------------------------#
        order_config = get_config_fofo_shop('Minimum_Order_Value', shop.id)
        # order_config = fofo_config.get('min_order_value',None)#get_config_fofo_shop('Minimum order value', shop.id)
        # order_config = order_config if order_config else GlobalConfig.objects.filter(key='ecom_minimum_order_amount').last().value
        if order_config is not None:
            order_amount = cart.order_amount_after_discount
            if order_amount < order_config:
                return api_response(
                    "A minimum total purchase amount of {} is required to checkout.".format(order_config),
                    None, status.HTTP_200_OK, False)
        """"-----------------------------------------------------------------------------------------------------------------------"""

        if shop.online_inventory_enabled:
            out_of_stock_items = PosCartCls.out_of_stock_items(cart_products)

            # Return error for out of stock items
            if out_of_stock_items and shop.online_inventory_enabled:
                return api_response("Few items in your cart are not available.", out_of_stock_items, status.HTTP_200_OK,
                                    False, {'error_code': error_code.OUT_OF_STOCK_ITEMS})

        return api_response(msg, None, status.HTTP_200_OK, True)


class OrderReturnComplete(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    """
        Complete created return on an order
    """

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post(self, request, *args, **kwargs):
        """
            Complete return on order
        """
        # check order
        order_id = self.request.data.get('order_id')
        try:
            order = Order.objects.prefetch_related('rt_return_order').get(pk=order_id, seller_shop=kwargs['shop'])
            cart_type = order.ordered_cart.cart_type
            if (cart_type == 'BASIC' and order.order_status not in ['ordered', Order.PARTIALLY_RETURNED]) or (
                    cart_type == 'ECOM' and order.order_status not in [Order.DELIVERED, Order.PARTIALLY_RETURNED]):
                return api_response("Order Not Valid For Return")
        except ObjectDoesNotExist:
            return api_response("Order Not Valid For Return")
            # return {'error': "Order Not Valid For Return"}

        # Check Payment Type
        try:
            payment_type = PaymentType.objects.get(id=self.request.data.get('refund_method'))
            refund_method = payment_type.type
        except:
            return api_response("Invalid Refund Method")

        with transaction.atomic():
            # check if return created
            try:
                order_return = OrderReturn.objects.select_for_update().get(order=order, status='created')
            except ObjectDoesNotExist:
                return api_response("Order Return Does Not Exist / Already Closed")
            # check partial or fully refunded order
            return_qty = ReturnItems.objects.filter(return_id__order=order).aggregate(return_qty=Sum('return_qty'))[
                'return_qty']

            ordered_product = OrderedProduct.objects.get(order=order)

            initial_qty = ordered_product.rt_order_product_order_product_mapping \
                .aggregate(shipped_qty=Sum('shipped_qty'))['shipped_qty']

            if initial_qty == return_qty:
                order.order_status = Order.FULLY_RETURNED
                ordered_product.shipment_status = 'FULLY_RETURNED_AND_VERIFIED'
            else:
                order.order_status = Order.PARTIALLY_RETURNED
                ordered_product.shipment_status = 'PARTIALLY_DELIVERED_AND_VERIFIED'
            ordered_product.last_modified_by = self.request.user
            ordered_product.save()
            order.last_modified_by = self.request.user
            order.save()
            # Return redeem points if any
            # Deduct order credit points based on remaining order value
            return_ids = []
            refund_amount = 0
            returns = OrderReturn.objects.filter(order=order)
            for ret in returns:
                return_ids += [ret.id]
                refund_amount += ret.refund_amount
            new_paid_amount = ordered_product.invoice_amount_final - refund_amount
            points_credit, points_debit, net_points = RewardCls.adjust_points_on_return_cancel(
                order_return.refund_points, order.buyer, order_return.id, 'order_return_credit', 'order_return_debit',
                self.request.user, new_paid_amount, order.order_no, return_ids, kwargs['shop'])
            # Update inventory
            returned_products = ReturnItems.objects.filter(return_id=order_return)
            for rp in returned_products:
                PosInventoryCls.order_inventory(rp.ordered_product.retailer_product.id, PosInventoryState.SHIPPED,
                                                PosInventoryState.AVAILABLE, rp.return_qty, self.request.user, rp.id,
                                                PosInventoryChange.RETURN)
            # complete return
            order_return.status = 'completed'
            order_return.refund_mode = refund_method
            order_return.save()
            return_count = OrderReturn.objects.filter(order=order, status='completed').count()
            credit_note_id = generate_credit_note_id(ordered_product.invoice_no, return_count)
            credit_note_instance = CreditNote.objects.create(credit_note_id=credit_note_id, order_return=order_return)
            pdf_generation_return_retailer(request, order, ordered_product, order_return, returned_products,
                                           credit_note_instance)

            # Send Return Successful Push Notification to ECOMM USER
            info_logger.info("Sending Return Successful notifications to Ecom users......")
            message_title = "Order return has been accepted."
            message_body = "You will receive a confirmation once the refund has been initiated."
            send_notification_ecom_user(order, message_title, message_body)

            return api_response("Return Completed Successfully!", OrderReturnCheckoutSerializer(order).data,
                                status.HTTP_200_OK, True)


def send_notification_ecom_user(order, message_title, message_body):
    push_service_ecom = FCMNotification(api_key=config('FCM_SERVER_KEY_ECOM'))
    user_devices = Device.objects.filter(user=order.buyer, app_type='ecom').distinct('reg_id')
    for user_device in user_devices:
        result = push_service_ecom.notify_single_device(registration_id=user_device.reg_id,
                                                        message_title=message_title, message_body=message_body)
        info_logger.info(result)


def sendemailforsuperstoreorder(order):
    subject = 'A new SuperStore order has been placed.'
    platform = 'seller' if config('ENVIRONMENT') == 'production' else config('ENVIRONMENT')
    url = 'https://{}.gramfactory.com/admin/retailer_to_sp/order/{}'.format(platform, order.id)
    body = 'Click here for more details - {}'.format(url)
    sender = GlobalConfig.objects.get(key='sender')
    receiver = GlobalConfig.objects.get(key='superstore_order_internal_email_recipient')
    info_logger.info("--------------Sending mail for superstore order!------------------")
    info_logger.info("Body :: {}".format(body))
    try:
        send_mail(
            subject,
            body,
            sender.value,
            receiver.value.split(','),
            fail_silently=False,
        )
        info_logger.info("----------Mail send successfully for superstore order!-------------")
    except Exception as e:
        info_logger.error(e)


# class OrderList(generics.ListAPIView):
#     serializer_class = OrderListSerializer
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def list(self, request):
#         user = self.request.user
#         # queryset = self.get_queryset()
#         shop_id = self.request.GET.get('shop_id')
#         msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
#
#         if checkNotShopAndMapping(shop_id):
#             return Response(msg, status=status.HTTP_200_OK)
#
#         parent_mapping = getShopMapping(shop_id)
#         if parent_mapping is None:
#             return Response(msg, status=status.HTTP_200_OK)
#
#         current_url = request.get_host()
#         if parent_mapping.parent.shop_type.shop_type == 'sp':
#             queryset = Order.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')[:10]
#             serializer = OrderListSerializer(
#                 queryset, many=True,
#                 context={'parent_mapping_id': parent_mapping.parent.id,
#                          'current_url': current_url,
#                          'buyer_shop_id': shop_id})
#         elif parent_mapping.parent.shop_type.shop_type == 'gf':
#             queryset = GramMappedOrder.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
#             serializer = GramMappedOrderSerializer(
#                 queryset, many=True,
#                 context={'parent_mapping_id': parent_mapping.parent.id,
#                          'current_url': current_url,
#                          'buyer_shop_id': shop_id})
#
#         if serializer.data:
#             msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
#         return Response(msg, status=status.HTTP_200_OK)


# class OrderDetail(generics.RetrieveAPIView):
#     serializer_class = OrderDetailSerializer
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def retrieve(self, request, *args, **kwargs):
#         pk = self.kwargs.get('pk')
#         shop_id = self.request.GET.get('shop_id')
#         msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
#
#         if checkNotShopAndMapping(shop_id):
#             return Response(msg, status=status.HTTP_200_OK)
#
#         parent_mapping = getShopMapping(shop_id)
#         if parent_mapping is None:
#             return Response(msg, status=status.HTTP_200_OK)
#
#         current_url = request.get_host()
#         if parent_mapping.parent.shop_type.shop_type == 'sp':
#             queryset = Order.objects.get(id=pk)
#             serializer = OrderDetailSerializer(
#                 queryset,
#                 context={'parent_mapping_id': parent_mapping.parent.id,
#                          'current_url': current_url,
#                          'buyer_shop_id': shop_id})
#         elif parent_mapping.parent.shop_type.shop_type == 'gf':
#             queryset = GramMappedOrder.objects.get(id=pk)
#             serializer = GramMappedOrderSerializer(queryset, context={'parent_mapping_id': parent_mapping.parent.id,
#                                                                       'current_url': current_url})
#
#         if serializer.data:
#             msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
#         return Response(msg, status=status.HTTP_200_OK)


class DownloadInvoiceSP(APIView):
    """
    This class is creating and downloading single pdf and bulk pdf along with zip for Plan Shipment, Invoice and Order
    Product
    """
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        """

        :param request: request params
        :param args: argument list
        :param kwargs: keyword argument
        :return: zip folder which contains the pdf files
        """
        # check condition for single pdf download using download invoice link
        if len(args) == ZERO:
            # get primary key
            pk = kwargs.get('pk')
            # check pk is exist or not for Order product model
            ordered_product = get_object_or_404(OrderedProduct, pk=pk)
            # call pdf generation method to generate pdf and download the pdf
            pdf_generation(request, ordered_product)
            result = requests.get(ordered_product.invoice.invoice_pdf.url)
            file_prefix = PREFIX_INVOICE_FILE_NAME
            # generate pdf file
            response = single_pdf_file(ordered_product, result, file_prefix)
            # return response
        else:
            # list of file path for every pdf file
            file_path_list = []
            # list of created date for every pdf file
            pdf_created_date = []
            for pk in args[0]:
                # check pk is exist or not for Order product model
                ordered_product = get_object_or_404(OrderedProduct, pk=pk)
                # call pdf generation method to generate and save pdf
                pdf_generation(request, ordered_product)
                # append the pdf file path
                file_path_list.append(ordered_product.invoice.invoice_pdf.url)
                # append created date for pdf file
                pdf_created_date.append(ordered_product.created_at)
            # condition to check the download file count
            if len(pdf_created_date) == 1:
                result = requests.get(ordered_product.invoice.invoice_pdf.url)
                file_prefix = PREFIX_INVOICE_FILE_NAME
                # generate pdf file
                response = single_pdf_file(ordered_product, result, file_prefix)
                return response, False
            else:
                # get merged pdf file name
                prefix_file_name = INVOICE_DOWNLOAD_ZIP_NAME
                merge_pdf_name = create_merge_pdf_name(prefix_file_name, pdf_created_date)
                # call function to merge pdf files
                response = merge_pdf_files(file_path_list, merge_pdf_name)
            return response, True
        return response


# @task
def pdf_generation(request, ordered_product):
    """
    :param request: request object
    :param ordered_product: Order product object
    :return: pdf instance
    """
    # get prefix of file name
    file_prefix = PREFIX_INVOICE_FILE_NAME
    # get the file name along with with prefix name
    filename = create_file_name(file_prefix, ordered_product, with_timestamp=True)
    # we will be changing based on shop name
    template_name = 'admin/invoice/invoice_sp.html'
    if type(request) is str:
        request = None
        ordered_product = get_object_or_404(OrderedProduct, pk=ordered_product)
    else:
        request = request
        ordered_product = ordered_product

    if ordered_product.invoice and ordered_product.invoice.invoice_pdf and ordered_product.invoice.invoice_pdf.url:
        pass
    else:
        barcode = barcodeGen(ordered_product.invoice_no)
        e_invoice_data = None
        # Check if e-invoicing is done for this order
        # and get e-invocing details
        # details include QRCode, IRN, Ack No, Ack Date
        zoho_invoice = ZohoInvoice.objects.filter(invoice_number=ordered_product.invoice_no).last()
        if zoho_invoice and zoho_invoice.e_invoice_qr_raw_data:
            try:
                qrCode = qrCodeGen(ordered_product.invoice_no, zoho_invoice.e_invoice_qr_raw_data)
                irn = zoho_invoice.e_invoice_reference_number
                ack_no = zoho_invoice.e_invoice_ack_number
                ack_date = zoho_invoice.e_invoice_ack_date

                e_invoice_data = {'qrCode': qrCode, 'irn': irn, 'ack_no': ack_no, 'ack_date': ack_date}
            except Exception as e:
                pass
        buyer_shop_id = ordered_product.order.buyer_shop_id

        # Licence
        shop_mapping = ParentRetailerMapping.objects.filter(
            retailer=ordered_product.order.ordered_cart.seller_shop).last()
        if shop_mapping:
            shop_name = shop_mapping.parent.shop_name
        else:
            shop_name = ordered_product.order.ordered_cart.seller_shop.shop_name
        license_number = getShopLicenseNumber(shop_name)
        # CIN
        cin_number = getShopCINNumber(shop_name)
        fin_year_start_dt = get_fin_year_start_date()
        paid_amount = OrderedProduct.objects.filter(order__buyer_shop_id=buyer_shop_id,
                                                    created_at__gte=fin_year_start_dt) \
            .aggregate(paid_amount=RoundAmount(Sum(
            F('rt_order_product_order_product_mapping__effective_price') *
            F('rt_order_product_order_product_mapping__shipped_qty'),
            output_field=FloatField())))['paid_amount']

        try:
            if ordered_product.order.buyer_shop.shop_timing:
                open_time = ordered_product.order.buyer_shop.shop_timing.open_timing
                close_time = ordered_product.order.buyer_shop.shop_timing.closing_timing
                if open_time == 'midnight' and close_time == 'midnight':
                    open_time = '-'
                    close_time = '-'

            else:
                open_time = '-'
                close_time = '-'
        except:
            open_time = '-'
            close_time = '-'

        seller_shop_gistin = 'unregistered'
        buyer_shop_gistin = 'unregistered'
        if ordered_product.order.ordered_cart.seller_shop.shop_name_documents.exists():
            seller_shop_gistin = ordered_product.order.ordered_cart.seller_shop.shop_name_documents.filter(
                shop_document_type='gstin').last().shop_document_number if ordered_product.order.ordered_cart.seller_shop.shop_name_documents.filter(
                shop_document_type='gstin').exists() else getGSTINNumber(shop_name)

        if ordered_product.order.ordered_cart.buyer_shop and ordered_product.order.ordered_cart.buyer_shop.shop_name_documents.exists():
            buyer_shop_gistin = ordered_product.order.ordered_cart.buyer_shop.shop_name_documents.filter(
                shop_document_type='gstin').last().shop_document_number if ordered_product.order.ordered_cart.buyer_shop.shop_name_documents.filter(
                shop_document_type='gstin').exists() else 'unregistered'

        shop_mapping_list = ShopMigrationMapp.objects.filter(
            new_sp_addistro_shop=ordered_product.order.ordered_cart.seller_shop.pk).all()
        if shop_mapping_list.exists():
            template_name = 'admin/invoice/invoice_addistro_sp.html'

        product_listing = []
        taxes_list = []
        gst_tax_list = []
        cess_tax_list = []
        surcharge_tax_list = []
        sum_qty = 0
        igst = sum(gst_tax_list)
        cgst = (sum(gst_tax_list)) / 2
        sgst = (sum(gst_tax_list)) / 2
        cess = sum(cess_tax_list)
        surcharge = sum(surcharge_tax_list)
        open_time = '-'
        close_time = '-'
        sum_qty = 0
        sum_basic_amount = 0
        shop_name_gram = 'GFDN SERVICES PVT LTD'
        nick_name_gram = '-'
        address_line1_gram = '-'
        city_gram = '-'
        state_gram = '-'
        pincode_gram = '-'
        cin = '-'
        list1 = []
        for m in ordered_product.rt_order_product_order_product_mapping.filter(shipped_qty__gt=0):
            dict1 = {}
            flag = 0
            if len(list1) > 0:
                for i in list1:
                    if i["hsn"] == m.product.product_hsn:
                        i["taxable_value"] = i["taxable_value"] + m.base_price
                        i["cgst"] = i["cgst"] + (m.base_price * m.get_products_gst()) / 200
                        i["sgst"] = i["sgst"] + (m.base_price * m.get_products_gst()) / 200
                        i["igst"] = i["igst"] + (m.base_price * m.get_products_gst()) / 100
                        i["cess"] = i["cess"] + (m.base_price * m.get_products_gst_cess_tax()) / 100
                        i["surcharge"] = i["surcharge"] + (m.base_price * m.get_products_gst_surcharge()) / 100
                        if m.product.product_special_cess is None:
                            i["product_special_cess"] = i["product_special_cess"] + 0.0
                        else:
                            i["product_special_cess"] = i["product_special_cess"] + m.total_product_cess_amount
                        i["total"] = i["total"] + m.product_tax_amount
                        flag = 1

            if flag == 0:
                dict1["hsn"] = m.product.product_hsn
                dict1["taxable_value"] = m.base_price
                dict1["cgst"] = (m.base_price * m.get_products_gst()) / 200
                dict1["cgst_rate"] = m.get_products_gst() / 2
                dict1["sgst"] = (m.base_price * m.get_products_gst()) / 200
                dict1["sgst_rate"] = m.get_products_gst() / 2
                dict1["igst"] = (m.base_price * m.get_products_gst()) / 100
                dict1["igst_rate"] = m.get_products_gst()
                dict1["cess"] = (m.base_price * m.get_products_gst_cess_tax()) / 100
                dict1["cess_rate"] = m.get_products_gst_cess_tax()
                dict1["surcharge"] = (m.base_price * m.get_products_gst_surcharge()) / 100
                dict1["product_special_cess"] = m.product.product_special_cess
                if dict1["product_special_cess"] is None:
                    dict1["product_special_cess"] = 0.0
                else:
                    dict1["product_special_cess"] = m.total_product_cess_amount
                dict1["surcharge_rate"] = m.get_products_gst_surcharge()
                dict1["total"] = m.product_tax_amount
                list1.append(dict1)

            sum_qty += m.shipped_qty
            sum_basic_amount += m.base_price
            tax_sum = 0
            basic_rate = 0
            product_tax_amount = 0
            product_pro_price_mrp = 0
            product_pro_price_ptr = 0

            no_of_pieces = 0
            cart_qty = 0
            product_tax_amount = 0
            basic_rate = 0
            inline_sum_amount = 0
            cart_product_map = ordered_product.order.ordered_cart.rt_cart_list.filter(cart_product=m.product).last()
            product_price = cart_product_map.get_cart_product_price(
                ordered_product.order.ordered_cart.seller_shop,
                ordered_product.order.ordered_cart.buyer_shop)

            if ordered_product.order.ordered_cart.cart_type != 'DISCOUNTED':
                product_pro_price_ptr = m.effective_price
            else:
                product_pro_price_ptr = cart_product_map.item_effective_prices
            if m.product.product_mrp:
                product_pro_price_mrp = m.product.product_mrp
            else:
                product_pro_price_mrp = round(product_price.mrp, 2)
            no_of_pieces = m.product.rt_cart_product_mapping.last().no_of_pieces
            cart_qty = m.product.rt_cart_product_mapping.last().qty

            # new code for tax start
            tax_sum = m.get_product_tax_json()

            get_tax_val = tax_sum / 100
            basic_rate = (float(product_pro_price_ptr)) / (float(get_tax_val) + 1)
            base_price = (float(product_pro_price_ptr) * float(m.shipped_qty)) / (float(get_tax_val) + 1)
            product_tax_amount = round(float(base_price) * float(get_tax_val), 2)
            for z in ordered_product.order.seller_shop.shop_name_address_mapping.all():
                cin = 'U74999HR2018PTC075977' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else '---'
                shop_name_gram = 'GFDN SERVICES PVT LTD' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else z.shop_name
                nick_name_gram, address_line1_gram = z.nick_name, z.address_line1
                city_gram, state_gram, pincode_gram = z.city, z.state, z.pincode

            ordered_prodcut = {
                "product_sku": m.product.product_gf_code,
                "product_short_description": m.product.product_short_description if m.product.product_type == 0 else m.product.product_short_description + " (Discounted)",
                "product_ean_code": m.product.product_ean_code,
                "product_hsn": m.product.product_hsn,
                "product_tax_percentage": "" if tax_sum == 0 else str(tax_sum) + "%",
                "product_mrp": product_pro_price_mrp,
                "shipped_qty": m.shipped_qty,
                "product_inner_case_size": m.product.product_inner_case_size,
                "product_no_of_pices": int(m.shipped_qty) * int(m.product.product_inner_case_size),
                "basic_rate": basic_rate,
                "basic_amount": float(m.shipped_qty) * float(basic_rate),
                "price_to_retailer": round(product_pro_price_ptr, 2),
                "product_sub_total": float(m.shipped_qty) * float(product_pro_price_ptr),
                "product_tax_amount": product_tax_amount
            }
            # total_tax_sum = total_tax_sum + product_tax_amount
            # inline_sum_amount = inline_sum_amount + product_pro_price_ptr
            product_listing.append(ordered_prodcut)
            # New Code For Product Listing End

            # sum_qty += int(m.shipped_qty)
            # sum_amount += int(m.shipped_qty) * product_pro_price_ptr
            inline_sum_amount += int(m.shipped_qty) * product_pro_price_ptr
            gst_tax = (m.base_price * m.get_products_gst()) / 100
            cess_tax = (m.base_price * m.get_products_gst_cess_tax()) / 100
            surcharge_tax = (m.base_price * m.get_products_gst_surcharge()) / 100
            product_special_cess = m.product.product_special_cess
            if product_special_cess is None:
                product_special_cess = 0.0
            else:
                product_special_cess = product_special_cess
            gst_tax_list.append(gst_tax)
            cess_tax_list.append(cess_tax)
            surcharge_tax_list.append(surcharge_tax)
            igst, cgst, sgst, cess, surcharge = sum(gst_tax_list), (sum(gst_tax_list)) / 2, (
                sum(gst_tax_list)) / 2, sum(
                cess_tax_list), sum(surcharge_tax_list)

        total_amount = ordered_product.invoice.invoice_sub_total
        tcs_rate = ordered_product.invoice.tcs_percent
        tcs_tax = ordered_product.invoice.tcs_amount
        total_tax_amount = ordered_product.sum_amount_tax()
        try:
            product_special_cess = round(m.total_product_cess_amount)
        except:
            product_special_cess = 0
        amount = total_amount
        total_amount = total_amount + tcs_tax
        total_amount_int = round(total_amount)
        total_tax_amount_int = round(total_tax_amount)

        amt = [num2words(i) for i in str(total_amount_int).split('.')]
        rupees = amt[0]

        tax_amt = [num2words(i) for i in str(total_tax_amount_int).split('.')]
        tax_rupees = tax_amt[0]

        logger.info("creating invoice pdf")
        logger.info(template_name)
        logger.info(request.get_host())

        data = {"shipment": ordered_product, "order": ordered_product.order,
                "url": request.get_host(), "scheme": request.is_secure() and "https" or "http",
                "igst": igst, "cgst": cgst, "sgst": sgst, "product_special_cess": product_special_cess,
                "tcs_tax": tcs_tax, "tcs_rate": tcs_rate, "cess": cess,
                "surcharge": surcharge, "total_amount": total_amount, "amount": amount,
                "barcode": barcode, "product_listing": product_listing, "rupees": rupees, "tax_rupees": tax_rupees,
                "seller_shop_gistin": seller_shop_gistin, "buyer_shop_gistin": buyer_shop_gistin,
                "open_time": open_time, "close_time": close_time, "sum_qty": sum_qty,
                "sum_basic_amount": sum_basic_amount,
                "shop_name_gram": shop_name_gram, "nick_name_gram": nick_name_gram,
                "address_line1_gram": address_line1_gram, "city_gram": city_gram, "state_gram": state_gram,
                "pincode_gram": pincode_gram, "cin": cin_number,
                "hsn_list": list1, "license_number": license_number, "e_invoice_data": e_invoice_data,
                "no_of_crate":ordered_product.shipment_packaging.filter(packaging_type='CRATE').count(),
                "no_of_box":ordered_product.shipment_packaging.filter(packaging_type='BOX').count(),
                "no_of_sack":ordered_product.shipment_packaging.filter(packaging_type='SACK').count()
                }

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)

        try:
            create_invoice_data(ordered_product)
            ordered_product.invoice.invoice_pdf.save("{}".format(filename),
                                                     ContentFile(response.rendered_content), save=True)
        except Exception as e:
            logger.exception(e)


def return_challan_generation(request, return_order_id):
    # get prefix of file name
    file_prefix = PREFIX_RETURN_CHALLAN_FILE_NAME
    # we will be changing based on shop name
    template_name = 'admin/return_order/return_invoice_sp.html'
    return_order = get_object_or_404(ReturnOrder, pk=return_order_id)
    # get the file name along with with prefix name
    if not return_order.return_challan_no:
        return_order.return_challan_no = common_function.generate_return_challan_number(return_order,
                                                                                        return_order.seller_shop.shop_name_address_mapping.filter(
                                                                                            address_type='billing').last().pk)
    filename = create_file_name(file_prefix, return_order.return_challan_no, with_timestamp=True)

    # if return_order.return_invoice and return_order.return_invoice.invoice_pdf and return_order.return_invoice.invoice_pdf.url:
    #     pass
    # else:
    barcode = barcodeGen(return_order.return_challan_no)
    e_invoice_data = None
    # Check if e-invoicing is done for this order
    # and get e-invocing details
    # details include QRCode, IRN, Ack No, Ack Date
    # zoho_invoice = ZohoInvoice.objects.filter(invoice_number=ordered_product.invoice_no).last()
    # if zoho_invoice and zoho_invoice.e_invoice_qr_raw_data:
    #     try:
    #         qrCode = qrCodeGen(ordered_product.invoice_no, zoho_invoice.e_invoice_qr_raw_data)
    #         irn = zoho_invoice.e_invoice_reference_number
    #         ack_no = zoho_invoice.e_invoice_ack_number
    #         ack_date = zoho_invoice.e_invoice_ack_date

    #         e_invoice_data = {'qrCode': qrCode, 'irn': irn, 'ack_no': ack_no, 'ack_date': ack_date}
    #     except Exception as e:
    #         pass
    buyer_shop_id = return_order.buyer_shop_id

    # Licence
    shop_mapping = ParentRetailerMapping.objects.filter(
        retailer=return_order.seller_shop).last()
    if shop_mapping:
        shop_name = shop_mapping.parent.shop_name
    else:
        shop_name = return_order.seller_shop.shop_name
    license_number = getShopLicenseNumber(shop_name)
    # CIN
    cin_number = getShopCINNumber(shop_name)
    fin_year_start_dt = get_fin_year_start_date()
    paid_amount = OrderedProduct.objects.filter(order__buyer_shop_id=buyer_shop_id,
                                                created_at__gte=fin_year_start_dt) \
        .aggregate(paid_amount=RoundAmount(Sum(
        F('rt_order_product_order_product_mapping__effective_price') *
        F('rt_order_product_order_product_mapping__shipped_qty'),
        output_field=FloatField())))['paid_amount']

    try:
        if return_order.buyer_shop.shop_timing:
            open_time = return_order.buyer_shop.shop_timing.open_timing
            close_time = return_order.buyer_shop.shop_timing.closing_timing
            if open_time == 'midnight' and close_time == 'midnight':
                open_time = '-'
                close_time = '-'

        else:
            open_time = '-'
            close_time = '-'
    except:
        open_time = '-'
        close_time = '-'

    seller_shop_gistin = 'unregistered'
    buyer_shop_gistin = 'unregistered'
    if return_order.seller_shop.shop_name_documents.exists():
        seller_shop_gistin = return_order.seller_shop.shop_name_documents.filter(
            shop_document_type='gstin').last().shop_document_number if return_order.seller_shop.shop_name_documents.filter(
            shop_document_type='gstin').exists() else getGSTINNumber(shop_name)

    if return_order.buyer_shop and return_order.buyer_shop.shop_name_documents.exists():
        buyer_shop_gistin = return_order.buyer_shop.shop_name_documents.filter(
            shop_document_type='gstin').last().shop_document_number if return_order.buyer_shop.shop_name_documents.filter(
            shop_document_type='gstin').exists() else 'unregistered'

    shipping_address = return_order.buyer_shop.shop_name_address_mapping.filter(address_type='shipping').last()
    billing_address = return_order.buyer_shop.shop_name_address_mapping.filter(address_type='billing').last()
    if not billing_address:
        billing_address = shipping_address
    product_listing = []
    taxes_list = []
    gst_tax_list = []
    cess_tax_list = []
    surcharge_tax_list = []
    sum_qty = 0
    igst = sum(gst_tax_list)
    cgst = (sum(gst_tax_list)) / 2
    sgst = (sum(gst_tax_list)) / 2
    cess = sum(cess_tax_list)
    surcharge = sum(surcharge_tax_list)
    open_time = '-'
    close_time = '-'
    sum_qty = 0
    sum_basic_amount = 0
    shop_name_gram = 'GFDN SERVICES PVT LTD'
    nick_name_gram = '-'
    address_line1_gram = '-'
    city_gram = '-'
    state_gram = '-'
    pincode_gram = '-'
    cin = '-'
    list1 = []
    for m in return_order.shipment.rt_order_product_order_product_mapping.filter(shipped_qty__gt=0):
        dict1 = {}
        flag = 0
        if len(list1) > 0:
            for i in list1:
                if i["hsn"] == m.product.product_hsn:
                    i["taxable_value"] = i["taxable_value"] + m.base_price
                    i["cgst"] = i["cgst"] + (m.base_price * m.get_products_gst()) / 200
                    i["sgst"] = i["sgst"] + (m.base_price * m.get_products_gst()) / 200
                    i["igst"] = i["igst"] + (m.base_price * m.get_products_gst()) / 100
                    i["cess"] = i["cess"] + (m.base_price * m.get_products_gst_cess_tax()) / 100
                    i["surcharge"] = i["surcharge"] + (m.base_price * m.get_products_gst_surcharge()) / 100
                    if m.product.product_special_cess is None:
                        i["product_special_cess"] = i["product_special_cess"] + 0.0
                    else:
                        i["product_special_cess"] = i["product_special_cess"] + m.total_product_cess_amount
                    i["total"] = i["total"] + m.product_tax_amount
                    flag = 1

        if flag == 0:
            dict1["hsn"] = m.product.product_hsn
            dict1["taxable_value"] = m.base_price
            dict1["cgst"] = (m.base_price * m.get_products_gst()) / 200
            dict1["cgst_rate"] = m.get_products_gst() / 2
            dict1["sgst"] = (m.base_price * m.get_products_gst()) / 200
            dict1["sgst_rate"] = m.get_products_gst() / 2
            dict1["igst"] = (m.base_price * m.get_products_gst()) / 100
            dict1["igst_rate"] = m.get_products_gst()
            dict1["cess"] = (m.base_price * m.get_products_gst_cess_tax()) / 100
            dict1["cess_rate"] = m.get_products_gst_cess_tax()
            dict1["surcharge"] = (m.base_price * m.get_products_gst_surcharge()) / 100
            dict1["product_special_cess"] = m.product.product_special_cess
            if dict1["product_special_cess"] is None:
                dict1["product_special_cess"] = 0.0
            else:
                dict1["product_special_cess"] = m.total_product_cess_amount
            dict1["surcharge_rate"] = m.get_products_gst_surcharge()
            dict1["total"] = m.product_tax_amount
            list1.append(dict1)

        sum_qty += m.shipped_qty
        sum_basic_amount += m.base_price
        tax_sum = 0
        basic_rate = 0
        product_tax_amount = 0
        product_pro_price_mrp = 0
        product_pro_price_ptr = 0

        no_of_pieces = 0
        cart_qty = 0
        product_tax_amount = 0
        basic_rate = 0
        inline_sum_amount = 0
        cart_product_map = return_order.shipment.order.ordered_cart.rt_cart_list.filter(cart_product=m.product).last()
        product_price = cart_product_map.selling_price

        # if ordered_product.order.ordered_cart.cart_type != 'DISCOUNTED':
        #     product_pro_price_ptr = m.effective_price
        # else:
        #     product_pro_price_ptr = cart_product_map.item_effective_prices
        # if m.product.product_mrp:
        product_pro_price_mrp = m.product.product_mrp
        # else:
        #     product_pro_price_mrp = round(product_price.mrp, 2)
        no_of_pieces = m.product.rt_cart_product_mapping.last().no_of_pieces
        cart_qty = m.product.rt_cart_product_mapping.last().qty

        # new code for tax start
        tax_sum = m.get_product_tax_json()

        get_tax_val = tax_sum / 100
        basic_rate = (float(product_pro_price_ptr)) / (float(get_tax_val) + 1)
        base_price = (float(product_pro_price_ptr) * float(m.shipped_qty)) / (float(get_tax_val) + 1)
        product_tax_amount = round(float(base_price) * float(get_tax_val), 2)
        for z in return_order.seller_shop.shop_name_address_mapping.all():
            cin = 'U74999HR2018PTC075977' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else '---'
            shop_name_gram = 'GFDN SERVICES PVT LTD' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else z.shop_name
            nick_name_gram, address_line1_gram = z.nick_name, z.address_line1
            city_gram, state_gram, pincode_gram = z.city, z.state, z.pincode

        ordered_prodcut = {
            "product_sku": m.product.product_gf_code,
            "product_short_description": m.product.product_short_description,
            "product_ean_code": m.product.product_ean_code,
            "product_hsn": m.product.product_hsn,
            "product_tax_percentage": "" if tax_sum == 0 else str(tax_sum) + "%",
            "product_mrp": product_pro_price_mrp,
            "shipped_qty": m.shipped_qty,
            "product_inner_case_size": m.product.product_inner_case_size,
            "product_no_of_pices": int(m.shipped_qty) * int(m.product.product_inner_case_size),
            "basic_rate": basic_rate,
            "basic_amount": float(m.shipped_qty) * float(basic_rate),
            "price_to_retailer": round(product_pro_price_ptr, 2),
            "product_sub_total": float(m.shipped_qty) * float(product_pro_price_ptr),
            "product_tax_amount": product_tax_amount
        }
        # total_tax_sum = total_tax_sum + product_tax_amount
        # inline_sum_amount = inline_sum_amount + product_pro_price_ptr
        product_listing.append(ordered_prodcut)
        # New Code For Product Listing End

        # sum_qty += int(m.shipped_qty)
        # sum_amount += int(m.shipped_qty) * product_pro_price_ptr
        inline_sum_amount += int(m.shipped_qty) * product_pro_price_ptr
        gst_tax = (m.base_price * m.get_products_gst()) / 100
        cess_tax = (m.base_price * m.get_products_gst_cess_tax()) / 100
        surcharge_tax = (m.base_price * m.get_products_gst_surcharge()) / 100
        product_special_cess = m.product.product_special_cess
        if product_special_cess is None:
            product_special_cess = 0.0
        else:
            product_special_cess = product_special_cess
        gst_tax_list.append(gst_tax)
        cess_tax_list.append(cess_tax)
        surcharge_tax_list.append(surcharge_tax)
        igst, cgst, sgst, cess, surcharge = sum(gst_tax_list), (sum(gst_tax_list)) / 2, (
            sum(gst_tax_list)) / 2, sum(
            cess_tax_list), sum(surcharge_tax_list)

    total_amount = return_order.return_invoice.invoice_sub_total
    tcs_rate = 0.0
    # ordered_product.invoice.tcs_percent
    tcs_tax = 0.0
    # ordered_product.invoice.tcs_amount
    total_tax_amount = return_order.shipment.sum_amount_tax()
    try:
        product_special_cess = round(m.total_product_cess_amount)
    except:
        product_special_cess = 0
    amount = total_amount
    total_amount = total_amount + tcs_tax
    total_amount_int = round(total_amount)
    total_tax_amount_int = round(total_tax_amount)

    amt = [num2words(i) for i in str(total_amount_int).split('.')]
    rupees = amt[0]

    tax_amt = [num2words(i) for i in str(total_tax_amount_int).split('.')]
    tax_rupees = tax_amt[0]

    logger.info("creating return challan pdf")
    logger.info(template_name)
    logger.info(request.get_host())

    data = {"shipment": return_order.shipment, "order": return_order.shipment.order, "return_order": return_order,
            "url": request.get_host(), "scheme": request.is_secure() and "https" or "http",
            "shipping_address": shipping_address, "billing_address": billing_address,
            "igst": igst, "cgst": cgst, "sgst": sgst, "product_special_cess": product_special_cess,
            "tcs_tax": tcs_tax, "tcs_rate": tcs_rate, "cess": cess,
            "surcharge": surcharge, "total_amount": total_amount, "amount": amount,
            "barcode": barcode, "product_listing": product_listing, "rupees": rupees, "tax_rupees": tax_rupees,
            "seller_shop_gistin": seller_shop_gistin, "buyer_shop_gistin": buyer_shop_gistin,
            "open_time": open_time, "close_time": close_time, "sum_qty": sum_qty,
            "sum_basic_amount": sum_basic_amount,
            "shop_name_gram": shop_name_gram, "nick_name_gram": nick_name_gram,
            "address_line1_gram": address_line1_gram, "city_gram": city_gram, "state_gram": state_gram,
            "pincode_gram": pincode_gram, "cin": cin_number,
            "hsn_list": list1, "license_number": license_number, "e_invoice_data": e_invoice_data}

    cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                  "no-stop-slow-scripts": True, "quiet": True}
    response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                   context=data, show_content_in_browser=False, cmd_options=cmd_option)

    try:
        # create_invoice_data(ordered_product)
        return_order.return_invoice.invoice_pdf.save("{}".format(filename),
                                                     ContentFile(response.rendered_content), save=True)
        return_order.save()
    except Exception as e:
        logger.exception(e)
    return return_order


def pdf_superstore_generation(request, ordered_product):
    """
    :param request: request object
    :param ordered_product: Order product object
    :return: pdf instance
    """
    # get prefix of file name
    file_prefix = PREFIX_INVOICE_FILE_NAME
    # get the file name along with with prefix name
    filename = create_file_name(file_prefix, ordered_product, with_timestamp=True)
    # we will be changing based on shop name
    template_name = 'admin/invoice/invoice_sp_superstore.html'
    if type(request) is str:
        request = None
        ordered_product = get_object_or_404(OrderedProduct, pk=ordered_product)
    else:
        request = request
        ordered_product = ordered_product
    if ordered_product.order.ordered_cart.cart_type == 'SUPERSTORE_RETAIL':
        product = ordered_product.rt_order_product_order_product_mapping.last().product
        ordered_product = ordered_product.order.reference_order.rt_order_order_product.filter(
            rt_order_product_order_product_mapping__product=product).last()
    if ordered_product.invoice and ordered_product.invoice.invoice_pdf and ordered_product.invoice.invoice_pdf.url:
        pass
    else:
        barcode = barcodeGen(ordered_product.invoice_no)
        e_invoice_data = None
        shop = ordered_product.order.seller_shop
        shop_name = shop.shop_name
        license_number = getShopLicenseNumber(shop_name)
        # CIN
        cin_number = getShopCINNumber(shop_name)
        open_time = '-'
        close_time = '-'

        seller_shop_gistin = 'unregistered'
        buyer_shop_gistin = 'unregistered'
        if shop and shop.shop_name_documents.exists():
            seller_shop_gistin = ordered_product.order.ordered_cart.seller_shop.shop_name_documents.filter(
                shop_document_type='gstin').last().shop_document_number if ordered_product.order.ordered_cart.seller_shop.shop_name_documents.filter(
                shop_document_type='gstin').exists() else getGSTINNumber(shop_name)

        # shop_mapping_list = ShopMigrationMapp.objects.filter(
        #     new_sp_addistro_shop=ordered_product.order.ordered_cart.seller_shop.pk).all()
        # if shop_mapping_list.exists():
        #     template_name = 'admin/invoice/invoice_addistro_sp.html'
        dispatch_address = ordered_product.order.seller_shop.shop_name_address_mapping.filter(
            address_type='shipping').last()
        product_listing = []
        taxes_list = []
        gst_tax_list = []
        cess_tax_list = []
        surcharge_tax_list = []
        sum_qty = 0
        igst = sum(gst_tax_list)
        cgst = (sum(gst_tax_list)) / 2
        sgst = (sum(gst_tax_list)) / 2
        cess = sum(cess_tax_list)
        surcharge = sum(surcharge_tax_list)
        open_time = '-'
        close_time = '-'
        sum_qty = 0
        sum_basic_amount = 0
        shop_name_gram = 'GFDN SERVICES PVT LTD'
        nick_name_gram = '-'
        address_line1_gram = '-'
        city_gram = '-'
        state_gram = '-'
        pincode_gram = '-'
        cin = '-'
        list1 = []
        for m in ordered_product.rt_order_product_order_product_mapping.filter(shipped_qty__gt=0):
            dict1 = {}
            flag = 0
            if len(list1) > 0:
                for i in list1:
                    if i["hsn"] == m.product.product_hsn:
                        i["taxable_value"] = i["taxable_value"] + m.base_price
                        i["cgst"] = i["cgst"] + (m.base_price * m.get_products_gst()) / 200
                        i["sgst"] = i["sgst"] + (m.base_price * m.get_products_gst()) / 200
                        i["igst"] = i["igst"] + (m.base_price * m.get_products_gst()) / 100
                        i["cess"] = i["cess"] + (m.base_price * m.get_products_gst_cess_tax()) / 100
                        i["surcharge"] = i["surcharge"] + (m.base_price * m.get_products_gst_surcharge()) / 100
                        if m.product.product_special_cess is None:
                            i["product_special_cess"] = i["product_special_cess"] + 0.0
                        else:
                            i["product_special_cess"] = i["product_special_cess"] + m.total_product_cess_amount
                        i["total"] = i["total"] + m.product_tax_amount
                        flag = 1

            if flag == 0:
                dict1["hsn"] = m.product.product_hsn
                dict1["taxable_value"] = m.base_price
                dict1["cgst"] = (m.base_price * m.get_products_gst()) / 200
                dict1["cgst_rate"] = m.get_products_gst() / 2
                dict1["sgst"] = (m.base_price * m.get_products_gst()) / 200
                dict1["sgst_rate"] = m.get_products_gst() / 2
                dict1["igst"] = (m.base_price * m.get_products_gst()) / 100
                dict1["igst_rate"] = m.get_products_gst()
                dict1["cess"] = (m.base_price * m.get_products_gst_cess_tax()) / 100
                dict1["cess_rate"] = m.get_products_gst_cess_tax()
                dict1["surcharge"] = (m.base_price * m.get_products_gst_surcharge()) / 100
                dict1["product_special_cess"] = m.product.product_special_cess
                if dict1["product_special_cess"] is None:
                    dict1["product_special_cess"] = 0.0
                else:
                    dict1["product_special_cess"] = m.total_product_cess_amount
                dict1["surcharge_rate"] = m.get_products_gst_surcharge()
                dict1["total"] = m.product_tax_amount
                list1.append(dict1)

            sum_qty += m.shipped_qty
            sum_basic_amount += m.base_price
            tax_sum = 0
            basic_rate = 0
            product_tax_amount = 0
            product_pro_price_mrp = 0
            product_pro_price_ptr = 0

            no_of_pieces = 0
            cart_qty = 0
            product_tax_amount = 0
            basic_rate = 0
            inline_sum_amount = 0
            cart_product_map = ordered_product.order.ordered_cart.rt_cart_list.filter(cart_product=m.product).last()
            product_price = cart_product_map.selling_price

            if ordered_product.order.ordered_cart.cart_type != 'DISCOUNTED':
                product_pro_price_ptr = m.effective_price
            else:
                product_pro_price_ptr = cart_product_map.item_effective_prices
            if m.product.product_mrp:
                product_pro_price_mrp = m.product.product_mrp
            else:
                product_pro_price_mrp = round(product_price.mrp, 2)
            no_of_pieces = m.product.rt_cart_product_mapping.last().no_of_pieces
            cart_qty = m.product.rt_cart_product_mapping.last().qty

            # new code for tax start
            tax_sum = m.get_product_tax_json()

            get_tax_val = tax_sum / 100
            basic_rate = (float(product_pro_price_ptr)) / (float(get_tax_val) + 1)
            base_price = (float(product_pro_price_ptr) * float(m.shipped_qty)) / (float(get_tax_val) + 1)
            product_tax_amount = round(float(base_price) * float(get_tax_val), 2)
            if shop:
                for z in shop.shop_name_address_mapping.all():
                    cin = 'U74999HR2018PTC075977' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else '---'
                    shop_name_gram = 'GFDN SERVICES PVT LTD' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else z.shop_name
                    nick_name_gram, address_line1_gram = z.nick_name, z.address_line1
                    city_gram, state_gram, pincode_gram = z.city, z.state, z.pincode
            else:
                cin = None
                shop_name_gram = None
                nick_name_gram, address_line1_gram = None, None
                city_gram, state_gram, pincode_gram = None, None, None

            ordered_prodcut = {
                "product_sku": m.product.product_gf_code,
                "product_short_description": m.product.product_short_description if m.product.product_type == 0 else m.product.product_short_description + " (Discounted)",
                "product_ean_code": m.product.product_ean_code,
                "product_hsn": m.product.product_hsn,
                "product_tax_percentage": "" if tax_sum == 0 else str(tax_sum) + "%",
                "product_mrp": product_pro_price_mrp,
                "shipped_qty": m.shipped_qty,
                "product_inner_case_size": m.product.product_inner_case_size,
                "product_no_of_pices": int(m.shipped_qty) * int(m.product.product_inner_case_size),
                "basic_rate": basic_rate,
                "basic_amount": float(m.shipped_qty) * float(basic_rate),
                "price_to_retailer": round(product_pro_price_ptr, 2),
                "product_sub_total": float(m.shipped_qty) * float(product_pro_price_ptr),
                "product_tax_amount": product_tax_amount
            }
            # total_tax_sum = total_tax_sum + product_tax_amount
            # inline_sum_amount = inline_sum_amount + product_pro_price_ptr
            product_listing.append(ordered_prodcut)
            # New Code For Product Listing End

            # sum_qty += int(m.shipped_qty)
            # sum_amount += int(m.shipped_qty) * product_pro_price_ptr
            inline_sum_amount += int(m.shipped_qty) * product_pro_price_ptr
            gst_tax = (m.base_price * m.get_products_gst()) / 100
            cess_tax = (m.base_price * m.get_products_gst_cess_tax()) / 100
            surcharge_tax = (m.base_price * m.get_products_gst_surcharge()) / 100
            product_special_cess = m.product.product_special_cess
            if product_special_cess is None:
                product_special_cess = 0.0
            else:
                product_special_cess = product_special_cess
            gst_tax_list.append(gst_tax)
            cess_tax_list.append(cess_tax)
            surcharge_tax_list.append(surcharge_tax)
            igst, cgst, sgst, cess, surcharge = sum(gst_tax_list), (sum(gst_tax_list)) / 2, (
                sum(gst_tax_list)) / 2, sum(
                cess_tax_list), sum(surcharge_tax_list)

        total_amount = ordered_product.invoice.invoice_sub_total
        tcs_rate = ordered_product.invoice.tcs_percent
        tcs_tax = ordered_product.invoice.tcs_amount
        total_tax_amount = ordered_product.sum_amount_tax()
        try:
            product_special_cess = round(m.total_product_cess_amount)
        except:
            product_special_cess = 0
        amount = total_amount
        total_amount = total_amount + tcs_tax
        total_amount_int = round(total_amount)
        total_tax_amount_int = round(total_tax_amount)

        amt = [num2words(i) for i in str(total_amount_int).split('.')]
        rupees = amt[0].capitalize()

        tax_amt = [num2words(i) for i in str(total_tax_amount_int).split('.')]
        tax_rupees = tax_amt[0].capitalize()

        logger.info("createing invoice pdf")
        logger.info(template_name)
        logger.info(request.get_host())
        data = {"shipment": ordered_product, "order": ordered_product.order,
                "url": request.get_host(), "scheme": request.is_secure() and "https" or "http",
                "igst": igst, "cgst": cgst, "sgst": sgst, "product_special_cess": product_special_cess,
                "tcs_tax": tcs_tax, "tcs_rate": tcs_rate, "cess": cess,
                "surcharge": surcharge, "total_amount": total_amount, "amount": amount,
                "barcode": barcode, "product_listing": product_listing, "rupees": rupees, "tax_rupees": tax_rupees,
                "seller_shop_gistin": seller_shop_gistin, "buyer_shop_gistin": buyer_shop_gistin,
                "open_time": open_time, "close_time": close_time, "sum_qty": sum_qty,
                "sum_basic_amount": sum_basic_amount,
                "shop_name_gram": shop_name_gram, "nick_name_gram": nick_name_gram,
                "address_line1_gram": address_line1_gram, "city_gram": city_gram, "state_gram": state_gram,
                "pincode_gram": pincode_gram, "cin": cin_number,
                "hsn_list": list1,
                "license_number": license_number,
                "e_invoice_data": e_invoice_data,
                "dispatch_address": dispatch_address}

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)

        try:
            create_invoice_data(ordered_product)
            ordered_product.invoice.invoice_pdf.save("{}".format(filename),
                                                     ContentFile(response.rendered_content), save=True)
        except Exception as e:
            logger.exception(e)
    return ordered_product


def pdf_generation_retailer(request, order_id, delay=True):
    """
    :param request: request object
    :param order_id: Order id
    :return: pdf instance
    """
    file_prefix = PREFIX_INVOICE_FILE_NAME
    order = Order.objects.filter(id=order_id).last()
    # ordered_product = order.rt_order_order_product.all()[0]
    filename = create_file_name(file_prefix, order.rt_order_order_product.all()[0], with_timestamp=True)
    template_name = 'admin/invoice/invoice_retailer_3inch.html'
    # Don't create pdf if already created
    if order.rt_order_order_product.all()[0].invoice and order.rt_order_order_product.all()[0].invoice.invoice_pdf and \
            order.rt_order_order_product.all()[0].invoice.invoice_pdf.url:
        try:
            phone_number, shop_name = order.buyer.phone_number, order.seller_shop.shop_name
            media_url, file_name, manager = order.rt_order_order_product.all()[0].invoice.invoice_pdf.url, \
                                            order.rt_order_order_product.all()[0].invoice.invoice_no, \
                                            order.ordered_cart.seller_shop.pos_shop.filter(
                                                user_type='manager').last()
            if delay:
                whatsapp_opt_in.delay(phone_number, shop_name, media_url, file_name)
                if manager and manager.user.email:
                    send_invoice_pdf_email.delay(manager.user.email, shop_name, order.order_no, media_url,
                                                 file_name, 'order')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
                # email task to send manager order invoice ^
            else:
                if manager and manager.user.email:
                    send_invoice_pdf_email(manager.user.email, shop_name, order.order_no, media_url, file_name,
                                           'order')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
            return whatsapp_opt_in(phone_number, shop_name, media_url, file_name)
        except Exception as e:
            logger.exception("Retailer Invoice send error order {}".format(order.order_no))
            logger.exception(e)

    else:
        barcode = barcodeGen(order.rt_order_order_product.all()[0].invoice_no)
        # Products
        product_listing = []
        # Total invoice qty
        sum_qty = 0
        # Total Ordered Amount
        total_mrp = 0
        total = 0
        count = 0
        for m in order.rt_order_order_product.all()[0].rt_order_product_order_product_mapping.filter(shipped_qty__gt=0):
            sum_qty += m.shipped_qty
            cart_product_map = order.rt_order_order_product.all()[0].order.ordered_cart.rt_cart_list.filter(
                retailer_product=m.retailer_product,
                product_type=m.product_type
            ).last()
            product_pro_price_ptr = cart_product_map.selling_price
            product = cart_product_map.retailer_product
            product_pack_type = product.product_pack_type
            default_unit = "piece"
            if product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=product.measurement_category, default=True).unit
            ordered_p = {
                "id": cart_product_map.id,
                "product_short_description": m.retailer_product.product_short_description,
                "product_ean_code": m.retailer_product.product_ean_code,
                "mrp": m.retailer_product.mrp if product_pack_type == 'packet' else str(
                    m.retailer_product.mrp) + '/' + default_unit,
                "qty": int(m.shipped_qty) if product_pack_type == 'packet' else str(m.shipped_qty) + ' ' + default_unit,
                "rate": float(product_pro_price_ptr) if product_pack_type == 'packet' else str(
                    product_pro_price_ptr) + '/' + default_unit,
                "product_sub_total": round(float(m.shipped_qty) * float(product_pro_price_ptr), 2)
            }
            total += ordered_p['product_sub_total']
            total_mrp += m.shipped_qty * m.retailer_product.mrp
            product_listing.append(ordered_p)
            if len(m.retailer_product.product_short_description) > 34:
                count = count + 2  # height of double line
            else:
                count = count + 1  # height of sinlge line
        cart = order.rt_order_order_product.all()[0].order.ordered_cart
        product_listing = sorted(product_listing, key=itemgetter('id'))
        # Total payable amount
        total_amount = round(order.rt_order_order_product.all()[0].invoice_amount_final, 2)
        total_amount_int = int(round(total_amount))
        # redeem value
        redeem_value = round(cart.redeem_points / cart.redeem_factor, 2) if cart.redeem_factor else 0
        # Total discount
        discount = round(total - total_amount - redeem_value, 2)
        # Total payable amount in words
        amt = [num2words(i) for i in str(total_amount_int).split('.')]
        rupees = amt[0]
        total_discount = round((total_mrp - total_amount_int), 2)
        # Shop Details
        nick_name = '-'
        address_line1 = '-'
        city = '-'
        state = '-'
        pincode = '-'
        address_contact_number = ''
        for z in order.rt_order_order_product.all()[0].order.seller_shop.shop_name_address_mapping.all():
            nick_name, address_line1 = z.nick_name, z.address_line1
            city, state, pincode = z.city, z.state, z.pincode
            address_contact_number = z.address_contact_number

        total = round(total)
        total_amount = round(total_amount)
        total = round(total, 2)

        # Licence
        shop_name = order.seller_shop.shop_name
        shop_mapping = ParentRetailerMapping.objects.filter(
            retailer=order.seller_shop).last()
        if shop_mapping:
            shop_name = shop_mapping.parent.shop_name
        else:
            shop_name = shop_name
        license_number = getShopLicenseNumber(shop_name)
        # CIN
        cin_number = getShopCINNumber(shop_name)
        # GSTIN
        retailer_gstin_number = ""
        if order.seller_shop.shop_name_documents.filter(shop_document_type='gstin'):
            retailer_gstin_number = order.seller_shop.shop_name_documents.filter(
                shop_document_type='gstin').last().shop_document_number

        height = 170 + 17 * count  # calculating page height of invoice 170 is base value

        data = {"shipment": order.rt_order_order_product.all()[0], "order": order.rt_order_order_product.all()[0].order,
                "url": request.get_host(),
                "scheme": request.is_secure() and "https" or "http", "total_amount": total_amount, 'total': total,
                'discount': discount, "barcode": barcode, "product_listing": product_listing, "rupees": rupees,
                "sum_qty": sum_qty, "nick_name": nick_name, "address_line1": address_line1, "city": city,
                "state": state, "total_discount": total_discount,
                "pincode": pincode, "address_contact_number": address_contact_number, "reward_value": redeem_value,
                "license_number": license_number, "retailer_gstin_number": retailer_gstin_number,
                "cin": cin_number,
                "payment_type": order.rt_order_order_product.all()[
                    0].order.rt_payment_retailer_order.last().payment_type.type}
        cmd_option = {"margin-top": 2, "margin-left": 0, "margin-right": 0, "margin-bottom": 2, "javascript-delay": 0,
                      "page-height": height, "page-width": 70, "no-stop-slow-scripts": True, "quiet": True,
                      'encoding': 'utf8 '
            , "dpi": 300}
        response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        # with open("heelo.pdf", "wb") as f:
        #     f.write(response.rendered_content)
        # content = render_to_string(template_name, data)
        # with codecs.open("abc.html", "w", "utf-8-sig") as static_file:
        #     static_file.write(content)

        try:
            # create_invoice_data(ordered_product)
            order.rt_order_order_product.all()[0].invoice.invoice_pdf.save("{}".format(filename),
                                                                           ContentFile(response.rendered_content),
                                                                           save=True)
            phone_number = order.buyer.phone_number
            shop_name = order.seller_shop.shop_name
            media_url = order.rt_order_order_product.all()[0].invoice.invoice_pdf.url
            file_name = order.rt_order_order_product.all()[0].invoice.invoice_no
            manager = order.ordered_cart.seller_shop.pos_shop.filter(user_type='manager').last()
            # whatsapp api call for sending an invoice
            if delay:
                if request.data.get("is_whatsapp", True):
                    whatsapp_opt_in.delay(phone_number, shop_name, media_url, file_name)
                if manager and manager.user.email:
                    send_invoice_pdf_email.delay(manager.user.email, shop_name, order.order_no, media_url, file_name,
                                                 'order')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
                # send email
            else:
                if manager and manager.user.email:
                    send_invoice_pdf_email(manager.user.email, shop_name, order.order_no, media_url, file_name, 'order')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
                if request.data.get("is_whatsapp", True):
                    return whatsapp_opt_in(phone_number, shop_name, media_url, file_name)
        except Exception as e:
            logger.exception("Retailer Invoice save and send error order {}".format(order.order_no))
            logger.exception(e)


def pdf_generation_return_retailer(request, order, ordered_product, order_return, return_items,
                                   credit_note_instance, delay=True):
    file_prefix = PREFIX_CREDIT_NOTE_FILE_NAME
    # template_name = 'admin/credit_note/credit_note_retailer.html'
    template_name = 'admin/credit_note/credit_retailer_3inch.html'

    # Don't create pdf if already created
    if credit_note_instance and credit_note_instance.credit_note_pdf and credit_note_instance.credit_note_pdf.url:
        try:
            order_number, order_status, phone_number = order.order_no, order.order_status, order.buyer.phone_number
            refund_amount = order_return.refund_amount if order_return.refund_amount > 0 else 0
            media_url, file_name = credit_note_instance.credit_note_pdf.url, ordered_product.invoice_no
            manager = order.ordered_cart.seller_shop.pos_shop.filter(user_type='manager').last()
            shop_name = order.ordered_cart.seller_shop.shop_name
            if delay:
                whatsapp_order_refund.delay(order_number, order_status, phone_number, refund_amount, media_url,
                                            file_name)
                if manager and manager.user.email:
                    send_invoice_pdf_email.delay(manager.user.email, shop_name, order_number, media_url, file_name,
                                                 'return')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
                # send mail to manager for return
            else:
                if manager and manager.user.email:
                    send_invoice_pdf_email(manager.user.email, shop_name, order_number, media_url, file_name,
                                           'return')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
                return whatsapp_order_refund(order_number, order_status, phone_number, refund_amount, media_url,
                                             file_name)
                # send mail to manager for return
        except Exception as e:
            logger.exception("Retailer Credit note send error order {} return {}".format(order.order_no,
                                                                                         order_return.id))
            logger.exception(e)

    else:
        filename = create_file_name(file_prefix, credit_note_instance.credit_note_id)
        barcode = barcodeGen(credit_note_instance.credit_note_id)
        # Total Items
        return_item_listing = []
        # Total Returned Amount
        total = 0
        return_qty = 0
        count = 0

        for item in return_items:
            product = item.ordered_product.retailer_product
            product_pack_type = product.product_pack_type
            if product_pack_type == 'loose':
                default_unit = MeasurementUnit.objects.get(category=product.measurement_category, default=True)
            return_p = {
                "id": item.id,
                "product_short_description": item.ordered_product.retailer_product.product_short_description,
                "mrp": item.ordered_product.retailer_product.mrp if product_pack_type == 'packet' else str(
                    item.ordered_product.retailer_product.mrp) + '/' + default_unit.unit,
                "qty": item.return_qty if product_pack_type == 'packet' else str(
                    item.return_qty) + ' ' + default_unit.unit,
                "rate": round(float(item.ordered_product.selling_price), 2) if product_pack_type == 'packet' else str(
                    round(float(item.ordered_product.selling_price), 2)) + '/' + default_unit.unit,
                "product_sub_total": float(item.return_qty) * float(item.ordered_product.selling_price)
            }
            return_qty += item.return_qty
            total += return_p['product_sub_total']
            return_item_listing.append(return_p)
            if len(item.ordered_product.retailer_product.product_short_description) > 34:
                count = count + 2  # height of double line
            else:
                count = count + 1  # height of sinlge line

        return_item_listing = sorted(return_item_listing, key=itemgetter('id'))
        # redeem value
        redeem_value = order_return.refund_points if order_return.refund_points > 0 else 0
        if redeem_value > 0:
            redeem_value = round(redeem_value / order.ordered_cart.redeem_factor, 2)
        # Total discount
        discount = order_return.discount_adjusted if order_return.discount_adjusted > 0 else 0
        # Total payable amount in words

        # Total payable amount
        total_amount = order_return.refund_amount if order_return.refund_amount > 0 else 0
        total_amount_int = round(total_amount)
        # Total payable amount in words
        amt = [num2words(i) for i in str(total_amount_int).split('.')]
        rupees = amt[0]

        # Shop Details
        nick_name = '-'
        address_line1 = '-'
        city = '-'
        state = '-'
        pincode = '-'
        address_contact_number = ''
        for z in ordered_product.order.seller_shop.shop_name_address_mapping.all():
            nick_name, address_line1 = z.nick_name, z.address_line1
            city, state, pincode = z.city, z.state, z.pincode
            address_contact_number = z.address_contact_number

        # Licence
        shop_mapping = ParentRetailerMapping.objects.filter(
            retailer=order.seller_shop).last()
        if shop_mapping:
            shop_name = shop_mapping.parent.shop_name
        else:
            shop_name = order.seller_shop.shop_name
        license_number = getShopLicenseNumber(shop_name)
        # CIN
        cin_number = getShopCINNumber(shop_name)
        # GSTIN
        retailer_gstin_number = ""
        if order.seller_shop.shop_name_documents.filter(shop_document_type='gstin'):
            retailer_gstin_number = order.seller_shop.shop_name_documents.filter(
                shop_document_type='gstin').last().shop_document_number

        height = 170 + 13 * count  # calculating page height of invoice 170 is base value
        data = {
            "url": request.get_host(),
            "scheme": request.is_secure() and "https" or "http",
            "credit_note": credit_note_instance,
            "shipment": ordered_product,
            "order": ordered_product.order,
            "total_amount": total_amount,
            "discount": discount,
            "reward_value": redeem_value,
            'total': math.floor(total),
            "barcode": barcode,
            "return_item_listing": return_item_listing,
            "rupees": rupees,
            "sum_qty": return_qty,
            "nick_name": nick_name,
            "address_line1": address_line1,
            "city": city,
            "state": state,
            "pincode": pincode,
            "address_contact_number": address_contact_number,
            "license_number": license_number,
            "cin": cin_number,
            "retailer_gstin_number": retailer_gstin_number
        }

        cmd_option = {"margin-top": 10, "margin-left": 0, "margin-right": 0, "javascript-delay": 0,
                      "page-height": height, "page-width": 80,
                      "no-stop-slow-scripts": True, "quiet": True, }
        response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)

        # with open("/home/amit/env/test5/qa4/cancel.pdf", "wb") as f:
        #     f.write(response.rendered_content)
        # # content = render_to_string(template_name, data)
        # # with open("abc.html", 'w') as static_file:
        # #     static_file.write(content)

        try:
            # create_invoice_data(ordered_product)
            credit_note_instance.credit_note_pdf.save("{}".format(filename), ContentFile(response.rendered_content),
                                                      save=True)
            order_number = order.order_no
            order_status = order.order_status
            phone_number = order.buyer.phone_number
            refund_amount = order_return.refund_amount if order_return.refund_amount > 0 else 0
            media_url = credit_note_instance.credit_note_pdf.url
            file_name = ordered_product.invoice_no
            manager = order.ordered_cart.seller_shop.pos_shop.filter(user_type='manager').last()
            shop_name = order.ordered_cart.seller_shop.shop_name
            if delay:
                if request.data.get("is_whatsapp", True):
                    whatsapp_order_refund.delay(order_number, order_status, phone_number, refund_amount, media_url,
                                                file_name)
                if manager and manager.user.email:
                    send_invoice_pdf_email.delay(manager.user.email, shop_name, order_number, media_url, file_name,
                                                 'return')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
                # send order return mail to
            else:
                if manager and manager.user.email:
                    send_invoice_pdf_email(manager.user.email, shop_name, order_number, media_url, file_name, 'return')
                else:
                    info_logger.error("Email not present for Manager {}".format(str(manager)))
                # send mail to manager
                if request.data.get("is_whatsapp", False):
                    return whatsapp_order_refund(order_number, order_status, phone_number, refund_amount, media_url,
                                                 file_name)
        except Exception as e:
            logger.exception("Retailer Credit note save and send error order {} return {}".format(order.order_no,
                                                                                                  order_return.id))
            logger.exception(e)


class DownloadCreditNoteDiscounted(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'credit_note.pdf'
    template_name = 'admin/credit_note/discounted_credit_note.html'

    def get(self, request, *args, **kwargs):
        credit_note = get_object_or_404(Note, pk=self.kwargs.get('pk'))
        # Licence
        shop_mapping = ParentRetailerMapping.objects.filter(
            retailer=credit_note.shipment.order.seller_shop).last()
        if shop_mapping:
            shop_name = shop_mapping.parent.shop_name
        else:
            shop_name = credit_note.shipment.order.seller_shop.shop_name
        license_number = getShopLicenseNumber(shop_name)
        # CIN
        cin_number = getShopCINNumber(shop_name)
        # PAN
        pan_number = getShopPANNumber(shop_name)

        for gs in credit_note.shipment.order.seller_shop.shop_name_documents.all():
            gstinn3 = gs.shop_document_number if gs.shop_document_type == 'gstin' else getGSTINNumber(shop_name)
        for gs in credit_note.shipment.order.billing_address.shop_name.shop_name_documents.all():
            gstinn2 = gs.shop_document_number if gs.shop_document_type == 'gstin' else 'Unregistered'
        for gs in credit_note.shipment.order.shipping_address.shop_name.shop_name_documents.all():
            gstinn1 = gs.shop_document_number if gs.shop_document_type == 'gstin' else 'Unregistered'
        # gst_number ='07AAHCG4891M1ZZ' if credit_note.shipment.order.seller_shop.shop_name_address_mapping.all().last().state.state_name=='Delhi' else '09AAHCG4891M1ZV'
        # changes for org change

        # shop_id = credit_note.shipment.order.buyer_shop.shop_owner_id
        # payment = PaymentDetail.objects.filter(paid_by_id=shop_id)
        # paid_amount = 0
        # for p in payment:
        #     date_time = p.created_at
        #     month = date_time.strftime("%m")
        #     year = date_time.strftime("%Y")
        #     if int(month) > 2 and int(year) > 2019:
        #         paid_amount += p.paid_amount

        shop_mapping_list = ShopMigrationMapp.objects.filter(
            new_sp_addistro_shop=credit_note.shipment.order.seller_shop.pk).all()
        if shop_mapping_list.exists():
            self.template_name = 'admin/credit_note/addistro_discounted_credit_note.html'
        amount = credit_note.amount
        credit_note_type = credit_note.credit_note_type
        products = credit_note.shipment.rt_order_product_order_product_mapping.all()
        # reason = 'Retuned' if [i for i in pp if i.returned_qty>0] else 'Damaged' if [i for i in pp if i.damaged_qty>0] else 'Returned and Damaged'
        order_id = credit_note.shipment.order.order_no
        sum_qty, sum_amount, tax_inline, sum_basic_amount, product_tax_amount, total_product_tax_amount = 0, 0, 0, 0, 0, 0
        taxes_list, gst_tax_list, cess_tax_list, surcharge_tax_list = [], [], [], []
        igst, cgst, sgst, cess, surcharge = 0, 0, 0, 0, 0
        tcs_rate = credit_note.shipment.invoice.tcs_percent
        tcs_tax = credit_note.tcs_amount
        list1 = []
        for z in credit_note.shipment.order.seller_shop.shop_name_address_mapping.all():
            pan_no = 'AAHCG4891M' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else '---'
            cin = 'U74999HR2018PTC075977' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else '---'
            shop_name_gram = 'GFDN SERVICES PVT LTD' if z.shop_name == 'GFDN SERVICES PVT LTD (NOIDA)' or z.shop_name == 'GFDN SERVICES PVT LTD (DELHI)' else z.shop_name
            nick_name_gram, address_line1_gram = z.nick_name, z.address_line1
            city_gram, state_gram, pincode_gram = z.city, z.state, z.pincode
        for m in products:
            dict1 = {}
            flag = 0
            basic_rate = m.basic_rate_discounted
            delivered_qty = float(m.delivered_qty)
            gst_percent = m.get_products_gst()
            cess = m.get_products_gst_cess_tax()
            surcharge = m.get_products_gst_surcharge()
            if len(list1) > 0:
                for i in list1:
                    if i["hsn"] == m.product.product_hsn:
                        i["taxable_value"] = i["taxable_value"] + basic_rate * delivered_qty
                        i["cgst"] = i["cgst"] + (delivered_qty * basic_rate * gst_percent) / 200
                        i["sgst"] = i["sgst"] + (delivered_qty * basic_rate * gst_percent) / 200
                        i["igst"] = i["igst"] + (delivered_qty * basic_rate * gst_percent) / 100
                        i["cess"] = i["cess"] + (delivered_qty * basic_rate * cess) / 100
                        i["surcharge"] = i["surcharge"] + (
                                delivered_qty * basic_rate * surcharge) / 100
                        i["total"] = i["total"] + m.product_tax_discount_amount
                        i["product_special_cess"] = i[
                                                        "product_special_cess"] + m.product.product_special_cess if m.product.product_special_cess else 0
                        flag = 1

            if flag == 0:
                dict1["hsn"] = m.product.product_hsn
                dict1["taxable_value"] = basic_rate * delivered_qty
                dict1["cgst"] = (basic_rate * delivered_qty * gst_percent) / 200
                dict1["cgst_rate"] = gst_percent / 2
                dict1["sgst"] = (basic_rate * delivered_qty * gst_percent) / 200
                dict1["sgst_rate"] = gst_percent / 2
                dict1["igst"] = (basic_rate * delivered_qty * gst_percent) / 100
                dict1["igst_rate"] = gst_percent
                dict1["cess"] = (basic_rate * delivered_qty * cess) / 100
                dict1["cess_rate"] = cess
                dict1["surcharge"] = (basic_rate * delivered_qty * surcharge) / 100
                # dict1["surcharge_rate"] = m.get_products_gst_surcharge() / 2
                dict1["surcharge_rate"] = surcharge
                dict1["total"] = m.product_tax_discount_amount
                dict1["product_special_cess"] = m.product.product_special_cess
                list1.append(dict1)

            sum_qty = sum_qty + (int(delivered_qty))
            sum_basic_amount += basic_rate * (delivered_qty)
            sum_amount = sum_amount + (int(delivered_qty) * (float(m.price_to_retailer) - float(m.discounted_price)))
            inline_sum_amount = (int(delivered_qty) * (m.price_to_retailer))
            gst_tax = (delivered_qty * basic_rate * gst_percent) / 100
            total_product_tax_amount += m.product_tax_discount_amount
            cess_tax = (delivered_qty * basic_rate * cess) / 100
            surcharge_tax = (delivered_qty * basic_rate * surcharge) / 100
            gst_tax_list.append(gst_tax)
            cess_tax_list.append(cess_tax)
            surcharge_tax_list.append(surcharge_tax)
            igst, cgst, sgst, cess, surcharge = sum(gst_tax_list), (sum(gst_tax_list)) / 2, (
                sum(gst_tax_list)) / 2, sum(cess_tax_list), sum(surcharge_tax_list)

        total_amount = sum_amount
        # if float(total_amount) + float(paid_amount) > 5000000:
        #     if gstinn2 == 'Unregistered':
        #         tcs_rate = 1
        #         tcs_tax = total_amount * decimal.Decimal(tcs_rate / 100)
        #     else:
        #         tcs_rate = 0.075
        #         tcs_tax = total_amount * decimal.Decimal(tcs_rate / 100)

        tcs_tax = round(tcs_tax, 2)
        total_amount = total_amount + tcs_tax
        total_amount_int = round(total_amount)
        total_product_tax_amount_int = round(total_product_tax_amount)

        amt = [num2words(i) for i in str(total_amount_int).split('.')]
        rupees = amt[0]

        prdct_tax_amt = [num2words(i) for i in str(total_product_tax_amount_int).split('.')]
        tax_rupees = prdct_tax_amt[0]

        data = {
            "object": credit_note, "products": products, "shop": credit_note, "total_amount": total_amount,
            "sum_qty": sum_qty, "sum_amount": sum_amount, "total_product_tax_amount": total_product_tax_amount,
            "tax_rupees": tax_rupees, "sum_basic_amount": sum_basic_amount, "tcs_tax": tcs_tax, "tcs_rate": tcs_rate,
            "url": request.get_host(), "scheme": request.is_secure() and "https" or "http", "igst": igst, "cgst": cgst,
            "sgst": sgst, "cess": cess, "surcharge": surcharge, "order_id": order_id, "shop_name_gram": shop_name_gram,
            "nick_name_gram": nick_name_gram, "city_gram": city_gram,
            "address_line1_gram": address_line1_gram, "pincode_gram": pincode_gram, "state_gram": state_gram,
            "amount": amount, "gstinn1": gstinn1, "gstinn2": gstinn2,
            "gstinn3": gstinn3, "rupees": rupees, "credit_note_type": credit_note_type, "pan_no": pan_number,
            "cin": cin_number,
            "hsn_list": list1, "license_number": license_number}

        cmd_option = {
            "margin-top": 10,
            "zoom": 1,
            "javascript-delay": 1000,
            "footer-center": "[page]/[topage]",
            "no-stop-slow-scripts": True,
            "quiet": True
        }
        response = PDFTemplateResponse(
            request=request, template=self.template_name,
            filename=self.filename, context=data,
            show_content_in_browser=False, cmd_options=cmd_option
        )
        return response


class DownloadNote(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'note.pdf'
    template_name = 'admin/invoice/note.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))
        data = {"object": order_obj, }
        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response


class DownloadDebitNote(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """

    filename = 'debitnote.pdf'
    template_name = 'admin/debitnote/debit_note.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(OrderedProduct, pk=self.kwargs.get('pk'))

        # order_obj1= get_object_or_404(OrderedProductMapping)
        pk = self.kwargs.get('pk')
        a = OrderedProduct.objects.get(pk=pk)
        products = a.rt_order_product_order_product_mapping.all()

        # Licence
        shop_mapping = ParentRetailerMapping.objects.filter(
            retailer=order_obj.order.ordered_cart.seller_shop.shop_name).last()
        if shop_mapping:
            shop_name = shop_mapping.parent.shop_name
        else:
            shop_name = order_obj.order.ordered_cart.seller_shop.shop_name
        license_number = getShopLicenseNumber(shop_name)
        cin_number = getShopCINNumber(shop_name)

        data = {"object": order_obj, "order": order_obj.order, "products": products,
                "license_number": license_number, "cin": cin_number}

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response


class CustomerCareApi(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        queryset = CustomerCare.objects.all()
        serializer = CustomerCareSerializer(queryset, many=True)
        msg = {'is_success': True, 'message': ['All Messages'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_201_CREATED)

    def post(self, request):
        phone_number = self.request.POST.get('phone_number')
        order_id = self.request.POST.get('order_id')
        select_issue = self.request.POST.get('select_issue')
        complaint_detail = self.request.POST.get('complaint_detail')
        msg = {'is_success': False, 'message': [''], 'response_data': None}
        if request.user.is_authenticated:
            phone_number = request.user.phone_number

        if not complaint_detail:
            msg['message'] = ["Please type the complaint_detail"]
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        serializer = CustomerCareSerializer(
            data={"phone_number": phone_number, "complaint_detail": complaint_detail, "order_id": order_id,
                  "select_issue": select_issue})
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True, 'message': ['Message Sent'], 'response_data': serializer.data}
            return Response(msg, status=status.HTTP_201_CREATED)
        else:
            msg = {'is_success': False, 'message': ['Phone Number is not Valid'], 'response_data': None}
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerOrdersList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # msg = {'is_success': True, 'message': ['No Orders of the logged in user'], 'response_data': None}
        # if request.user.is_authenticated:
        queryset = Order.objects.filter(ordered_by=request.user)
        if queryset.count() > 0:
            serializer = OrderNumberSerializer(queryset, many=True)
            msg = {'is_success': True, 'message': ['All Orders of the logged in user'],
                   'response_data': serializer.data}
        else:
            serializer = OrderNumberSerializer(queryset, many=True)
            msg = {'is_success': False, 'message': ['No Orders of the logged in user'], 'response_data': None}
        return Response(msg, status=status.HTTP_201_CREATED)
    # else:
    # return Response(msg, status=status.HTTP_201_CREATED)


class PaymentApi(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        queryset = Payment.objects.filter(payment_choice='cash_on_delivery')
        serializer = GramPaymentCodSerializer(queryset, many=True)
        msg = {'is_success': True, 'message': ['All Payments'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_201_CREATED)

    def post(self, request):  # TODO : Has to be updated as per new payment flow
        order_id = self.request.POST.get('order_id')
        payment_choice = self.request.POST.get('payment_choice')
        paid_amount = self.request.POST.get('paid_amount')
        neft_reference_number = self.request.POST.get('neft_reference_number')
        shop_id = self.request.POST.get('shop_id')
        imei_no = self.request.POST.get('imei_no')

        # payment_type = neft or cash_on_delivery
        msg = {'is_success': False, 'message': ['Have some error in shop or mapping'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        if not payment_choice:
            msg['message'] = ["Please enter payment_type"]
            return Response(msg, status=status.HTTP_200_OK)
        else:
            if payment_choice == 'neft' and not neft_reference_number:
                msg['message'] = ["Please enter neft_reference_number"]
                return Response(msg, status=status.HTTP_200_OK)

        if not paid_amount:
            msg['message'] = ["Please enter paid_amount"]
            return Response(msg, status=status.HTTP_200_OK)

        if parent_mapping.parent.shop_type.shop_type == 'sp':

            try:
                order = Order.objects.get(id=order_id)
            except ObjectDoesNotExist:
                msg['message'] = ["No order found"]
                return Response(msg, status=status.HTTP_200_OK)

            if Payment.objects.filter(order_id=order).exists():
                pass
            else:
                payment = Payment(order_id=order, paid_amount=paid_amount, payment_choice=payment_choice,
                                  neft_reference_number=neft_reference_number, imei_no=imei_no)
                payment.save()
                order.order_status = Order.ORDERED
                order.save()
            serializer = OrderSerializer(
                order, context={'parent_mapping_id': parent_mapping.parent.id,
                                'buyer_shop_id': shop_id})

        if serializer.data:
            msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class ReleaseBlocking(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        shop_id = self.request.POST.get('shop_id')
        cart_id = self.request.POST.get('cart_id')
        msg = {'is_success': False, 'message': ['Have some error in shop or mapping'], 'response_data': None}

        products_available = {}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        if not cart_id:
            msg['message'] = 'Cart id not found'
            return Response(msg, status=status.HTTP_200_OK)

        if parent_mapping.parent.shop_type.shop_type == 'sp':
            cart = Cart.objects.filter(id=cart_id).last()
            sku_id = [i.cart_product.id for i in cart.rt_cart_list.all()]
            reserved_args = json.dumps({
                'shop_id': parent_mapping.parent.id,
                'transaction_id': cart.cart_no,
                'transaction_type': 'released',
                'order_status': 'available'
            })

            OrderManagement.release_blocking(reserved_args, sku_id)
            if CusotmerCouponUsage.objects.filter(cart__id=cart_id, shop__id=shop_id).exists():
                CusotmerCouponUsage.objects.filter(cart__id=cart_id, shop__id=shop_id).delete()

            msg = {'is_success': True, 'message': ['Blocking has released'], 'response_data': None}

        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            if GramOrderedProductReserved.objects.filter(cart__id=cart_id, reserve_status='reserved').exists():
                for ordered_reserve in GramOrderedProductReserved.objects.filter(cart__id=cart_id,
                                                                                 reserve_status='reserved'):
                    ordered_reserve.order_product_reserved.available_qty = int(
                        ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
                    ordered_reserve.order_product_reserved.save()
                    ordered_reserve.delete()
            msg = {'is_success': True, 'message': ['Blocking has released'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)


class DeliveryBoyTrips(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        trip_date = ('{}-{}-{}').format(kwargs['year'], kwargs['month'], kwargs['day'])
        trip = Trip.objects.filter(created_at__date=trip_date, delivery_boy=self.request.user)
        trip_details = TripSerializer(trip, many=True)
        msg = {'is_success': True, 'message': ['Trip Details'], 'response_data': trip_details.data}
        return Response(msg, status=status.HTTP_201_CREATED)


class DeliveryShipmentDetails(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        trip_id = kwargs.get('trip')
        trips = Trip.objects.get(id=trip_id, delivery_boy=self.request.user)
        shipments = trips.rt_invoice_trip.all()
        return_details = self.getTripReturnGrouped(trips)
        shipment_details = ShipmentSerializer(shipments, many=True)
        response_data = shipment_details.data + return_details
        msg = {'is_success': True, 'message': ['Shipment Details'], 'response_data': response_data}
        return Response(msg, status=status.HTTP_201_CREATED)

    def getTripReturnGrouped(self, trip):
        trip_mappings = trip.last_mile_trip_returns_details.all()
        trip_return = []
        grouped_return_list = ReturnOrder.objects.filter(last_mile_trip_returns__in=trip_mappings)\
                                                 .values('buyer_shop', 'seller_shop')\
                                                 .annotate(return_count=Count('id'),
                                                           status=Sum(Case(
                                                               When(return_status__in=[ReturnOrder.RETURN_REQUESTED,
                                                                                       ReturnOrder.RETURN_INITIATED],
                                                                    then=1),
                                                               default=0
                                                           ), output_field=IntegerField())).order_by()
        for grouped_return in grouped_return_list:
            grouped_return_dict = {}
            grouped_return_dict['item_type'] = 'return'
            grouped_return_dict['shop_id'] = grouped_return['buyer_shop']
            shop_timing = ShopTiming.objects.filter(shop_id=grouped_return['buyer_shop'])
            if shop_timing.exists():
                final_timing = shop_timing.last()
                grouped_return_dict['shop_open_time'] = final_timing.open_timing
                grouped_return_dict['shop_close_time'] = final_timing.closing_timing
                grouped_return_dict['break_start_time'] = final_timing.break_start_time
                grouped_return_dict['break_end_time'] = final_timing.break_end_time
                grouped_return_dict['off_day'] = final_timing.off_day
            else:
                grouped_return_dict['shop_open_time'] = None
                grouped_return_dict['shop_close_time'] = None
                grouped_return_dict['break_start_time'] = None
                grouped_return_dict['break_end_time'] = None
                grouped_return_dict['off_day'] = None
            buyerShop = Shop.objects.filter(id=grouped_return['buyer_shop']).last()
            sellerShop = Shop.objects.filter(id=grouped_return['seller_shop']).last()
            shipping_address = buyerShop.shop_name_address_mapping.filter(address_type='shipping').last()
            shop_user_mapping = buyerShop.shop_user.filter(status=True,
                                                           employee_group__name='Sales Executive').last()
            sales_executive = None
            if shop_user_mapping:
                sales_executive = shop_user_mapping.employee
            sales_executive = ShopExecutiveUserSerializer(sales_executive)
            grouped_return_dict['sales_executive'] = sales_executive.data
            grouped_return_dict['seller_shop'] = SellerShopSerializer(sellerShop).data
            grouped_return_dict['buyer_shop'] = SellerShopSerializer(buyerShop).data
            grouped_return_dict['shipping_address'] = AddressSerializer(shipping_address).data
            grouped_return_dict['return_count'] = grouped_return['return_count']
            grouped_return_dict['shipment_status'] = 'PENDING' if grouped_return['status'] > 0 else 'COMPLETED'
            # grouped_return_dict['return_value'] = ReturnOrder.objects.filter(id=grouped_return['id']).last().return_amount
            grouped_return_dict['shipment_status'] = grouped_return['return_status']
            grouped_return_dict['return_value'] = ReturnOrder.objects.filter(id=grouped_return['id']).last().return_amount
            trip_return.append(grouped_return_dict)

        return trip_return


class ShipmentDeliveryBulkUpdate(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def is_pan_required(self, shipmentproductmapping):
        user_pan_exists = shipmentproductmapping.ordered_product.order. \
            buyer_shop.shop_owner.user_documents. \
            filter(user_document_type='pc').exists()
        if user_pan_exists:
            return False
        return True

    def post(self, request, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        products = ShipmentProducts.objects.filter(ordered_product__id=shipment_id)
        if not products.exists():
            msg = {'is_success': False,
                   'message': ['shipment id is invalid'],
                   'response_data': None,
                   'is_pan_required': False}
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        try:
            for item in products:
                item.delivered_qty = item.shipped_qty - (int(item.returned_qty) + int(item.returned_damage_qty))
                item.save()
            cash_to_be_collected = products.last().ordered_product.cash_to_be_collected()
            is_pan_required = self.is_pan_required(products.last())
        except Exception as e:
            msg = {'is_success': False,
                   'message': [str(e)],
                   'response_data': None,
                   'is_pan_required': False}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            msg = {'is_success': True,
                   'message': ['Shipment Details Updated Successfully!'],
                   'response_data': {'cash_to_be_collected': cash_to_be_collected},
                   'is_pan_required': is_pan_required}
            return Response(msg, status=status.HTTP_201_CREATED)


class ShipmentDeliveryUpdate(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        msg = {'is_success': False, 'message': ['shipment id is invalid'], 'response_data': None}
        try:
            shipment = ShipmentProducts.objects.filter(ordered_product__id=shipment_id)
            shipment_batch = OrderedProductBatch.objects.filter(
                ordered_product_mapping__ordered_product__id=shipment_id)
        except ObjectDoesNotExist:
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        try:
            for item in request.data.get('delivered_items'):
                product = item.get('product', None)
                returned_qty = item.get('returned_qty', None)
                damaged_qty = item.get('returned_damage_qty', None)
                shipped_qty = int(
                    ShipmentProducts.objects.get(ordered_product_id=shipment_id, product=product).shipped_qty)
                if shipped_qty >= int(returned_qty) + int(damaged_qty):
                    delivered_qty = shipped_qty - (int(returned_qty) + int(damaged_qty))
                    initial_returned_qty = int(returned_qty) + int(damaged_qty)
                    ShipmentProducts.objects.filter(ordered_product__id=shipment_id, product=product).update(
                        returned_qty=returned_qty, returned_damage_qty=damaged_qty, delivered_qty=delivered_qty,
                        initial_returned_qty=initial_returned_qty, initial_delivered_qty=delivered_qty,
                        cancellation_date=datetime.now())
                # shipment_product_details = ShipmentDetailSerializer(shipment, many=True)
                else:
                    product_name = Product.objects.get(id=product).product_name
                    text = 'Returned qty and damaged qty is greater than shipped qty for product: ' + product_name
                    msg = {'is_success': False, 'message': [text], 'response_data': None}
                    return Response(msg, status=status.HTTP_400_BAD_REQUEST)

            cash_to_be_collected = shipment.last().ordered_product.cash_to_be_collected()
            msg = {'is_success': True, 'message': ['Shipment Details Updated Successfully!'], 'response_data': None,
                   'cash_to_be_collected': cash_to_be_collected}
            return Response(msg, status=status.HTTP_201_CREATED)
        except Exception as e:
            msg = {'is_success': False,
                   'message': [str(e)],
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)


class ShipmentDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        shipment = ShipmentProducts.objects.filter(ordered_product__id=shipment_id)
        shipment_product_details = ShipmentDetailSerializer(shipment, many=True)
        cash_to_be_collected = shipment.last().ordered_product.cash_to_be_collected()
        msg = {'is_success': True, 'message': ['Shipment Details'],
               'response_data': shipment_product_details.data, 'cash_to_be_collected': cash_to_be_collected}
        return Response(msg, status=status.HTTP_201_CREATED)

    def post(self, *args, **kwargs):
        shipment_id = kwargs.get('shipment')
        msg = {'is_success': False, 'message': ['shipment id is invalid'], 'response_data': None}
        try:
            shipment = ShipmentProducts.objects.filter(ordered_product__id=shipment_id)
        except ObjectDoesNotExist:
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        product = self.request.POST.get('product')
        returned_qty = self.request.POST.get('returned_qty')
        returned_damage_qty = self.request.POST.get('returned_damage_qty')

        shipment_product = ShipmentProducts.objects.get(ordered_product_id=shipment_id, product=product)
        if int(shipment_product.shipped_qty) >= int(
                returned_qty) + int(returned_damage_qty):
            delivered_qty = shipment_product.shipped_qty - int(returned_qty) + int(returned_damage_qty)
            ShipmentProducts.objects.filter(ordered_product__id=shipment_id, product=product).update(
                delivered_qty=delivered_qty, returned_qty=returned_qty, returned_damage_qty=returned_damage_qty)
            # shipment_product_details = ShipmentDetailSerializer(shipment, many=True)
            cash_to_be_collected = shipment.last().ordered_product.cash_to_be_collected()
            msg = {'is_success': True, 'message': ['Shipment Details'], 'response_data': None,
                   'cash_to_be_collected': cash_to_be_collected}
            return Response(msg, status=status.HTTP_201_CREATED)
        else:
            msg = {'is_success': False, 'message': ['Returned qty and damaged qty is greater than shipped qty'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        # else:
        #     msg = {'is_success': False, 'message': ['Phone Number is not Valid'], 'response_data': None}
        #     return Response( msg, status=status.HTTP_400_BAD_REQUEST)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FeedbackData(generics.ListCreateAPIView):
    serializer_class = FeedBackSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        ship_id = self.kwargs.get('ship_id')
        queryset = Feedback.objects.all()
        if ship_id:
            queryset = Feedback.objects.filter(shipment__id=ship_id)
        return queryset

    def create(self, request, *args, **kwargs):
        can_comment = False
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            if ((serializer.data['delivery_experience'] and int(serializer.data['delivery_experience']) > 4) or (
                    serializer.data['overall_product_packaging'] and int(
                serializer.data['overall_product_packaging']) > 4)):
                can_comment = True
            msg = {'is_success': True, 'can_comment': can_comment, 'message': None, 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['shipment_id, user_id or status not found or value exists'],
                   'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        feedback = serializer.save(user=self.request.user)
        return feedback

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True, 'message': [""], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


# class CancelOrder(APIView):
#     authentication_classes = (authentication.TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated,)
#
#     def put(self, request, format=None):
#         """
#         Return error message
#         """
#         msg = {'is_success': False,
#                'message': ['Sorry! Order cannot be cancelled from the APP'],
#                'response_data': None}
#         return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
#         # try:
#         #     order = Order.objects.get(buyer_shop__shop_owner=request.user,
#         #                               pk=request.data['order_id'])
#         # except ObjectDoesNotExist:
#         #     msg = {'is_success': False,
#         #            'message': ['Order is not associated with the current user'],
#         #            'response_data': None}
#         #     return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
#         #
#         # serializer = CancelOrderSerializer(order, data=request.data,
#         #                                    context={'order': order})
#         # if serializer.is_valid():
#         #     serializer.save()
#         #     msg = {'is_success': True,
#         #            'message': ["Order Cancelled Successfully!"],
#         #            'response_data': serializer.data}
#         #     return Response(msg, status=status.HTTP_200_OK)
#         # else:
#         #     return format_serializer_errors(serializer.errors)


class RetailerShopsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        mobile_number = self.request.GET.get('mobile_number')
        msg = {'is_success': False, 'message': [''], 'response_data': None}
        if Shop.objects.filter(Q(shop_owner__phone_number=mobile_number), Q(retiler_mapping__status=True)).exclude(
                ~Q(shop_name_address_mapping__gt=1)).exists():
            shops_list = Shop.objects.filter(shop_owner__phone_number=mobile_number, shop_type=1).exclude(
                ~Q(shop_name_address_mapping__gt=1))
            shops_serializer = RetailerShopSerializer(shops_list, many=True)
            return Response({"message": [""], "response_data": shops_serializer.data, "is_success": True,
                             "is_user_mapped_with_same_sp": True})
        elif get_user_model().objects.filter(phone_number=mobile_number).exists():
            return Response({"message": ["The User is registered but does not have any shop"], "response_data": None,
                             "is_success": True, "is_user_mapped_with_same_sp": False})
        else:
            return Response({"message": ["User is not exists"], "response_data": None, "is_success": False,
                             "is_user_mapped_with_same_sp": False})


class RetailerList(generics.ListAPIView):
    serializer_class = SellerOrderListSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True)

    def get_child_employee(self):
        return ShopUserMapping.objects.filter(Q(manager__in=self.get_manager()) | Q(employee=self.request.user,
                                                                                    employee_group__permissions__codename='can_sales_person_add_shop'),
                                              shop__shop_type__shop_type__in=['r', 'f', 'sp'], status=True)

    def get_shops(self):
        return ShopUserMapping.objects.filter(Q(manager__in=self.get_manager()) | Q(employee=self.request.user,
                                                                                    employee_group__permissions__codename='can_sales_person_add_shop'),
                                              employee__in=self.get_child_employee().values('employee'),
                                              shop__shop_type__shop_type__in=['r', 'f', ], status=True)

    def get_queryset(self):
        shop_emp = self.get_child_employee()
        if not shop_emp.exists():
            shop_emp = self.get_shops()
        return shop_emp.values('shop')

    def list(self, request, *args, **kwargs):
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
        shop_list = self.get_queryset()
        queryset = Shop.objects.filter(id__in=shop_list, status=True).order_by('shop_name')

        params = request.query_params
        info_logger.info("RetailerList|query_params {}".format(request.query_params))
        if params.get('retailer_name') is not None:
            queryset = queryset.filter(shop_name__icontains=params.get('retailer_name'))

        if queryset.exists():
            serializer = ShopSerializer(queryset, many=True)
            if serializer.data:
                msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class SellerOrderList(generics.ListAPIView):
    serializer_class = SellerOrderListSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination
    is_manager = False

    def get_manager(self):
        return ShopUserMapping.objects.filter(employee=self.request.user, status=True)

    def get_child_employee(self):
        return ShopUserMapping.objects.filter(manager__in=self.get_manager(),
                                              shop__shop_type__shop_type__in=['r', 'f', 'sp'],
                                              status=True)

    def get_shops(self):
        return ShopUserMapping.objects.filter(employee__in=self.get_child_employee().values('employee'),
                                              shop__shop_type__shop_type__in=['r', 'f'], status=True)

    def get_employee(self):
        return ShopUserMapping.objects.filter(employee=self.request.user,
                                              employee_group__permissions__codename='can_sales_person_add_shop',
                                              shop__shop_type__shop_type__in=['r', 'f'], status=True)

    def get_order_status(self, status):
        order_status_dict = {
            'new': [Order.ORDERED, Order.PICKUP_CREATED, Order.PICKING_ASSIGNED, Order.PICKING_COMPLETE,
                    Order.FULL_SHIPMENT_CREATED, Order.PARTIAL_SHIPMENT_CREATED, Order.READY_TO_DISPATCH],
            'in_transit': [Order.DISPATCHED],
            'completed': [Order.PARTIAL_DELIVERED, Order.DELIVERED, Order.CLOSED, Order.COMPLETED],
            'cancelled': [Order.CANCELLED]
        }
        return order_status_dict.get(status)

    def get_queryset(self):
        shop_emp = self.get_employee()
        if not shop_emp.exists():
            shop_emp = self.get_shops()
            if shop_emp:
                self.is_manager = True
        return shop_emp.values('shop')

    def list(self, request, *args, **kwargs):
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}
        current_url = request.get_host()
        shop_list = self.get_queryset()
        # queryset = Order.objects.filter(buyer_shop__id__in=shop_list).order_by('-created_at') if self.is_manager \
        #             else Order.objects.filter(buyer_shop__id__in=shop_list, ordered_by=request.user)\
        #                               .order_by('-created_at')
        queryset = Order.objects.filter(buyer_shop__id__in=shop_list).order_by('-created_at')

        params = request.query_params
        info_logger.info("SellerOrderList|query_params {}".format(request.query_params))
        if params.get('order_status') is not None:
            order_status_list = self.get_order_status(params['order_status'])
            if order_status_list is not None:
                queryset = queryset.filter(order_status__in=order_status_list)

        if params.get('retailer_id') is not None:
            queryset = queryset.filter(buyer_shop_id=params.get('retailer_id'))
        elif params.get('retailer_name') is not None:
            queryset = queryset.filter(buyer_shop__shop_name__icontains=params.get('retailer_name'))
        if not queryset.exists():
            msg = {'is_success': False, 'message': ['Order not found'], 'response_data': None}
        else:
            objects = self.pagination_class().paginate_queryset(queryset, request)
            users_list = [v['employee_id'] for v in self.get_queryset().values('employee_id')]
            serializer = self.serializer_class(objects, many=True,
                                               context={'current_url': current_url, 'sales_person_list': users_list})
            if serializer.data:
                msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class RescheduleReason(generics.ListCreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ShipmentReschedulingSerializer

    def list(self, request, *args, **kwargs):
        data = [{'name': reason[0], 'display_name': reason[1]} for reason in ShipmentRescheduling.RESCHEDULING_REASON]
        msg = {'is_success': True, 'message': None, 'response_data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if ShipmentRescheduling.objects.filter(shipment=request.data.get('shipment')).exists():
            msg = {'is_success': False, 'message': ['A shipment cannot be rescheduled more than once.'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            products = ShipmentProducts.objects.filter(ordered_product__id=request.data.get('shipment'))
            for item in products:
                item.delivered_qty = item.returned_qty = item.returned_damage_qty = 0
                item.save()
            self.update_shipment(request.data.get('shipment'))
            update_trip_status(request.data.get('trip'))
            msg = {'is_success': True, 'message': ['Reschedule successfully done.'], 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['have some issue'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        shipment = OrderedProduct.objects.get(pk=self.request.data.get('shipment'))
        return serializer.save(created_by=self.request.user, trip=shipment.trip, rescheduled_count=1)

    def update_shipment(self, id):
        shipment = OrderedProduct.objects.get(pk=id)
        shipment.shipment_status = OrderedProduct.RESCHEDULED
        shipment.trip = None
        shipment.save()
        shipment_reschedule_inventory_change([shipment])


class NotAttemptReason(generics.ListCreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ShipmentNotAttemptSerializer

    def list(self, request, *args, **kwargs):
        data = [{'name': reason[0], 'display_name': reason[1]} for reason in ShipmentNotAttempt.NOT_ATTEMPT_REASON]
        msg = {'is_success': True, 'message': None, 'response_data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if ShipmentNotAttempt.objects.filter(shipment=request.data.get('shipment'),
                                             created_at__date=datetime.now().date()).exists():
            msg = {'is_success': False, 'message': ['A shipment cannot be mark not attempt more than once in a day.'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            products = ShipmentProducts.objects.filter(ordered_product__id=request.data.get('shipment'))
            for item in products:
                item.delivered_qty = item.returned_qty = item.returned_damage_qty = 0
                item.save()
            self.update_shipment(request.data.get('shipment'))
            update_trip_status(request.data.get('trip'))
            msg = {'is_success': True, 'message': ['Not Attempt successfully done.'], 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['have some issue'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        shipment = OrderedProduct.objects.get(pk=self.request.data.get('shipment'))
        return serializer.save(created_by=self.request.user, trip=shipment.trip)

    def update_shipment(self, id):
        shipment = OrderedProduct.objects.get(pk=id)
        shipment.shipment_status = OrderedProduct.NOT_ATTEMPT
        shipment.trip = None
        shipment.save()
        shipment_not_attempt_inventory_change([shipment])


def update_trip_status(trip_id):
    shipment_status_list = ['FULLY_DELIVERED_AND_COMPLETED', 'PARTIALLY_DELIVERED_AND_COMPLETED',
                            'FULLY_RETURNED_AND_COMPLETED', 'RESCHEDULED', 'NOT_ATTEMPT']
    order_product = OrderedProduct.objects.filter(trip_id=trip_id)
    return_orders = ReturnOrder.objects.filter(last_mile_trip_returns__trip_id=trip_id,
                                               return_status__in=[ReturnOrder.RETURN_INITIATED]).count()
    if order_product.exclude(shipment_status__in=shipment_status_list).count() == 0:
        # Trip.objects.filter(pk=trip_id).update(trip_status=Trip.COMPLETED, completed_at=datetime.now())
        # updating order status when trip is completed
        trip_instance = Trip.objects.get(id=trip_id)
        trip_shipments = trip_instance.rt_invoice_trip.values_list('id', flat=True)
        Order.objects.filter(rt_order_order_product__in=trip_shipments).update(order_status=Order.COMPLETED)
    if order_product.exclude(shipment_status__in=shipment_status_list).count() == 0 and return_orders == 0:
        Trip.objects.filter(pk=trip_id).update(trip_status=Trip.COMPLETED, completed_at=datetime.now())

class ReturnReason(generics.UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ShipmentReturnSerializer

    def get(self, request, *args, **kwargs):
        data = [{'name': reason[0], 'display_name': reason[1]} for reason in OrderedProduct.RETURN_REASON]
        msg = {'is_success': True, 'message': None, 'response_data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def get_queryset(self):
        return OrderedProduct.objects.get(pk=self.request.data.get('id'))

    def patch(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_queryset()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            # For creating credit note
            # shipment = OrderedProduct.objects.get(id=request.data.get('id'))
            # create_credit_note(shipment)
            msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': ['have some issue'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)


class RefreshEs(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        shop_id = None
        shop_id = self.request.GET.get('shop_id')
        info_logger.info('RefreshEs| shop {}, Started'.format(shop_id))
        upload_shop_stock(shop_id)
        info_logger.info('RefreshEs| shop {}, Ended'.format(shop_id))
        return Response({"message": "Shop data updated on ES", "response_data": None, "is_success": True})


def refresh_cron_es():
    shop_id = int(get_config('current_wh_active', 50484))
    info_logger.info('RefreshEs| shop {}, Started'.format(shop_id))
    upload_shop_stock(shop_id)
    info_logger.info('RefreshEs| shop {}, Ended'.format(shop_id))
    return Response()


class RefreshEsRetailer(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
            Refresh retailer Products Es
        """
        shops = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, pos_enabled=True)
        input_shop_id = self.request.GET.get('shop_id')
        if input_shop_id:
            shops = shops.filter(id=input_shop_id)

        if not shops.exists():
            return api_response("No shops found")
        for shop in shops:
            shop_id = shop.id
            info_logger.info('RefreshEsRetailer | shop {}, Started'.format(shop_id))
            all_products = RetailerProduct.objects.filter(shop=shop)
            try:
                update_es(all_products, shop_id)
            except Exception as e:
                info_logger.info("error in retailer shop refresh es {}".format(shop_id))
                info_logger.info(e)
            info_logger.info('RefreshEsRetailer | shop {}, Ended'.format(shop_id))
        return api_response("Shop data updated on ES", None, status.HTTP_200_OK, True)


class PosUserShopsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    def get(self, request, *args, **kwargs):
        user = request.user
        search_text = request.GET.get('search_text')
        user_mappings = PosShopUserMapping.objects.filter(user=user, status=True, shop__shop_type__shop_type='f',
                                                          shop__status=True, shop__pos_enabled=True,
                                                          shop__approval_status=2)
        if search_text:
            user_mappings = user_mappings.filter(shop__shop_name__icontains=search_text)
        # request_shops = self.pagination_class().paginate_queryset(user_mappings, self.request)
        data = PosShopSerializer(user_mappings, many=True).data
        if data:
            return api_response("Shops Mapped", data, status.HTTP_200_OK, True)
        else:
            return api_response("No Shops Mapped", None, status.HTTP_200_OK)


class PosShopUsersList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        shop = kwargs['shop']
        data = dict()
        data['shop_owner'] = PosShopUserSerializer(shop.shop_owner).data
        pos_shop_users = PosShopUserMapping.objects.filter(shop=shop, user__is_staff=False).order_by('-id')
        if self.request.GET.get('is_delivery_person', False):
            pos_shop_users = pos_shop_users.filter(Q(user_type='delivery_person') | Q(is_delivery_person=True))
        search_text = self.request.GET.get('search_text')
        if search_text:
            pos_shop_users = pos_shop_users.filter(Q(user__phone_number__icontains=search_text) |
                                                   Q(user__first_name__icontains=search_text))
        # pos_shop_users = pos_shop_users.order_by('-status')
        request_users = self.pagination_class().paginate_queryset(pos_shop_users, self.request)
        data['user_mappings'] = PosShopUserMappingListSerializer(request_users, many=True).data
        return api_response("Shop Users", data, status.HTTP_200_OK, True)


class OrderCommunication(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    def post(self, request, *args, **kwargs):

        com_type, pk, shop = kwargs['type'], kwargs['pk'], kwargs['shop']

        if com_type == 'invoice':
            return self.resend_invoice(pk, shop)
        elif com_type == 'credit-note':
            return self.resend_credit_note(pk, shop)
        else:
            return api_response("Invalid communication type")

    def resend_invoice(self, pk, shop):
        """
            Resend invoice for pos order
        """
        try:
            order = Order.objects.get(pk=pk, seller_shop=shop, ordered_cart__cart_type__in=['BASIC', 'ECOM'])
        except ObjectDoesNotExist:
            return api_response("Could not find order to send invoice for")

        if pdf_generation_retailer(self.request, order.id, False):
            return api_response("Invoice sent successfully!", None, status.HTTP_200_OK, True)
        else:
            return api_response("Invoice could not be sent. Please try again later", None,
                                status.HTTP_500_INTERNAL_SERVER_ERROR, False)

    def resend_credit_note(self, pk, shop):
        """
            Resend credit note for pos order return
        """
        try:
            order_return = OrderReturn.objects.get(pk=pk, order__seller_shop=shop,
                                                   order__ordered_cart__cart_type__in=['BASIC', 'ECOM'])
        except ObjectDoesNotExist:
            return api_response("Could not find return to send credit note for")

        try:
            credit_note = CreditNote.objects.get(order_return=order_return)
        except ObjectDoesNotExist:
            return api_response("Could not find credit note")

        order = order_return.order
        ordered_product = OrderedProduct.objects.get(order=order)
        returned_products = ReturnItems.objects.filter(return_id=order_return)

        if pdf_generation_return_retailer(self.request, order, ordered_product, order_return, returned_products,
                                          credit_note, False):
            return api_response("Credit note sent successfully!", None, status.HTTP_200_OK, True)
        else:
            return api_response("Credit note could not be sent. Please try again later", None,
                                status.HTTP_500_INTERNAL_SERVER_ERROR, False)


class ShipmentView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EcomShipmentSerializer

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post(self, request, *args, **kwargs):
        shop = kwargs['shop']
        serializer = self.serializer_class(data=self.request.data, context={'shop': shop})
        if serializer.is_valid():
            with transaction.atomic():
                data = serializer.validated_data
                products_info, order_id = data['products'], data['order_id']
                order = Order.objects.filter(pk=order_id, seller_shop=shop,
                                             order_status__in=['ordered', Order.PICKUP_CREATED],
                                             ordered_cart__cart_type='ECOM').last()
                # Create shipment
                shipment = OrderedProduct.objects.filter(order=order).last()
                if not shipment:
                    shipment = OrderedProduct(order=order)
                    shipment.save()

                for product_map in products_info:
                    cart_product_mapping = CartProductMapping.objects.filter(cart=order.ordered_cart,
                                                                             retailer_product_id=product_map[
                                                                                 'product_id'],
                                                                             product_type=1).last()
                    if cart_product_mapping and cart_product_mapping.qty > product_map['picked_qty'] \
                            and product_map['product_type'] == 1:
                        retailer_product = RetailerProduct.objects.filter(id=product_map['product_id'],
                                                                          shop=shop).last()
                        retailer_product.online_enabled = False
                        retailer_product.online_disabled_status = product_map['online_disabled_status']
                        retailer_product.save()
                    elif cart_product_mapping and cart_product_mapping.qty == product_map['picked_qty'] \
                            and product_map['product_type'] == 1:
                        retailer_product = RetailerProduct.objects.filter(id=product_map['product_id'],
                                                                          shop=shop).last()
                        retailer_product.online_enabled = True
                        retailer_product.online_disabled_status = None
                        retailer_product.save()
                    product_id, qty, product_type = product_map['product_id'], product_map['picked_qty'], product_map[
                        'product_type']
                    ordered_product_mapping, _ = ShipmentProducts.objects.get_or_create(ordered_product=shipment,
                                                                                        retailer_product_id=product_id,
                                                                                        product_type=product_type)
                    ordered_product_mapping.shipped_qty = qty
                    ordered_product_mapping.picked_pieces = qty
                    ordered_product_mapping.selling_price = product_map['selling_price']
                    ordered_product_mapping.save()
                    # Item Batch
                    batch = OrderedProductBatch.objects.filter(ordered_product_mapping=ordered_product_mapping).last()
                    if not batch:
                        OrderedProductBatch.objects.create(ordered_product_mapping=ordered_product_mapping,
                                                           pickup_quantity=qty, quantity=qty, delivered_qty=qty)
                    else:
                        batch.pickup_quantity = qty
                        batch.quantity = qty
                        batch.delivered_qty = qty
                        batch.save()

                order.order_status = Order.PICKUP_CREATED
                order.ordered_by = self.request.user
                order.save()
                return api_response("Pickup recorded", None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    def get_combo_offers(self, order):
        """
            Get combo offers mapping with product purchased
        """
        offers = order.ordered_cart.offers
        product_combo_map = {}
        cart_free_product = {}
        if offers:
            for offer in offers:
                if offer['type'] == 'combo':
                    product_combo_map[int(offer['item_id'])] = product_combo_map[int(offer['item_id'])] + [offer] \
                        if int(offer['item_id']) in product_combo_map else [offer]
                if offer['type'] == 'free_product':
                    cart_free_product = offer
        return product_combo_map, cart_free_product


class EcomPaymentView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_ecom_user
    def post(self, request, *args, **kwags):
        try:
            hash_string = self.request.data.get('hash_string')
            hash_string += str(config('PAYU_SALT'))
            hash_string = sha512(hash_string.encode()).hexdigest().lower()
            return api_response("", hash_string, status.HTTP_200_OK, True)
        except:
            return api_response("Something went wrong!")

    @check_ecom_user
    def get(self, request, *args, **kwargs):
        queryset = PaymentType.objects.filter(app__in=['ecom', 'both'])
        queryset = SmallOffsetPagination().paginate_queryset(queryset, request)
        serializer = PaymentTypeSerializer(queryset, many=True)
        msg = "" if queryset else "No payment found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)


class EcomPaymentSuccessView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def post(self, request, *args, **kwags):
        return render(request, "ecom/payment_success.html", {'media_url': AWS_MEDIA_URL})


class EcomPaymentFailureView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def post(self, request, *args, **kwags):
        return render(request, "ecom/payment_failed.html", {'media_url': AWS_MEDIA_URL})


class ShipmentProductView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OrderedProduct.objects. \
        select_related('order', 'order__buyer_shop', 'order__buyer_shop__shop_owner'). \
        prefetch_related('rt_order_product_order_product_mapping',
                         'rt_order_product_order_product_mapping__rt_ordered_product_mapping')
    serializer_class = ShipmentProductSerializer

    def get(self, request):
        """ GET API for Shipment Product """
        info_logger.info("Shipment Product GET api called.")
        if request.GET.get('id'):
            """ Get Shipment Products for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shipment_products_data = id_validation['data']
            shipment_product_total_count = shipment_products_data.count()
            serializer = self.serializer_class(shipment_products_data, many=True)
            msg = f"total count {shipment_product_total_count}"
            return get_response(msg, serializer.data, True)
        return get_response("'id' | This is mandatory.")


class ReturnOrderProductView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ReturnOrderTripProductSerializer

    def get(self, request):
        if request.GET.get('id'):
            try:
                return_order = ReturnOrder.objects.get(id=request.GET.get('id'))
                serializer = self.serializer_class(return_order)
                msg = f"return order products"
                return get_response(msg, serializer.data, True)
            except ReturnOrder.DoesNotExist:
                return get_response("Return Order not found.")
        return get_response("'id' | This is required.")


class ProcessShipmentView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OrderedProductMapping.objects. \
        all()
    serializer_class = RetailerOrderedProductMappingSerializer

    def get(self, request):
        """ GET API for Process Shipment """
        info_logger.info("Process Shipment GET api called.")

        if request.GET.get('id'):
            """ Get Process Shipment for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            process_shipments_data = id_validation['data']

        else:
            """ Get Process Shipment for specific Shipment and batch Id """

            if request.GET.get('shipment_id') and not re.match("^\d+$", str(request.GET.get('shipment_id'))):
                return get_response('please provide valid shipment_id', False)
            if not request.GET.get('shipment_id') or not (request.GET.get('batch_id') or request.GET.get('ean_code')):
                return get_response('please provide id / shipment_id & batch_id to get shipment product detail', False)
            process_shipments_data = self.filter_shipment_data()

        serializer = self.serializer_class(process_shipments_data, many=True)
        msg = "" if process_shipments_data else "no shipment product found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_coordinator_supervisor_qc_executive
    def put(self, request):
        """ PUT API for Process Shipment Updation """

        info_logger.info("Process Shipment PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to process_shipment', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        process_shipment_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=process_shipment_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(last_modified_by=request.user)
            info_logger.info("Process Shipment Updated Successfully.")
            return get_response('process_shipment updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def filter_shipment_data(self):
        """ Filters the Shipment data based on request"""
        shipment_id = self.request.GET.get('shipment_id')
        batch_id = self.request.GET.get('batch_id')
        ean_code = self.request.GET.get('ean_code')

        '''Filters using shipment_id & batch_id'''
        if shipment_id:
            self.queryset = self.queryset.filter(ordered_product__id=shipment_id)

        if batch_id:
            self.queryset = self.queryset.filter(rt_ordered_product_mapping__batch_id=batch_id)

        if ean_code:
            self.queryset = self.queryset.filter(product__product_ean_code__startswith=ean_code)

        return self.queryset.distinct('id')


class ShipmentQCView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShipmentQCSerializer
    queryset = OrderedProduct.objects.filter(~Q(order__order_status=Order.CANCELLED)). \
        annotate(status=Case(
        When(shipment_status__in=[OrderedProduct.SHIPMENT_CREATED, OrderedProduct.QC_STARTED],
             then=Value(OrderedProduct.SHIPMENT_CREATED)),
        default=F('shipment_status'))). \
        select_related('order', 'order__seller_shop', 'order__shipping_address', 'order__shipping_address__city',
                       'order__shipping_address__state', 'order__shipping_address__pincode_link', 'invoice', 'qc_area'). \
        prefetch_related('qc_area__qc_desk_areas', 'qc_area__qc_desk_areas__qc_executive'). \
        only('id', 'order__order_no', 'order__seller_shop__id', 'order__seller_shop__shop_name',
             'order__buyer_shop__id', 'order__buyer_shop__shop_name', 'order__shipping_address__pincode',
             'order__dispatch_center__id', 'order__dispatch_center__shop_name', 'order__dispatch_delivery',
             'order__shipping_address__pincode_link_id', 'order__shipping_address__nick_name',
             'order__shipping_address__address_line1', 'order__shipping_address__address_contact_name',
             'order__shipping_address__address_contact_number', 'order__shipping_address__address_type',
             'order__shipping_address__city_id', 'order__shipping_address__city__city_name',
             'order__shipping_address__state__state_name', 'shipment_status', 'invoice__invoice_no', 'qc_area__id',
             'qc_area__area_id', 'qc_area__area_type', 'created_at'). \
        order_by('-id')

    def get(self, request):

        if request.GET.get('id'):
            """ Get Shipments for specific warehouse """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            self.queryset = id_validation['data']

        else:
            """ GET Shipment List """
            self.queryset = self.search_filter_shipment_data()
            self.queryset = get_logged_user_wise_query_set_for_shipment(request.user, self.queryset)
        shipment_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shipment_data, many=True)
        msg = "" if shipment_data else "no shipment found"
        return get_response(msg, serializer.data, True)

    @check_qc_dispatch_executive
    def put(self, request):
        """ PUT API for shipment update """

        info_logger.info("PUT API for shipment update called.")
        if not request.data.get('data').get('id'):
            return get_response('please provide id to update shipment', False)

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        shipment_data = validate_shipment(self.queryset, int(modified_data['id']))
        if 'error' in shipment_data:
            return get_response(shipment_data['error'])
        modified_data['user'] = request.user
        serializer = self.serializer_class(instance=shipment_data['data'], data=modified_data)
        if serializer.is_valid():
            shipment = serializer.save(updated_by=request.user, data=modified_data)
            return get_response('Shipment updated!', shipment.data)
        result = {"is_success": False, "message": serializer_error(serializer), "response_data": []}
        return Response(result, status=status.HTTP_200_OK)

    def search_filter_shipment_data(self):
        """ Filters the Shipment data based on request"""
        search_text = self.request.GET.get('search_text')
        qc_desk = self.request.GET.get('qc_desk')
        qc_executive = self.request.GET.get('qc_executive')
        date = self.request.GET.get('date')
        status = self.request.GET.get('status')
        city = self.request.GET.get('city')
        city_name = self.request.GET.get('city_name')
        pincode = self.request.GET.get('pincode')
        pincode_no = self.request.GET.get('pincode_no')
        buyer_shop = self.request.GET.get('buyer_shop')
        dispatch_center = self.request.GET.get('dispatch_center')
        trip_id = self.request.GET.get('trip_id')
        availability = self.request.GET.get('availability')
        return_packages = self.request.GET.get('return_packages')

        '''search using warehouse name, product's name'''
        if search_text:
            self.queryset = shipment_search(self.queryset, search_text)

        '''Filters using warehouse, product, zone, date, status, putaway_type_id'''

        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        if qc_desk:
            self.queryset = self.queryset.filter(Q(qc_area__qc_desk_areas__desk_number__icontains=qc_desk) |
                                                 Q(qc_area__qc_desk_areas__name__icontains=qc_desk))

        if qc_executive:
            self.queryset = self.queryset.filter(qc_area__qc_desk_areas__qc_executive=qc_executive)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if city:
            self.queryset = self.queryset.filter(order__shipping_address__city_id=city)

        if city_name:
            self.queryset = self.queryset.filter(order__shipping_address__city__city_name__icontains=city_name)

        if pincode_no:
            self.queryset = self.queryset.filter(order__shipping_address__pincode=pincode_no)

        if pincode:
            self.queryset = self.queryset.filter(order__shipping_address__pincode_link_id=pincode)

        if buyer_shop:
            self.queryset = self.queryset.filter(order__buyer_shop_id=buyer_shop)

        if return_packages and return_packages in ['0', '1', 0, 1]:
            if int(return_packages):
                self.queryset = self.queryset.filter(order__dispatch_delivery=True,
                                                     shipment_packaging__movement_type=ShipmentPackaging.RETURNED)

        return self.queryset.distinct('id')


class ShipmentStatusList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for Shipment Status """
        fields = ['id', 'status']
        data = [dict(zip(fields, d)) for d in OrderedProduct.SHIPMENT_STATUS]
        msg = ""
        return get_response(msg, data, True)


class ShipmentCityFilterView(generics.GenericAPIView):
    serializer_class = CitySerializer
    permission_classes = (AllowAny,)
    queryset = City.objects.all()

    def get(self, request):
        """ GET Shop List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = self.city_search(search_text)
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no city found"
        return get_response(msg, serializer.data, True)

    def city_search(self, search_text):
        '''
        search using city_name & state_name based on criteria that matches
        '''
        queryset = self.queryset.filter(Q(city_name__icontains=search_text) |
                                        Q(state__state_name__icontains=search_text))
        return queryset


class ShipmentPincodeFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShipmentPincodeFilterSerializer
    queryset = Pincode.objects.all()

    def get(self, request):
        self.queryset = self.search_filter_pincode()
        pincode_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(pincode_data, many=True)
        msg = "" if pincode_data else "no pincode found"
        return get_response(msg, serializer.data, True)

    def search_filter_pincode(self):
        """ Filters the Shipment data based on request"""
        search_text = self.request.GET.get('search_text')
        city = self.request.GET.get('city')

        if search_text:
            self.queryset = self.queryset.filter(Q(pincode__icontains=search_text) |
                                                 Q(city__city_name__icontains=search_text))

        if city:
            self.queryset = self.queryset.filter(city_id=city)

        return self.queryset.distinct('pincode')


class ShipmentShopFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    queryset = Shop.objects.filter(shop_type__shop_type__in=['r', 'f'], status=True, approval_status=2). \
        prefetch_related('shop_owner'). \
        only('id', 'shop_name', 'shop_owner', 'shop_owner__phone_number', 'shop_type'). \
        order_by('-id')
    serializer_class = ShopBasicSerializer

    def get(self, request):
        """ GET Shop List """
        self.queryset = self.shop_search()
        shop = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop, many=True)
        msg = "" if shop else "no shop found"
        return get_response(msg, serializer.data, True)

    def shop_search(self):
        '''
        search using shop_name & parent shop based on criteria that matches
        '''

        search_text = self.request.GET.get('search_text')
        city = self.request.GET.get('city')
        pincode = self.request.GET.get('pincode')

        if search_text:
            self.queryset = self.queryset.filter(Q(shop_name__icontains=search_text) | Q(
                retiler_mapping__parent__shop_name__icontains=search_text))
        if city:
            self.queryset = self.queryset.filter(shop_name_address_mapping__address_type='shipping',
                                                 shop_name_address_mapping__city_id=city)
        if pincode:
            self.queryset = self.queryset.filter(shop_name_address_mapping__address_type='shipping',
                                                 shop_name_address_mapping__pincode=pincode)
        return self.queryset


class ShipmentProductRejectionReasonList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get shipment package rejection reason list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in OrderedProductBatch.REJECTION_REASON_CHOICE]
        msg = ""
        return get_response(msg, data, True)


class PackagingTypeList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get packaging type list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in ShipmentPackaging.PACKAGING_TYPE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class DispatchItemsView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShipmentPackaging.objects.order_by('packaging_type')
    serializer_class = DispatchItemsSerializer

    # @check_whc_manager_dispatch_executive
    def get(self, request):
        '''
        API to get all the packages for a shipment
        '''
        if request.GET.get('id'):
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            all_packages = int(request.GET.get('get_all', 0))
            if not all_packages:
                self.queryset = id_validation['data']
            else:
                ## Return all the packages belonging to the same shipment
                shipment_id = ShipmentPackaging.objects.get(id=request.GET.get('id')).shipment_id
                self.queryset = self.queryset.filter(shipment_id=shipment_id)
        else:
            if not request.GET.get('shipment_id'):
                return get_response("'shipment_id' | This is mandatory")
            self.queryset = self.filter_packaging_items()
        dispatch_items = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(dispatch_items, many=True)
        msg = "" if dispatch_items else "no dispatch details found"
        return get_response(msg, serializer.data, True)

    def filter_packaging_items(self):
        shipment_id = self.request.GET.get('shipment_id')
        package_status = self.request.GET.get('package_status')
        movement_type = self.request.GET.get('movement_type')

        if shipment_id:
            self.queryset = self.queryset.filter(shipment_id=shipment_id)

        if package_status:
            self.queryset = self.queryset.filter(status=package_status)

        if movement_type:
            self.queryset = self.queryset.filter(movement_type=movement_type)
        else:
            self.queryset = self.queryset.filter(movement_type=ShipmentPackaging.DISPATCH)
        return self.queryset


class DispatchItemsUpdateView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShipmentPackaging.objects.all()
    serializer_class = DispatchItemsSerializer

    @check_dispatch_executive
    def put(self, request):

        '''
        API to mark dispatch packages as ready to be dispatched
        '''

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to process item', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])

        if 'shipment_id' not in modified_data:
            return get_response('please provide shipment id to process this item', False)

        dispatch_data = validate_shipment_dispatch_item(self.queryset, int(modified_data['id']),
                                                        int(modified_data['shipment_id']))
        if 'error' in dispatch_data:
            return get_response(dispatch_data['error'])
        serializer = self.serializer_class(instance=dispatch_data['data'], data=modified_data)
        if serializer.is_valid():
            dispatch_item = serializer.save(updated_by=request.user, data=modified_data)
            return get_response('Dispatch updated!', serializer.data)
        result = {"is_success": False, "message": serializer_error(serializer), "response_data": []}
        return Response(result, status=status.HTTP_200_OK)


class DispatchDashboardView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OrderedProduct.objects.filter(
        shipment_status__in=[OrderedProduct.READY_TO_SHIP, OrderedProduct.MOVED_TO_DISPATCH])
    serializer_class = DispatchDashboardSerializer

    @check_whc_manager_dispatch_executive
    def get(self, request):
        """ GET API for order status summary """
        info_logger.info("Dispatch Status Summary GET api called.")
        """ GET Dispatch Status Summary List """

        self.queryset = get_logged_user_wise_query_set_for_dispatch(self.request.user, self.queryset)
        self.queryset = self.filter_dispatch_summary_data()
        dispatch_summary_data = {"total": 0, "qc_done": 0, "moved_to_dispatch": 0}
        for obj in self.queryset:
            if obj.shipment_status == OrderedProduct.READY_TO_SHIP:
                dispatch_summary_data['total'] += 1
                dispatch_summary_data['qc_done'] += 1
            if obj.shipment_status == OrderedProduct.MOVED_TO_DISPATCH:
                dispatch_summary_data['total'] += 1
                dispatch_summary_data['moved_to_dispatch'] += 1
            # elif obj.shipment_status == OrderedProduct.READY_TO_DISPATCH:
            #     dispatch_summary_data['total'] += 1
            #     dispatch_summary_data['ready_to_dispatch'] += 1
            # elif obj.shipment_status == OrderedProduct.OUT_FOR_DELIVERY:
            #     dispatch_summary_data['total'] += 1
            #     dispatch_summary_data['out_for_delivery'] += 1
            # elif obj.shipment_status == OrderedProduct.RESCHEDULED:
            #     dispatch_summary_data['total'] += 1
            #     dispatch_summary_data['rescheduled'] += 1
        serializer = self.serializer_class(dispatch_summary_data)
        msg = "" if dispatch_summary_data else "no dispatch summary found"
        return get_response(msg, serializer.data, True)

    def filter_dispatch_summary_data(self):
        selected_date = self.request.GET.get('date')
        data_days = self.request.GET.get('data_days')

        if selected_date:
            if data_days:
                end_date = datetime.strptime(selected_date, "%Y-%m-%d")
                start_date = end_date - timedelta(days=int(data_days))
                end_date = end_date + timedelta(days=1)
                self.queryset = self.queryset.filter(
                    created_at__gte=start_date.date(), created_at__lt=end_date.date())
            else:
                selected_date = datetime.strptime(selected_date, "%Y-%m-%d")
                self.queryset = self.queryset.filter(created_at__date=selected_date.date())

        return self.queryset


class DownloadShipmentInvoice(APIView):
    """
    This class is creating and downloading single pdf and bulk pdf along with zip for Invoices
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request):
        """
        :param request: request params
        :return: zip folder which contains the pdf files
        """
        shipment_ids = request.data.get('shipment_ids')
        invoice_type = request.data.get('invoice_type', None)
        # check condition for single pdf download using download invoice link
        if len(shipment_ids) == 1:
            # check pk is exist or not for Order product model
            ordered_product = get_object_or_404(OrderedProduct, pk=shipment_ids[0])
            # call pdf generation method to generate pdf and download the pdf
            if invoice_type == 'superstore':
                ordered_product = pdf_superstore_generation(request, ordered_product)
            else:
                pdf_generation(request, ordered_product)
            result = requests.get(ordered_product.invoice.invoice_pdf.url)
            file_prefix = PREFIX_INVOICE_FILE_NAME
            # generate pdf file
            response = single_pdf_file(ordered_product, result, file_prefix)
            # return response
        else:
            # list of file path for every pdf file
            file_path_list = []
            # list of created date for every pdf file
            pdf_created_date = []
            for pk in shipment_ids:
                # check pk is exist or not for Order product model
                ordered_product = get_object_or_404(OrderedProduct, pk=pk)
                # call pdf generation method to generate and save pdf
                if invoice_type == 'superstore':
                    ordered_product = pdf_superstore_generation(request, ordered_product)
                else:
                    pdf_generation(request, ordered_product)
                # append the pdf file path
                file_path_list.append(ordered_product.invoice.invoice_pdf.url)
                # append created date for pdf file
                pdf_created_date.append(ordered_product.created_at)
            # condition to check the download file count
            if len(pdf_created_date) == 1:
                result = requests.get(ordered_product.invoice.invoice_pdf.url)
                file_prefix = PREFIX_INVOICE_FILE_NAME
                # generate pdf file
                response = single_pdf_file(ordered_product, result, file_prefix)
                return response
            else:
                # get merged pdf file name
                prefix_file_name = INVOICE_DOWNLOAD_ZIP_NAME
                merge_pdf_name = create_merge_pdf_name(prefix_file_name, pdf_created_date)
                # call function to merge pdf files
                merged_file_url = merge_pdf_files(file_path_list, merge_pdf_name)
                file_pointer = requests.get(merged_file_url)
                # response = HttpResponse(file_pointer, content_type='application/msword')
                # response['Content-Disposition'] = 'attachment; filename=NameOfFile'
                response = HttpResponse(file_pointer.content, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="{}"'.format(merge_pdf_name)

                return response
        return response


class DispatchPackageRejectionReasonList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get shipment package rejection reason list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in ShipmentPackaging.REASON_FOR_REJECTION]
        msg = ""
        return get_response(msg, data, True)


class OrderPaymentStatusChangeView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Order.objects.order_by('-id')
    serializer_class = OrderPaymentStatusChangeSerializers

    def put(self, request, *args, **kwargs):
        """
            allowed updates to order status
        """
        info_logger.info("Order PUT api called.")
        app_type = self.request.META.get('HTTP_APP_TYPE', '3')

        if app_type == '2':
            return self.put_ecom_order_status_from_pos_app(request, *args, **kwargs)
        elif app_type == '3':
            return self.put_ecom_order_status(request, *args, **kwargs)
        elif app_type == '4':
            return self.put_superstore_order_status(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    @check_pos_shop
    def put_ecom_order_status(self, request, *args, **kwargs):
        """
            Update ecom order
        """
        shop = kwargs['shop']
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return api_response(modified_data['error'])

        if 'id' not in modified_data:
            return api_response('please provide id to update order')

        try:
            order = Order.objects.get(pk=int(modified_data['id']), seller_shop=shop, ordered_cart__cart_type='ECOM',
                                      buyer=self.request.user)
        except ObjectDoesNotExist:
            return api_response('Order Not Found!')

        serializer = self.serializer_class(instance=order, data=modified_data, context={'app-type': 3})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Order Updated Successfully.")
            return api_response('order updated!', serializer.data, status.HTTP_200_OK, True)
        return api_response(serializer_error(serializer), success=False)

    @check_pos_shop
    def put_ecom_order_status_from_pos_app(self, request, *args, **kwargs):
        """
            Update ecom order
        """
        shop = kwargs['shop']
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return api_response(modified_data['error'])

        if 'id' not in modified_data:
            return api_response('please provide id to update order')

        try:
            order = Order.objects.get(pk=int(modified_data['id']), seller_shop=shop, ordered_cart__cart_type='ECOM')
        except ObjectDoesNotExist:
            return api_response('Order Not Found!')

        serializer = self.serializer_class(instance=order, data=modified_data, context={'app-type': 2})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Order Updated Successfully.")
            return api_response('order updated!', serializer.data, status.HTTP_200_OK, True)
        return api_response(serializer_error(serializer), success=False)

    @check_pos_shop
    def put_superstore_order_status(self, request, *args, **kwargs):
        shop = kwargs['shop']
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return api_response(modified_data['error'])

        if 'id' not in modified_data:
            return api_response('please provide id to update order')
        if 'sub_app_type' in modified_data and modified_data['sub_app_type'] == 'pos':
            sub_app_type = 'pos'
        else:
            sub_app_type = 'ecom'

        try:
            if sub_app_type == 'pos':
                ordered_product_mapping = OrderedProductMapping.objects.get(pk=int(modified_data['id']),
                                                                            ordered_product__order__seller_shop=shop,
                                                                            ordered_product__order__ordered_cart__cart_type='SUPERSTORE')
            else:
                ordered_product_mapping = OrderedProductMapping.objects.get(pk=int(modified_data['id']),
                                                                            ordered_product__order__seller_shop=shop,
                                                                            ordered_product__order__ordered_cart__cart_type='SUPERSTORE',
                                                                            ordered_product__order__buyer=request.user)
            order = ordered_product_mapping.ordered_product.order
        except OrderedProductMapping.DoesNotExist:
            return api_response('Order Not Found!')

        serializer = self.serializer_class(instance=order, data=modified_data,
                                           context={'app-type': 4, 'sub-app-type': sub_app_type})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Order Updated Successfully.")
            return api_response('order updated!', serializer.data, status.HTTP_200_OK, True)
        return api_response(serializer_error(serializer), success=False)


class OrderStatusChoicesList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get payment mode choices list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in [(Order.PAYMENT_PENDING, "Payment Pending"),
                                               (Order.PAYMENT_FAILED, "Payment Failed"),
                                               (Order.PAYMENT_APPROVED, "Payment Approved"),
                                               (Order.PAYMENT_COD, "Payment COD")]]
        return api_response('', data, status.HTTP_200_OK, True)


class DeliverBoysList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = get_user_model().objects.values('id', 'phone_number', 'first_name', 'last_name').order_by('-id')
    serializer_class = UserSerializers

    def user_search(self, queryset, search_string):
        """
        This method is used to search using user name & phone number based on criteria that matches
        @param queryset:
        @param search_string:
        @return: queryset
        """
        sts_list = search_string.split(' ')
        for search_text in sts_list:
            queryset = queryset.filter(Q(phone_number__icontains=search_text) | Q(first_name__icontains=search_text)
                                       | Q(last_name__icontains=search_text))
        return queryset

    def get(self, request):
        info_logger.info("Delivery Boys api called.")
        """ GET Delivery Boys List """
        group = Group.objects.get(name='Delivery Boy')
        self.queryset = self.queryset.filter(groups=group)
        warehouse = self.request.GET.get('warehouse')
        if warehouse:
            self.queryset = self.queryset.filter(shop_employee__shop_id=warehouse)
        id = self.request.GET.get('id')
        if id:
            self.queryset = self.queryset.filter(id=id)
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = self.user_search(self.queryset, search_text)
        delivery_boys = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(delivery_boys, many=True)
        msg = "" if delivery_boys else "no delivery boy found"
        return get_response(msg, serializer.data, True)


class VehicleDriverList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = get_user_model().objects.values('id', 'phone_number', 'first_name', 'last_name').order_by('-id')
    serializer_class = UserSerializers

    def user_search(self, queryset, search_string):
        """
        This method is used to search using user name & phone number based on criteria that matches
        @param queryset:
        @param search_string:
        @return: queryset
        """
        sts_list = search_string.split(' ')
        for search_text in sts_list:
            queryset = queryset.filter(Q(phone_number__icontains=search_text) | Q(first_name__icontains=search_text)
                                       | Q(last_name__icontains=search_text))
        return queryset

    def get(self, request):
        info_logger.info("Delivery Boys api called.")
        """ GET Delivery Boys List """
        group = Group.objects.get(name='Vehicle Driver')
        self.queryset = self.queryset.filter(groups=group)
        warehouse = self.request.GET.get('warehouse')
        if warehouse:
            self.queryset = self.queryset.filter(shop_employee__shop_id=warehouse)
        id = self.request.GET.get('id')
        if id:
            self.queryset = self.queryset.filter(id=id)
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = self.user_search(self.queryset, search_text)
        vehicle_drivers = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(vehicle_drivers, many=True)
        msg = "" if vehicle_drivers else "no vehicle driver found"
        return get_response(msg, serializer.data, True)


class DispatchTripsCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = DispatchTrip.objects. \
        annotate(status=Case(
        When(trip_status__in=[DispatchTrip.NEW, DispatchTrip.STARTED], then=Value("PENDING")),
        When(trip_status__in=[DispatchTrip.COMPLETED, DispatchTrip.UNLOADING, ],
             then=Value("COMPLETED")),
        default=F('trip_status'))). \
        select_related('seller_shop', 'seller_shop__shop_owner', 'seller_shop__shop_type',
                       'seller_shop__shop_type__shop_sub_type', 'source_shop', 'source_shop__shop_owner',
                       'source_shop__shop_type', 'source_shop__shop_type__shop_sub_type', 'destination_shop',
                       'destination_shop__shop_owner', 'destination_shop__shop_type',
                       'destination_shop__shop_type__shop_sub_type', 'delivery_boy', 'created_by', 'updated_by'). \
        only('id', 'dispatch_no', 'vehicle_no', 'seller_shop__id', 'seller_shop__status', 'seller_shop__shop_name',
             'seller_shop__shop_type', 'seller_shop__shop_type__shop_type', 'seller_shop__shop_type__shop_sub_type',
             'seller_shop__shop_type__shop_sub_type__retailer_type_name', 'seller_shop__shop_owner',
             'seller_shop__shop_owner__first_name', 'seller_shop__shop_owner__last_name',
             'seller_shop__shop_owner__phone_number', 'source_shop__id', 'source_shop__status',
             'source_shop__shop_name', 'source_shop__shop_type', 'source_shop__shop_type__shop_type',
             'source_shop__shop_type__shop_sub_type', 'source_shop__shop_type__shop_sub_type__retailer_type_name',
             'source_shop__shop_owner', 'source_shop__shop_owner__first_name', 'source_shop__shop_owner__last_name',
             'source_shop__shop_owner__phone_number', 'destination_shop__id', 'destination_shop__status',
             'destination_shop__shop_name', 'destination_shop__shop_type', 'destination_shop__shop_type__shop_type',
             'destination_shop__shop_type__shop_sub_type', 'destination_shop__shop_owner',
             'destination_shop__shop_type__shop_sub_type__retailer_type_name',
             'destination_shop__shop_owner__first_name', 'destination_shop__shop_owner__last_name',
             'destination_shop__shop_owner__phone_number', 'delivery_boy__id', 'delivery_boy__first_name',
             'delivery_boy__last_name', 'delivery_boy__phone_number', 'trip_status', 'starts_at',
             'completed_at', 'opening_kms', 'closing_kms', 'no_of_crates', 'no_of_packets', 'no_of_sacks',
             'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check', 'created_at', 'updated_at',
             'created_by__id', 'created_by__first_name', 'created_by__last_name', 'created_by__phone_number',
             'updated_by__id', 'updated_by__first_name', 'updated_by__last_name', 'updated_by__phone_number', ). \
        order_by('-id')
    serializer_class = DispatchTripCrudSerializers

    @check_whc_manager_dispatch_executive
    def get(self, request):
        """ GET API for Dispatch Trip """
        info_logger.info("Dispatch Trip GET api called.")
        if request.GET.get('id'):
            """ Get Dispatch Trip for specific ID """
            dispatch_trip_total_count = self.queryset.count()
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            dispatch_trips_data = id_validation['data']
        else:
            """ GET Dispatch Trip List """
            self.queryset = get_logged_user_wise_query_set_for_dispatch_trip(request.user, self.queryset)
            self.queryset = self.search_filter_dispatch_trips_data()
            dispatch_trip_total_count = self.queryset.count()
            dispatch_trips_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(dispatch_trips_data, many=True)
        msg = f"total count {dispatch_trip_total_count}" if dispatch_trips_data else "no dispatch_trip found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_dispatch_executive
    def post(self, request):
        """ POST API for Dispatch Trip Creation with Image """

        info_logger.info("Dispatch Trip POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Dispatch Trip Created Successfully.")
            return get_response('dispatch_trip created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_whc_manager_dispatch_executive
    def put(self, request):
        """ PUT API for Dispatch Trip Updation """

        info_logger.info("Dispatch Trip PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update dispatch_trip', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        dispatch_trip_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=dispatch_trip_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Dispatch Trip Updated Successfully.")
            return get_response('dispatch_trip updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_whc_manager_dispatch_executive
    def delete(self, request):
        """ Delete Dispatch Trip """

        info_logger.info("Dispatch Trip DELETE api called.")
        if not request.data.get('dispatch_trip_id'):
            return get_response('please provide dispatch_trip_id', False)
        try:
            for z_id in request.data.get('dispatch_trip_id'):
                dispatch_trip_id = self.queryset.get(id=int(z_id))
                try:
                    trip_mappings = DispatchTripShipmentMapping.objects.filter(trip_id=dispatch_trip_id)
                    if trip_mappings:
                        trip_mappings.delete()
                    dispatch_trip_id.delete()
                except:
                    return get_response(f'can not delete dispatch trip | {dispatch_trip_id.id} | getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid dispatch trip id {z_id}', False)
        return get_response('dispatch trip were deleted successfully!', True)

    def search_filter_dispatch_trips_data(self):
        search_text = self.request.GET.get('search_text')
        seller_shop = self.request.GET.get('seller_shop')
        source_shop = self.request.GET.get('source_shop')
        destination_shop = self.request.GET.get('destination_shop')
        delivery_boy = self.request.GET.get('delivery_boy')
        dispatch_no = self.request.GET.get('dispatch_no')
        dispatch_center = self.request.GET.get('dispatch_center')
        vehicle_no = self.request.GET.get('vehicle_no')
        trip_status = self.request.GET.get('trip_status')
        trip_type = self.request.GET.get('trip_type')
        date = self.request.GET.get('date')
        data_days = self.request.GET.get('data_days')
        status = self.request.GET.get('status')

        '''search using seller_shop name, source_shop's firstname  and destination_shop's firstname'''
        if search_text:
            self.queryset = dispatch_trip_search(self.queryset, search_text)

        '''
            Filters using seller_shop, source_shop, destination_shop, delivery_boy, dispatch_no, vehicle_no, trip_status
        '''
        if seller_shop:
            self.queryset = self.queryset.filter(seller_shop__id=seller_shop)

        if source_shop:
            self.queryset = self.queryset.filter(source_shop__id=source_shop)

        if destination_shop:
            self.queryset = self.queryset.filter(destination_shop__id=destination_shop)

        if delivery_boy:
            self.queryset = self.queryset.filter(delivery_boy__id=delivery_boy)

        if dispatch_no:
            self.queryset = self.queryset.filter(dispatch_no=dispatch_no)

        if dispatch_center:
            self.queryset = self.queryset.filter(
                Q(source_shop_id=dispatch_center) | Q(destination_shop_id=dispatch_center))

        if vehicle_no:
            self.queryset = self.queryset.filter(vehicle_no=vehicle_no)

        if trip_status:
            self.queryset = self.queryset.filter(trip_status=trip_status)

        if date:
            if data_days:
                end_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = end_date - timedelta(days=int(data_days))
                self.queryset = self.queryset.filter(
                    created_at__date__gte=start_date.date(), created_at__date__lte=end_date.date())
            else:
                created_at = datetime.strptime(date, "%Y-%m-%d")
                self.queryset = self.queryset.filter(created_at__date=created_at)

        if trip_type:
            self.queryset = self.queryset.filter(trip_type=trip_type)
        else:
            self.queryset = self.queryset.filter(trip_type=DispatchTrip.FORWARD)

        if status:
            self.queryset = self.queryset.filter(status=status)

        return self.queryset.distinct('id')


class DispatchTripStatusChangeView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = DispatchTrip.objects. \
        select_related('seller_shop', 'seller_shop__shop_owner', 'seller_shop__shop_type',
                       'seller_shop__shop_type__shop_sub_type', 'source_shop', 'source_shop__shop_owner',
                       'source_shop__shop_type', 'source_shop__shop_type__shop_sub_type', 'destination_shop',
                       'destination_shop__shop_owner', 'destination_shop__shop_type',
                       'destination_shop__shop_type__shop_sub_type', 'delivery_boy', 'created_by', 'updated_by'). \
        prefetch_related('shipments_details'). \
        only('id', 'dispatch_no', 'vehicle_no', 'seller_shop__id', 'seller_shop__status', 'seller_shop__shop_name',
             'seller_shop__shop_type', 'seller_shop__shop_type__shop_type', 'seller_shop__shop_type__shop_sub_type',
             'seller_shop__shop_type__shop_sub_type__retailer_type_name', 'seller_shop__shop_owner',
             'seller_shop__shop_owner__first_name', 'seller_shop__shop_owner__last_name',
             'seller_shop__shop_owner__phone_number', 'source_shop__id', 'source_shop__status',
             'source_shop__shop_name', 'source_shop__shop_type', 'source_shop__shop_type__shop_type',
             'source_shop__shop_type__shop_sub_type', 'source_shop__shop_type__shop_sub_type__retailer_type_name',
             'source_shop__shop_owner', 'source_shop__shop_owner__first_name', 'source_shop__shop_owner__last_name',
             'source_shop__shop_owner__phone_number', 'destination_shop__id', 'destination_shop__status',
             'destination_shop__shop_name', 'destination_shop__shop_type', 'destination_shop__shop_type__shop_type',
             'destination_shop__shop_type__shop_sub_type', 'destination_shop__shop_owner',
             'destination_shop__shop_type__shop_sub_type__retailer_type_name',
             'destination_shop__shop_owner__first_name', 'destination_shop__shop_owner__last_name',
             'destination_shop__shop_owner__phone_number', 'delivery_boy__id', 'delivery_boy__first_name',
             'delivery_boy__last_name', 'delivery_boy__phone_number', 'trip_status', 'starts_at',
             'completed_at', 'opening_kms', 'closing_kms', 'no_of_crates', 'no_of_packets', 'no_of_sacks',
             'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check', 'created_at', 'updated_at',
             'created_by__id', 'created_by__first_name', 'created_by__last_name', 'created_by__phone_number',
             'updated_by__id', 'updated_by__first_name', 'updated_by__last_name', 'updated_by__phone_number', ). \
        order_by('-id')
    serializer_class = DispatchTripStatusChangeSerializers

    @check_whc_manager_dispatch_executive
    def get(self, request):
        """ GET API for Dispatch Trip """
        info_logger.info("Dispatch Trip GET api called.")
        if request.GET.get('id'):
            """ Get Dispatch Trip for specific ID """
            dispatch_trip_total_count = self.queryset.count()
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            dispatch_trips_data = id_validation['data']
        else:
            """ GET Dispatch Trip List """
            self.queryset = get_logged_user_wise_query_set_for_dispatch_trip(request.user, self.queryset)
            self.queryset = self.search_filter_dispatch_trips_data()
            dispatch_trip_total_count = self.queryset.count()
            dispatch_trips_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(dispatch_trips_data, many=True)
        msg = f"total count {dispatch_trip_total_count}" if dispatch_trips_data else "no dispatch_trip found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_dispatch_executive
    def put(self, request):
        """ PUT API for Dispatch Trip Updation """

        info_logger.info("Dispatch Trip PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update dispatch_trip', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        dispatch_trip_instance = id_validation['data'].last()
        if 'vehicle_no' not in modified_data:
            modified_data['vehicle_no'] = dispatch_trip_instance.vehicle_no

        serializer = self.serializer_class(instance=dispatch_trip_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Dispatch Trip Updated Successfully.")
            return get_response('dispatch_trip updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_dispatch_trips_data(self):
        search_text = self.request.GET.get('search_text')
        seller_shop = self.request.GET.get('seller_shop')
        source_shop = self.request.GET.get('source_shop')
        destination_shop = self.request.GET.get('destination_shop')
        delivery_boy = self.request.GET.get('delivery_boy')
        dispatch_no = self.request.GET.get('dispatch_no')
        vehicle_no = self.request.GET.get('vehicle_no')
        trip_status = self.request.GET.get('trip_status')

        '''search using seller_shop name, source_shop's firstname  and destination_shop's firstname'''
        if search_text:
            self.queryset = dispatch_trip_search(self.queryset, search_text)

        '''
            Filters using seller_shop, source_shop, destination_shop, delivery_boy, dispatch_no, vehicle_no, trip_status
        '''
        if seller_shop:
            self.queryset = self.queryset.filter(seller_shop__id=seller_shop)

        if source_shop:
            self.queryset = self.queryset.filter(source_shop__id=source_shop)

        if destination_shop:
            self.queryset = self.queryset.filter(destination_shop__id=destination_shop)

        if delivery_boy:
            self.queryset = self.queryset.filter(delivery_boy__id=delivery_boy)

        if dispatch_no:
            self.queryset = self.queryset.filter(dispatch_no=dispatch_no)

        if vehicle_no:
            self.queryset = self.queryset.filter(vehicle_no=vehicle_no)

        if trip_status:
            self.queryset = self.queryset.filter(trip_status=trip_status)

        return self.queryset.distinct('id')


class ShipmentPackagingView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShipmentPackaging.objects. \
        select_related('crate', 'warehouse', 'warehouse__shop_owner', 'shipment', 'shipment__invoice',
                       'shipment__order', 'shipment__order__shipping_address', 'shipment__order__buyer_shop',
                       'shipment__order__shipping_address__shop_name', 'shipment__order__buyer_shop__shop_owner',
                       'warehouse__shop_type', 'warehouse__shop_type__shop_sub_type', 'created_by', 'updated_by'). \
        prefetch_related('packaging_details', 'trip_packaging_details', 'shipment__trip_shipment',
                         'shipment__rescheduling_shipment', 'shipment__not_attempt_shipment',
                         'shipment__last_mile_trip_shipment'). \
        order_by('-id')
    serializer_class = ShipmentPackageSerializer

    def get(self, request):
        """ GET API for Shipment Packaging """
        info_logger.info("Shipment Packaging GET api called.")
        if not request.GET.get('packaging_id') and not request.GET.get('shipment_id'):
            return get_response("'packaging_id' or 'shipment_id' is required.")
        if request.GET.get('packaging_id'):
            """ Get Shipment Packaging for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('packaging_id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            packaging_data = id_validation['data']
            shipment = packaging_data.last().shipment
            movement_type = packaging_data.last().movement_type
        elif request.GET.get('shipment_id'):
            id_validation = validate_shipment_id(int(request.GET.get('shipment_id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shipment = id_validation['data']
            movement_type = ShipmentPackaging.DISPATCH
        self.queryset = self.queryset.filter(shipment=shipment, movement_type=movement_type)
        serializer = self.serializer_class(
            self.queryset.filter(shipment=shipment, movement_type=movement_type), many=True)
        msg = "" if self.queryset.exists() else "no packaging found"
        return get_response(msg, serializer.data, True)


class ShipmentDetailsByCrateView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OrderedProduct.objects. \
        select_related('order', 'order__seller_shop', 'order__shipping_address', 'order__shipping_address__city',
                       'order__shipping_address__state', 'order__shipping_address__pincode_link', 'invoice', 'qc_area'). \
        prefetch_related('shipment_packaging'). \
        only('id', 'order__order_no', 'order__seller_shop__id', 'order__seller_shop__shop_name',
             'order__buyer_shop__id', 'order__buyer_shop__shop_name', 'order__shipping_address__pincode',
             'order__dispatch_center__id', 'order__dispatch_center__shop_name', 'order__dispatch_delivery',
             'order__shipping_address__pincode_link_id', 'order__shipping_address__nick_name',
             'order__shipping_address__address_line1', 'order__shipping_address__address_contact_name',
             'order__shipping_address__address_contact_number', 'order__shipping_address__address_type',
             'order__shipping_address__city_id', 'order__shipping_address__city__city_name',
             'order__shipping_address__state__state_name', 'shipment_status', 'invoice__invoice_no', 'qc_area__id',
             'qc_area__area_id', 'qc_area__area_type', 'created_at'). \
        order_by('-id')
    serializer_class = ShipmentDetailsByCrateSerializer

    def get(self, request):
        """ GET API for Shipment Details By Crate """
        info_logger.info("Shipment Details By Crate GET api called.")
        if not (request.GET.get('crate_id') or request.GET.get('shipment_id') or request.GET.get('shipment_label_id')):
            return get_response("'crate_id/shipment_label_id/shipment_id' | This is mandatory.")
        """Get Shipment"""
        if request.GET.get('crate_id'):
            """ Get Shipment Details By Crate for specific ID """
            id_validation = get_shipment_by_crate_id(request.GET.get('crate_id'), Crate.DISPATCH)
        elif request.GET.get('shipment_label_id'):
            id_validation = get_shipment_by_shipment_label(request.GET.get('shipment_label_id'))
        elif request.GET.get('shipment_id'):
            id_validation = validate_shipment_id(request.GET.get('shipment_id'))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        shipment_id = id_validation['data']

        serializer = self.serializer_class(self.queryset.filter(id=shipment_id).last())
        msg = "" if shipment_id else "no shipment found"
        return get_response(msg, serializer.data, True)


class ShipmentCratesPackagingView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = LastMileTripShipmentPackages.objects.order_by('-id')
    serializer_class = VerifyShipmentPackageSerializer

    @check_whc_manager_dispatch_executive
    def put(self, request):
        """ PUT API for Dispatch Trip Updation """

        info_logger.info("Dispatch Trip PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'crate_id' not in modified_data or 'shipment_id' not in modified_data:
            return get_response('please provide crate_id and shipment_id to verify shipment crate', False)

        # validations for input id
        id_validation = self.validate_package_by_crate_id(modified_data['crate_id'], modified_data['shipment_id'])
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        packaging_data = id_validation['data']
        modified_data['shop'] = request.user.shop_employee.all().last().shop_id

        serializer = self.serializer_class(instance=packaging_data, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("shipment crate verified successfully.")
            return get_response('shipment crate verified!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def validate_package_by_crate_id(self, crate_id, shipment_id=None):
        shipment = OrderedProduct.objects.filter(id=shipment_id).last()
        if not shipment:
            return {'error': 'Invalid shipment.'}
        trip_package = self.queryset.filter(
            ~Q(trip_shipment__shipment_status=LastMileTripShipmentMapping.CANCELLED),
            trip_shipment__trip=shipment.last_trip, shipment_packaging__shipment=shipment,
            shipment_packaging__crate__crate_id=crate_id).last()
        if not trip_package:
            return {'error': 'Invalid Crate for selected shipment.'}
        return {'data': trip_package}


class VerifyRescheduledShipmentPackagesView(generics.GenericAPIView):
    """
       View to verify shipment packages from a rescheduled shipment.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = LastMileTripShipmentPackages.objects.all()
    serializer_class = VerifyRescheduledShipmentPackageSerializer

    def validate_package_by_shipment_package(self, package_id, shipment_id, trip_id):
        shipment_package = self.queryset.filter(shipment_packaging_id=package_id,
                                                trip_shipment__shipment_id=shipment_id,
                                                trip_shipment__trip_id=trip_id).last()
        if not shipment_package:
            return {"error": "Package does not belong to this trip."}
        if shipment_package.trip_shipment.shipment.shipment_status != OrderedProduct.RESCHEDULED:
            return {"error": f"Invalid Shipment status."}
        return {"data": shipment_package}

    @check_whc_manager_dispatch_executive
    def put(self, request):
        """ PUT API for Dispatch Trip Updation """

        info_logger.info("Dispatch Trip PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'package_id' not in modified_data:
            return get_response("'package_id' | This is required.", False)
        if 'shipment_id' not in modified_data:
            return get_response("'shipment_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)
        if 'return_status' not in modified_data:
            return get_response("'return_status' | This is required.", False)

        # validations for input id
        id_validation = self.validate_package_by_shipment_package(modified_data['package_id'],
                                                                  modified_data['shipment_id'],
                                                                  modified_data['trip_id'])
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        packaging_data = id_validation['data']

        serializer = self.serializer_class(instance=packaging_data, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("shipment package verified successfully.")
            return get_response('shipment package verified!', serializer.data)
        return get_response(serializer_error(serializer), False)


class VerifyNotAttemptShipmentPackagesView(generics.GenericAPIView):
    """
       View to verify shipment packages from a rescheduled shipment.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = LastMileTripShipmentPackages.objects.all()
    serializer_class = VerifyNotAttemptShipmentPackageSerializer

    def validate_package_by_shipment_package(self, package_id, shipment_id, trip_id):
        shipment_package = self.queryset.filter(shipment_packaging_id=package_id,
                                                trip_shipment__shipment_id=shipment_id,
                                                trip_shipment__trip_id=trip_id).last()
        if not shipment_package:
            return {"error": "Package does not belong to this trip."}
        if shipment_package.trip_shipment.shipment.shipment_status != OrderedProduct.NOT_ATTEMPT:
            return {"error": f"Invalid Shipment status."}

        return {"data": shipment_package}

    @check_whc_manager_dispatch_executive
    def put(self, request):
        """ PUT API for Dispatch Trip Updation """

        info_logger.info("Dispatch Trip PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'package_id' not in modified_data:
            return get_response("'package_id' | This is required.", False)
        if 'shipment_id' not in modified_data:
            return get_response("'shipment_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)
        if 'return_status' not in modified_data:
            return get_response("'return_status' | This is required.", False)

        # validations for input id
        id_validation = self.validate_package_by_shipment_package(modified_data['package_id'],
                                                                  modified_data['shipment_id'],
                                                                  modified_data['trip_id'])
        if 'error' in id_validation:
            return get_response(id_validation['error'])

        packaging_data = id_validation['data']

        serializer = self.serializer_class(instance=packaging_data, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("shipment package verified successfully.")
            return get_response('shipment package verified!', serializer.data)
        return get_response(serializer_error(serializer), False)


class VerifyReturnShipmentProductsView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = OrderedProductMapping.objects.all()
    serializer_class = VerifyReturnShipmentProductsSerializer

    @check_whc_manager_dispatch_executive
    def get(self, request):
        """ GET API for Process Shipment """
        info_logger.info("Process Shipment GET api called.")

        if request.GET.get('id'):
            """ Get Process Shipment for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            process_shipments_data = id_validation['data']

        else:
            """ Get Process Shipment for specific Shipment and batch Id """
            if request.GET.get('shipment_id') and (request.GET.get('batch_id') or request.GET.get('product_ean_code')):
                process_shipments_data = self.filter_shipment_data()
            else:
                return get_response('please provide id / shipment_id & (batch_id or product_ean_code) '
                                    'to get shipment product detail', False)

        serializer = self.serializer_class(process_shipments_data, many=True)
        msg = "" if process_shipments_data else "no shipment product found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_dispatch_executive
    def put(self, request):
        """ PUT API for Process Shipment Updation """

        info_logger.info("Process Shipment PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to process_shipment', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        process_shipment_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=process_shipment_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(last_modified_by=request.user)
            info_logger.info("Process Shipment Updated Successfully.")
            return get_response('process_shipment updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def filter_shipment_data(self):
        """ Filters the Shipment data based on request"""
        shipment_id = self.request.GET.get('shipment_id')
        product_ean_code = self.request.GET.get('product_ean_code')
        batch_id = self.request.GET.get('batch_id')

        '''Filters using shipment_id & batch_id'''
        if shipment_id:
            self.queryset = self.queryset.filter(ordered_product__id=shipment_id)

        if product_ean_code:
            self.queryset = self.queryset.filter(product__product_ean_code__startswith=product_ean_code)

        if batch_id:
            self.queryset = self.queryset.filter(rt_ordered_product_mapping__batch_id=batch_id)

        return self.queryset.distinct('id')


class VerifyReturnOrderProductsView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    
    def get(self, request):
        if not request.GET.get('id'):
            return get_response('id for return is mandatory')
        if not request.GET.get('product'):
            return get_response('product id is mandatory')
        try:
            return_order = ReturnOrder.objects.get(id=request.GET.get('id'))
            return_order_product_mapping = return_order.return_order_products.filter(product_id=request.GET.get('product')).last()
            serializer = ReturnOrderProductSerializer(return_order_product_mapping)
            return get_response("return order product", serializer.data, True)
        except ReturnOrder.DoesNotExist:
            return get_response("Return Order not found.")
    
    def put(self, request):
        modified_data = validate_data_format(request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide return id to verify return products', False)
        
        if 'product' not in modified_data:
            return get_response('please provide product id to verify return products', False)
        
        if 'returned_qty' not in modified_data:
            return get_response('Please provide verified returned quantity of products')
        
        if 'damaged_qty' not in modified_data:
            return get_response('Please provide verfied damaged quantity of products')
                        
        try:
            return_order = ReturnOrder.objects.get(id=modified_data['id'])
            return_order_product_mapping = return_order.return_order_products.filter(product_id=modified_data['product']).last()
            if int(modified_data['returned_qty']) + int(modified_data['damaged_qty']) > return_order_product_mapping.delivery_picked_quantity:
                return get_response('Quantity greater than requested return quantity not allowed.')
            return_order_product_mapping.verified_return_quantity = modified_data['returned_qty']
            return_order_product_mapping.damaged_qty = modified_data['damaged_qty']
            if modified_data.get('verify_type', 'ltm') == 'bck':
                return_order_product_mapping.is_bck_return_verified = True
            else:
                return_order_product_mapping.is_return_verified = True
            return_order_product_mapping.save()
            self.create_update_return_order_product_batch(return_order_product_mapping, 
                                                   modified_data['returned_qty'], 
                                                   modified_data['damaged_qty'], 
                                                   return_order)
            return get_response('Return Order successfully updated.', None, True)
        except ReturnOrder.DoesNotExist:
            return get_response('Return Order not Found.')
            
    def create_update_return_order_product_batch(self, return_order_product_mapping, 
                                                 return_qty, damaged_qty, return_order):
        batch_id = return_order.shipment.rt_order_product_order_product_mapping.last()\
            .rt_ordered_product_mapping.last().batch_id
        return_batch, _ = ReturnProductBatch.objects.get_or_create(
            return_product = return_order_product_mapping
        )
        return_batch.batch_id = batch_id
        return_batch.return_qty = return_qty
        return_batch.damaged_qty = damaged_qty
        return_batch.save()


class ShipmentCratesValidatedView(generics.GenericAPIView):
    """
       View to validate shipment crates.
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShipmentCratesValidatedSerializer
    queryset = OrderedProduct.objects.order_by('-id')

    def get(self, request):
        if not request.GET.get('id'):
            return get_response("'id' | This is mandatory")

        """ Get Shipment for specific id """
        id_validation = validate_id(self.queryset, int(request.GET.get('id')))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        self.queryset = id_validation['data']

        shipment_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shipment_data, many=True)
        msg = "" if shipment_data else "no shipment found"
        return get_response(msg, serializer.data, True)


class ShipmentCompleteVerifyView(generics.GenericAPIView):
    """
       View to complete verify a shipment.
    """

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShipmentCompleteVerifySerializer
    queryset = OrderedProduct.objects. \
        select_related('order', 'order__seller_shop', 'order__shipping_address', 'order__shipping_address__city',
                       'order__shipping_address__state', 'order__shipping_address__pincode_link', 'invoice', 'qc_area'). \
        prefetch_related('qc_area__qc_desk_areas', 'qc_area__qc_desk_areas__qc_executive'). \
        only('id', 'order__order_no', 'order__seller_shop__id', 'order__seller_shop__shop_name',
             'order__buyer_shop__id', 'order__buyer_shop__shop_name', 'order__shipping_address__pincode',
             'order__dispatch_center__id', 'order__dispatch_center__shop_name', 'order__dispatch_delivery',
             'order__shipping_address__pincode_link_id', 'order__shipping_address__nick_name',
             'order__shipping_address__address_line1', 'order__shipping_address__address_contact_name',
             'order__shipping_address__address_contact_number', 'order__shipping_address__address_type',
             'order__shipping_address__city_id', 'order__shipping_address__city__city_name',
             'order__shipping_address__state__state_name', 'shipment_status', 'invoice__invoice_no', 'qc_area__id',
             'qc_area__area_id', 'qc_area__area_type', 'created_at'). \
        order_by('-id')

    @check_whc_manager_dispatch_executive
    def put(self, request):
        """ PUT API for shipment update """

        info_logger.info("Shipment PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update shipment', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        shipment_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=shipment_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Shipment Updated Successfully.")
            return get_response('shipment updated!', serializer.data)
        return get_response(serializer_error(serializer), False)


class ReturnOrderCompleteVerifyView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    @check_whc_manager_dispatch_executive
    def put(self, request):
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update shipment', False)
        try:
            return_order = ReturnOrder.objects.get(id=modified_data['id'])
            if return_order.return_order_products.filter(is_return_verified=False).exists():
                return get_response('All products should be verified before complete verification of return order.')
            trip = Trip.objects.filter(last_mile_trip_returns_details__return_order=return_order)\
                .exclude(last_mile_trip_returns_details__shipment_status=LastMileTripReturnMapping.CANCELLED).last()
            if trip.source_shop.shop_type.shop_type == 'sp':
                return_order.return_status = ReturnOrder.WH_ACCEPTED
                return_putaway(return_order)
            else:
                return_order.return_status = ReturnOrder.DC_ACCEPTED
                return_order.dc_location = trip.source_shop
            return_order.save()
            return get_response('return order updated successfully', None, True)
        except ReturnOrder.DoesNotExist:
            return get_response('return order not found')


class TripSummaryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = TripSummarySerializer

    @check_whc_manager_dispatch_executive
    def get(self, request):
        """ GET API for trip summary """
        info_logger.info("Order Status Summary GET api called.")
        """ GET Trip Summary List """
        if not self.request.GET.get('dispatch_center', None):
            return get_response("'dispatch_center' | This is mandatory")
        if not self.request.GET.get('trip_id', None):
            return get_response("'trip_id' | This is mandatory")
        dispatch_trip_qs = DispatchTrip.objects.prefetch_related('shipments_details').order_by('-id')
        id_validation = validate_id(dispatch_trip_qs, self.request.GET.get('trip_id'))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        trip = id_validation['data'].last()
        trip_summary_data = {
            "trip_data": self.added_shipments_to_trip_summary(self.request, trip),
            "non_trip_data": self.non_added_shipments_to_trip_summary(self.request, trip)
        }
        serializer = self.serializer_class(trip_summary_data)
        msg = "" if trip_summary_data else "no trip found"
        return get_response(msg, serializer.data, True)

    def added_shipments_to_trip_summary(self, request, dispatch_trip_instance):
        """ GET API for trip summary """
        info_logger.info("Added shipmets to Trip Summary called.")

        if dispatch_trip_instance:
            trip_summary_data = {
                'total_invoices': dispatch_trip_instance.no_of_shipments,
                'total_crates': dispatch_trip_instance.no_of_crates,
                'total_packets': dispatch_trip_instance.no_of_packets,
                'total_sack': dispatch_trip_instance.no_of_sacks,
                'total_empty_crate': dispatch_trip_instance.no_of_empty_crates,
                'total_return_box': dispatch_trip_instance.return_order_details.filter(
                    return_order_status=DispatchTripReturnOrderMapping.LOADED).count(),
                'weight': dispatch_trip_instance.get_trip_weight,
                'invoices_check': dispatch_trip_instance.shipments_details.filter(
                    shipment_status=DispatchTripShipmentMapping.UNLOADED_AT_DC).count(),
                'total_crates_check': dispatch_trip_instance.no_of_crates_check,
                'total_packets_check': dispatch_trip_instance.no_of_packets_check,
                'total_sack_check': dispatch_trip_instance.no_of_sacks_check,
                'total_empty_crate_check': dispatch_trip_instance.no_of_empty_crates_check,
                'remaining_invoices': dispatch_trip_instance.shipments_details.filter(
                    shipment_status=DispatchTripShipmentMapping.UNLOADING_AT_DC).count(),
                'remaining_crates': dispatch_trip_instance.no_of_crates - dispatch_trip_instance.no_of_crates_check,
                'remaining_packets': dispatch_trip_instance.no_of_packets - dispatch_trip_instance.no_of_packets_check,
                'remaining_sacks': dispatch_trip_instance.no_of_sacks - dispatch_trip_instance.no_of_sacks_check,
                'remaining_empty_crate': dispatch_trip_instance.no_of_empty_crates - dispatch_trip_instance.no_of_empty_crates_check,
                'remaining_return_box': dispatch_trip_instance.return_order_details.filter(
                    return_order_status=DispatchTripReturnOrderMapping.UNLOADED).count(),
            }
        else:
            trip_summary_data = {
                'total_invoices': 0,
                'total_crates': 0,
                'total_packets': 0,
                'total_sack': 0,
                'total_empty_crate': 0,
                'total_return_box': 0,
                'weight': 0,
                'invoices_check': 0,
                'total_crates_check': 0,
                'total_packets_check': 0,
                'total_sack_check': 0,
                'total_empty_crate_check': 0,
                'remaining_invoices': 0,
                'remaining_crates': 0,
                'remaining_packets': 0,
                'remaining_sacks': 0,
                'remaining_empty_crate': 0,
                'remaining_return_box': 0
            }
        return trip_summary_data

    def non_added_shipments_to_trip_summary(self, request, dispatch_trip_instance):
        """ GET API for trip summary """
        info_logger.info("Added shipmets to Trip Summary called.")
        if dispatch_trip_instance.trip_type == DispatchTrip.FORWARD:
            trip_summary_data = self.get_non_trip_data_forward_trip(request)
        elif dispatch_trip_instance.trip_type == DispatchTrip.BACKWARD:
            trip_summary_data = self.get_non_trip_data_backward_trip(request)

        return trip_summary_data

    def get_non_trip_data_forward_trip(self, request):
        shipment_qs = OrderedProduct.objects.filter(shipment_status=OrderedProduct.MOVED_TO_DISPATCH). \
            select_related('order', 'order__seller_shop'). \
            order_by('-id')
        shipment_qs = get_logged_user_wise_query_set_for_trip_invoices(request.user, shipment_qs)
        shipment_qs = self.filter_non_added_in_trip_shipments_summary_data(shipment_qs)
        resp_data = shipment_qs.aggregate(no_of_invoices=Count('id'))
        resp_data['no_of_crates'] = 0
        resp_data['no_of_packets'] = 0
        resp_data['no_of_sacks'] = 0
        resp_data['weight'] = 0
        for ss in shipment_qs.all():
            smt_pack_data = ss.shipment_packaging. \
                exclude(trip_packaging_details__package_status=DispatchTripShipmentPackages.LOADED,
                        trip_packaging_details__trip_shipment__trip__trip_status=DispatchTrip.NEW). \
                aggregate(no_of_crates=Count(Case(When(packaging_type=ShipmentPackaging.CRATE, then=1))),
                          no_of_packets=Count(Case(When(packaging_type=ShipmentPackaging.BOX, then=1))),
                          no_of_sacks=Count(Case(When(packaging_type=ShipmentPackaging.SACK, then=1)))
                          )
            if smt_pack_data:
                resp_data['no_of_crates'] += smt_pack_data['no_of_crates'] if smt_pack_data['no_of_crates'] else 0
                resp_data['no_of_packets'] += smt_pack_data['no_of_packets'] if smt_pack_data['no_of_packets'] else 0
                resp_data['no_of_sacks'] += smt_pack_data['no_of_sacks'] if smt_pack_data['no_of_sacks'] else 0
        trip_summary_data = {
            'total_invoices': resp_data['no_of_invoices'] if resp_data['no_of_invoices'] else 0,
            'total_crates': resp_data['no_of_crates'] if resp_data['no_of_crates'] else 0,
            'total_packets': resp_data['no_of_packets'] if resp_data['no_of_packets'] else 0,
            'total_sack': resp_data['no_of_sacks'] if resp_data['no_of_sacks'] else 0,
            'total_empty_crate': 0,
            'total_return_box': 0,
            'weight': resp_data['weight'] if resp_data['weight'] else 0,
            'invoices_check': 0,
            'total_crates_check': 0,
            'total_packets_check': 0,
            'total_sack_check': 0,
            'total_empty_crate_check': 0,
            'remaining_invoices': 0,
            'remaining_crates': 0,
            'remaining_packets': 0,
            'remaining_sacks': 0,
            'remaining_empty_crate': 0,
            'remaining_return_box': 0
        }
        return trip_summary_data

    def get_non_trip_data_backward_trip(self, request):
        dispatch_center = request.GET.get('dispatch_center')
        trip_id = request.GET.get('trip_id')
        resp_data = ShipmentPackaging.objects.filter(
            Q(trip_packaging_details__isnull=True) |
            Q(trip_packaging_details__package_status=DispatchTripShipmentPackages.CANCELLED),
            movement_type=ShipmentPackaging.RETURNED,
            status=ShipmentPackaging.DISPATCH_STATUS_CHOICES.PACKED,
            warehouse_id=dispatch_center,
            shipment__shipment_status__in=[
                OrderedProduct.FULLY_RETURNED_AND_VERIFIED,
                OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED]). \
            aggregate(no_of_crates=Count(Case(When(packaging_type=ShipmentPackaging.CRATE, then=1))),
                      no_of_packets=Count(Case(When(packaging_type=ShipmentPackaging.BOX, then=1))),
                      no_of_sacks=Count(Case(When(packaging_type=ShipmentPackaging.SACK, then=1)))
                      )
        trip_summary_data = {
            'total_invoices': 0,
            'total_crates': resp_data['no_of_crates'] if resp_data['no_of_crates'] else 0,
            'total_packets': resp_data['no_of_packets'] if resp_data['no_of_packets'] else 0,
            'total_sack': resp_data['no_of_sacks'] if resp_data['no_of_sacks'] else 0,
            'total_empty_crate': ShopCrate.objects.filter(shop_id=dispatch_center, is_available=True).count(),
            'total_return_box': ReturnOrder.objects.filter(dc_location_id=dispatch_center,trip_return_order__isnull=True).count(),
            'weight': 0,
            'invoices_check': 0,
            'total_crates_check': 0,
            'total_packets_check': 0,
            'total_sack_check': 0,
            'total_empty_crate_check': 0,
            'remaining_invoices': 0,
            'remaining_crates': 0,
            'remaining_packets': 0,
            'remaining_sacks': 0,
            'remaining_empty_crate': 0,
            'remaining_return_box': 0
        }
        return trip_summary_data

    def filter_non_added_in_trip_shipments_summary_data(self, queryset):
        trip_id = self.request.GET.get('trip_id')
        dispatch_center = self.request.GET.get('dispatch_center')

        '''Filters using dispatch_center'''
        if trip_id:
            queryset = queryset.filter(current_shop=DispatchTrip.objects.get(id=trip_id).source_shop)

        if dispatch_center:
            queryset = queryset.filter(order__dispatch_center__id=dispatch_center)

        return queryset


class DispatchCenterShipmentView(generics.GenericAPIView):
    """
    View to get invoices ready for dispatch to dispatch center.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DispatchInvoiceSerializer
    queryset = OrderedProduct.objects. \
        select_related('order', 'order__seller_shop', 'order__shipping_address', 'order__shipping_address__city',
                       'invoice'). \
        only('id', 'order__order_no', 'order__seller_shop__id', 'order__seller_shop__shop_name',
             'order__buyer_shop__id', 'order__buyer_shop__shop_name', 'order__shipping_address__pincode',
             'order__dispatch_center__id', 'order__dispatch_center__shop_name', 'order__dispatch_delivery',
             'order__shipping_address__pincode_link_id', 'order__shipping_address__nick_name',
             'order__shipping_address__address_line1', 'order__shipping_address__address_contact_name',
             'order__shipping_address__address_contact_number', 'order__shipping_address__address_type',
             'order__shipping_address__city_id', 'order__shipping_address__city__city_name',
             'order__shipping_address__state__state_name', 'shipment_status', 'invoice__invoice_no', 'created_at'). \
        order_by('-id')

    def get(self, request):
        validation_response = self.validate_get_request()
        if "error" in validation_response:
            return get_response(validation_response["error"], False)
        self.queryset = get_logged_user_wise_query_set_for_trip_invoices(request.user, self.queryset)
        self.queryset = self.search_filter_invoice_data()
        shipment_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shipment_data, many=True)
        msg = "" if shipment_data else "no invoice found"
        return get_response(msg, serializer.data, True)

    def validate_get_request(self):
        try:
            if not self.request.GET.get('dispatch_center', None):
                return {"error": "'dispatch_center'| This is required"}
            elif not self.request.GET.get('availability') \
                    or int(self.request.GET.get('availability')) not in INVOICE_AVAILABILITY_CHOICES._db_values:
                return {"error": "'availability' | Invalid availability choice."}
            elif int(self.request.GET['availability']) in [INVOICE_AVAILABILITY_CHOICES.ADDED,
                                                           INVOICE_AVAILABILITY_CHOICES.ALL] and \
                    not self.request.GET.get('trip_id'):
                return {"error": "'trip_id' | This is required."}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}

    def search_filter_invoice_data(self):
        """ Filters the Shipment data based on request"""
        search_text = self.request.GET.get('search_text')
        date = self.request.GET.get('date')
        status = self.request.GET.get('status')
        city = self.request.GET.get('city')
        city_name = self.request.GET.get('city_name')
        pincode = self.request.GET.get('pincode')
        pincode_no = self.request.GET.get('pincode_no')
        buyer_shop = self.request.GET.get('buyer_shop')
        dispatch_center = self.request.GET.get('dispatch_center')
        trip_id = self.request.GET.get('trip_id')
        invoice_package_status = self.request.GET.get('invoice_package_status', None)
        invoice_package_status = int(invoice_package_status) if invoice_package_status else None
        availability = int(self.request.GET.get('availability'))

        '''search using warehouse name, product's name'''
        if search_text:
            self.queryset = shipment_search(self.queryset, search_text)

        '''Filters using warehouse, product, zone, date, status, putaway_type_id'''

        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if city:
            self.queryset = self.queryset.filter(order__shipping_address__city_id=city)

        if city_name:
            self.queryset = self.queryset.filter(order__shipping_address__city__city_name__icontains=city_name)

        if pincode_no:
            self.queryset = self.queryset.filter(order__shipping_address__pincode=pincode_no)

        if pincode:
            self.queryset = self.queryset.filter(order__shipping_address__pincode_link_id=pincode)

        if buyer_shop:
            self.queryset = self.queryset.filter(order__buyer_shop_id=buyer_shop)

        if dispatch_center:
            self.queryset = self.queryset.filter(order__dispatch_center_id=dispatch_center)

        if invoice_package_status in PACKAGE_VERIFY_CHOICES._db_values:
            if invoice_package_status == PACKAGE_VERIFY_CHOICES.OK:
                self.queryset = self.queryset.filter(
                    ~Q(trip_shipment__shipment_status=DispatchTripShipmentMapping.CANCELLED),
                    ~Q(trip_shipment__trip_shipment_mapped_packages__package_status__in=[
                        DispatchTripShipmentPackages.DAMAGED_AT_LOADING,
                        DispatchTripShipmentPackages.DAMAGED_AT_UNLOADING,
                        DispatchTripShipmentPackages.MISSING_AT_LOADING,
                        DispatchTripShipmentPackages.MISSING_AT_UNLOADING]))
            elif invoice_package_status == PACKAGE_VERIFY_CHOICES.DAMAGED:
                self.queryset = self.queryset.filter(
                    ~Q(trip_shipment__shipment_status=DispatchTripShipmentMapping.CANCELLED),
                    trip_shipment__trip_shipment_mapped_packages__package_status__in=[
                        DispatchTripShipmentPackages.DAMAGED_AT_LOADING,
                        DispatchTripShipmentPackages.DAMAGED_AT_UNLOADING])
            elif invoice_package_status == PACKAGE_VERIFY_CHOICES.MISSING:
                self.queryset = self.queryset.filter(
                    trip_shipment__trip_shipment_mapped_packages__package_status__in=[
                        DispatchTripShipmentPackages.MISSING_AT_LOADING,
                        DispatchTripShipmentPackages.MISSING_AT_UNLOADING])

        if availability:
            if availability == INVOICE_AVAILABILITY_CHOICES.ADDED:
                self.queryset = self.queryset.filter(trip_shipment__trip_id=trip_id,
                                                     trip_shipment__shipment_status__in=[
                                                         DispatchTripShipmentMapping.LOADED_FOR_DC,
                                                         DispatchTripShipmentMapping.UNLOADING_AT_DC,
                                                         DispatchTripShipmentMapping.UNLOADED_AT_DC],
                                                     )
            elif availability == INVOICE_AVAILABILITY_CHOICES.NOT_ADDED:
                shipment_moved_to_dispatch = self.queryset.filter(shipment_status=OrderedProduct.MOVED_TO_DISPATCH)
                shipment_not_added_in_any_trip = shipment_moved_to_dispatch.filter(trip_shipment__isnull=True)
                shipment_added_in_some_other_trip = shipment_moved_to_dispatch.exclude(
                    ~Q(trip_shipment__trip_id=trip_id),
                    trip_shipment__isnull=False,
                    trip_shipment__shipment_status__in=[
                        DispatchTripShipmentMapping.LOADING_FOR_DC,
                        DispatchTripShipmentMapping.LOADED_FOR_DC,
                        DispatchTripShipmentMapping.UNLOADING_AT_DC,
                        DispatchTripShipmentMapping.UNLOADED_AT_DC])

                self.queryset = shipment_not_added_in_any_trip.union(shipment_added_in_some_other_trip)
            elif availability == INVOICE_AVAILABILITY_CHOICES.ALL:

                shipment_moved_to_dispatch = self.queryset.filter(shipment_status__in=[
                    OrderedProduct.MOVED_TO_DISPATCH,
                    OrderedProduct.READY_TO_DISPATCH]
                )
                self.queryset = shipment_moved_to_dispatch.exclude(~Q(trip_shipment__trip_id=trip_id),
                                                                   trip_shipment__shipment_status__in=[
                                                                       DispatchTripShipmentMapping.LOADING_FOR_DC,
                                                                       DispatchTripShipmentMapping.LOADED_FOR_DC,
                                                                       DispatchTripShipmentMapping.UNLOADING_AT_DC,
                                                                       DispatchTripShipmentMapping.UNLOADED_AT_DC])
                # self.queryset = self.queryset.filter(Q(trip_shipment__isnull=True)|
                #                                      ~Q(trip_shipment__trip=trip_id) &
                #                                      Q(trip_shipment__shipment_status=
                #                                        DispatchTripShipmentMapping.CANCELLED),
                #                                      Q(shipment_status=OrderedProduct.MOVED_TO_DISPATCH)|
                #                                      Q(trip_shipment__trip_id=trip_id) &
                #                                      ~Q(trip_shipment__shipment_status=
                #                                         DispatchTripShipmentMapping.CANCELLED))

        return self.queryset.distinct('id')


class DispatchCenterCrateView(generics.GenericAPIView):
    """
    View to get crates ready for dispatch to dispatch center.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DispatchCenterCrateSerializer
    queryset = ShopCrate.objects. \
        select_related('shop', 'crate'). \
        only('id', 'shop__id', 'shop__shop_name', 'crate', 'is_available', 'created_at', 'updated_at'). \
        order_by('-id')

    def get(self, request):
        validation_response = self.validate_get_request()
        if "error" in validation_response:
            return get_response(validation_response["error"], False)
        self.queryset = get_logged_user_wise_query_set_for_dispatch_crates(request.user, self.queryset)
        self.queryset = self.search_filter_crates_data()
        mapping_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(mapping_data, many=True)
        msg = "" if mapping_data else "no crate found"
        return get_response(msg, serializer.data, True)

    def validate_get_request(self):
        try:
            if not self.request.GET.get('shop', None):
                return {"error": "'shop'| This is required"}
            elif not self.request.GET.get('availability') \
                    or int(self.request.GET.get('availability')) not in INVOICE_AVAILABILITY_CHOICES._db_values:
                return {"error": "'availability' | Invalid availability choice."}
            elif int(self.request.GET['availability']) in [INVOICE_AVAILABILITY_CHOICES.ADDED,
                                                           INVOICE_AVAILABILITY_CHOICES.ALL] and \
                    not self.request.GET.get('trip_id'):
                return {"error": "'trip_id' | This is required."}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}

    def search_filter_crates_data(self):
        """ Filters the Shipment data based on request"""
        crate = self.request.GET.get('crate')
        shop = self.request.GET.get('shop')
        trip_id = self.request.GET.get('trip_id')
        availability = int(self.request.GET.get('availability'))

        if crate:
            self.queryset = self.queryset.filter(crate_id=crate)

        if shop:
            self.queryset = self.queryset.filter(shop_id=shop)

        if availability:
            try:
                availability = int(availability)
                if availability == INVOICE_AVAILABILITY_CHOICES.ADDED:
                    self.queryset = self.queryset.filter(crate__crate_trips__isnull=False,
                                                         crate__crate_trips__trip_id=trip_id)
                elif availability == INVOICE_AVAILABILITY_CHOICES.NOT_ADDED:
                    self.queryset = self.queryset.filter(is_available=True)
                elif availability == INVOICE_AVAILABILITY_CHOICES.ALL:
                    self.queryset = self.queryset.filter(Q(crate__crate_trips__trip_id=trip_id) |
                                                         Q(is_available=True))
            except:
                pass

        return self.queryset.distinct('id')


class DispatchCenterReturnOrderView(generics.GenericAPIView):
    """
        View to get Return Orders
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DispatchCenterReturnOrderSerializer
    queryset = ReturnOrder.objects.all()

    def get(self, request):
        validation_response = self.validate_get_request()
        if "error" in validation_response:
            return get_response(validation_response["error"], False)

        self.queryset = self.search_filter_return_order_data()
        mapping_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(mapping_data, many=True)
        msg = "Return Orders list" if mapping_data else "no return order found"
        return get_response(msg, serializer.data, True)


    def validate_get_request(self):
        try:
            if not self.request.GET.get('shop', None):
                return {"error": "'shop'| This is required"}
            elif not self.request.GET.get('trip_id'):
                return {"error": "'trip_id' | This is required."}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}

    def search_filter_return_order_data(self):
        shop = self.request.GET.get('shop')
        trip_id = self.request.GET.get('trip_id', None)
        availability = int(self.request.GET.get('availability'))
        self.queryset = self.queryset.filter(return_status='DC_ACCEPTED')

        if shop:
            self.queryset = self.queryset.filter(dc_location_id=shop)

        if availability:
            try:
                availability = int(availability)
                if availability == INVOICE_AVAILABILITY_CHOICES.ADDED:
                    self.queryset = self.queryset.filter(trip_return_order__trip_id=trip_id)
                elif availability == INVOICE_AVAILABILITY_CHOICES.NOT_ADDED:
                    self.queryset = self.queryset.filter(trip_return_order__isnull=True)
            except Exception as e:
                info_logger.info(e)
        return self.queryset.distinct('id')


class DispatchCenterShipmentPackageView(generics.GenericAPIView):
    """
    View to get Shipment Package ready for dispatch to dispatch center.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DispatchCenterShipmentPackageSerializer
    queryset = ShipmentPackaging.objects. \
        select_related('warehouse', 'crate', 'shipment'). \
        only('id', 'warehouse__id', 'warehouse__shop_name', 'crate', 'shipment', 'created_at', 'updated_at'). \
        order_by('-id')

    def get(self, request):
        validation_response = self.validate_get_request()
        if "error" in validation_response:
            return get_response(validation_response["error"], False)
        self.queryset = get_logged_user_wise_query_set_for_shipment_packaging(request.user, self.queryset)
        self.queryset = self.search_filter_shipment_packages_data()
        mapping_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(mapping_data, many=True)
        msg = "" if mapping_data else "no packages found"
        return get_response(msg, serializer.data, True)

    def validate_get_request(self):
        try:
            if not self.request.GET.get('shop', None):
                return {"error": "'shop'| This is required"}
            elif not self.request.GET.get('availability') \
                    or int(self.request.GET.get('availability')) not in INVOICE_AVAILABILITY_CHOICES._db_values:
                return {"error": "'availability' | Invalid availability choice."}
            elif int(self.request.GET['availability']) in [INVOICE_AVAILABILITY_CHOICES.ADDED,
                                                           INVOICE_AVAILABILITY_CHOICES.ALL] and \
                    not self.request.GET.get('trip_id'):
                return {"error": "'trip_id' | This is required."}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}

    def search_filter_shipment_packages_data(self):
        """ Filters the Shipment data based on request"""
        package_id = self.request.GET.get('package_id')
        shop = self.request.GET.get('shop')
        trip_id = self.request.GET.get('trip_id')
        availability = int(self.request.GET.get('availability'))

        if package_id:
            self.queryset = self.queryset.filter(id=package_id)

        if shop:
            self.queryset = self.queryset.filter(warehouse_id=shop)

        if availability:
            try:
                availability = int(availability)
                if availability == INVOICE_AVAILABILITY_CHOICES.ADDED:
                    self.queryset = self.queryset.filter(
                        status='READY_TO_DISPATCH').filter(Q(shipment__trip_shipment__trip_id=trip_id) |
                                                           Q(shipment__last_mile_trip_shipment__trip_id=trip_id))
                elif availability == INVOICE_AVAILABILITY_CHOICES.NOT_ADDED:
                    self.queryset = self.queryset.filter(status='PACKED',
                                                         shipment__shipment_status__in=[
                                                             OrderedProduct.FULLY_RETURNED_AND_VERIFIED,
                                                             OrderedProduct.PARTIALLY_DELIVERED_AND_VERIFIED,
                                                             OrderedProduct.FULLY_RETURNED_AND_CLOSED,
                                                             OrderedProduct.PARTIALLY_DELIVERED_AND_CLOSED])
            except:
                pass

        return self.queryset.distinct('id')


class LoadVerifyCrateView(generics.GenericAPIView):
    """
       View to verify and load empty crate to a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LoadVerifyCrateSerializer

    @check_whc_manager_dispatch_executive
    def post(self, request):
        """ POST API for Empty Crate Load Verification """
        info_logger.info("Load Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        validated_trip = validate_trip_user(modified_data['trip_id'], request.user)
        if 'error' in validated_trip:
            return get_response(validated_trip['error'])
        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Empty crate loaded Successfully.")
            return get_response('Empty crate loaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class UnloadVerifyCrateView(generics.GenericAPIView):
    """
       View to verify and unload packages from a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = UnloadVerifyCrateSerializer
    queryset = DispatchTripCrateMapping.objects.all()

    def validate_trip_empty_crate(self, crate_id, trip_id):
        trip_empty_crate = self.queryset.filter(
            crate_status__in=[DispatchTripCrateMapping.LOADED, DispatchTripCrateMapping.DAMAGED_AT_LOADING],
            crate__crate_id=crate_id, trip__id=trip_id).last()
        if not trip_empty_crate:
            return {"error": "invalid Crate"}
        return {"data": trip_empty_crate}

    def put(self, request):
        """ POST API for Shipment Package Load Verification """
        info_logger.info("Load Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'crate_id' not in modified_data:
            return get_response("'crate_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)
        if 'status' not in modified_data:
            return get_response("'status' | This is required.", False)

        # validations for input
        crate_validation = self.validate_trip_empty_crate(modified_data['crate_id'], int(modified_data['trip_id']))
        if 'error' in crate_validation:
            return get_response(crate_validation['error'])
        trip_empty_crate = crate_validation['data']

        serializer = self.serializer_class(instance=trip_empty_crate, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Crate unloaded Successfully.")
            return get_response('Crate unloaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class LoadVerifyPackageView(generics.GenericAPIView):
    """
       View to verify and load packages to a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LoadVerifyPackageSerializer

    def post(self, request):
        """ POST API for Shipment Package Load Verification """
        info_logger.info("Load Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        validated_trip = validate_trip_user(modified_data['trip_id'], request.user)
        if 'error' in validated_trip:
            return get_response(validated_trip['error'])
        return_all_pkgs = False
        if 'return_all_pkgs' in modified_data and modified_data['return_all_pkgs'] is True:
            return_all_pkgs = True
        serializer = self.serializer_class(data=modified_data, context={'current_user': request.user})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Package loaded Successfully.")
            # return get_response('Package loaded successfully!', serializer.data)
            query_set = ShipmentPackaging.objects. \
                select_related('crate', 'warehouse', 'warehouse__shop_owner', 'shipment', 'shipment__invoice',
                               'shipment__order', 'shipment__order__shipping_address',
                               'shipment__order__buyer_shop', 'shipment__order__shipping_address__shop_name',
                               'shipment__order__buyer_shop__shop_owner', 'warehouse__shop_type',
                               'warehouse__shop_type__shop_sub_type', 'created_by', 'updated_by'). \
                prefetch_related('packaging_details', 'trip_packaging_details', 'shipment__trip_shipment',
                                 'shipment__last_mile_trip_shipment')
            if not return_all_pkgs:
                query_set = query_set.get(id=modified_data['package_id'])
                return get_response('Package loaded successfully!', ShipmentPackageSerializer(query_set).data)
            else:
                packaging_data = ShipmentPackaging.objects.get(id=modified_data['package_id'])
                query_set = query_set.filter(shipment=packaging_data.shipment,
                                             movement_type=packaging_data.movement_type)
                return get_response('Package loaded successfully!',
                                    ShipmentPackageSerializer(query_set, many=True).data)
        return get_response(serializer_error(serializer), False)


class LoadVerifyReturnOrderView(generics.GenericAPIView):
    """
       View to verify and load return order to a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LoadVerifyReturnOrderSerializer

    @check_whc_manager_dispatch_executive
    def post(self, request):
        """ POST API for Return Order Load Verification """
        info_logger.info("Load Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        validated_trip = validate_trip_user(modified_data['trip_id'], request.user)
        if 'error' in validated_trip:
            return get_response(validated_trip['error'])
        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Return order loaded Successfully.")
            return get_response('Return order loaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)



class UnloadVerifyReturnOrderView(generics.GenericAPIView):
    """
       View to verify and unload return order from a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = UnLoadVerifyReturnOrderSerializer
    queryset = DispatchTripReturnOrderMapping.objects.all()

    def validate_trip_return_order(self, return_id, trip_id):
        trip_return_order = self.queryset.filter(
            return_order_status__in=[DispatchTripReturnOrderMapping.UNLOADED,
                                     DispatchTripReturnOrderMapping.VERIFIED],
            return_order__id=return_id, trip__id=trip_id).last()
        if trip_return_order:
            return {"error": "Return order is already unloaded!"}
        trip_return_order = self.queryset.filter(
            return_order_status__in=[DispatchTripReturnOrderMapping.LOADED,
                                     DispatchTripReturnOrderMapping.DAMAGED_AT_LOADING],
            return_order__id=return_id, trip__id=trip_id).last()
        if not trip_return_order:
            return {"error": "invalid Return Order"}
        return {"data": trip_return_order}

    def put(self, request):
        """ POST API for Return Order UnLoad Verification """
        info_logger.info("UnLoad Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'return_id' not in modified_data:
            return get_response("'return_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)
        if 'status' not in modified_data:
            return get_response("'status' | This is required.", False)

        # validations for input
        return_order_validation = self.validate_trip_return_order(modified_data['return_id'], int(modified_data['trip_id']))
        if 'error' in return_order_validation:
            return get_response(return_order_validation['error'])
        trip_return_order = return_order_validation['data']

        serializer = self.serializer_class(instance=trip_return_order, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Return Order unloaded Successfully.")
            return get_response('Return Order unloaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class CurrentlyLoadingShipmentPackagesView(generics.GenericAPIView):
    """
       View to get all the packages of currently loading shipment.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShipmentPackaging.objects. \
        select_related('crate', 'warehouse', 'warehouse__shop_owner', 'shipment', 'shipment__invoice',
                       'shipment__order', 'shipment__order__shipping_address',
                       'shipment__order__buyer_shop', 'shipment__order__shipping_address__shop_name',
                       'shipment__order__buyer_shop__shop_owner', 'warehouse__shop_type',
                       'warehouse__shop_type__shop_sub_type', 'created_by', 'updated_by'). \
        prefetch_related('packaging_details', 'trip_packaging_details', 'shipment__trip_shipment',
                         'shipment__last_mile_trip_shipment').order_by('-id')
    serializer_class = ShipmentPackageSerializer

    def get_loading_shipment_by_trip_and_user(self, user, trip):
        """
            GET shipment by Trip id and the user
        """
        map_instance = DispatchTripShipmentMapping.objects.filter(
            trip=trip, loaded_by=user, shipment_status=DispatchTripShipmentMapping.LOADING_FOR_DC).last()
        return map_instance.shipment if map_instance else None

    def get(self, request):
        """ GET API for Shipment Packages """
        info_logger.info("Shipment Packages GET api called.")
        """ GET Shipment Packages List """
        if not request.GET.get('trip_id'):
            return get_response("'trip_id' | This is required.", False)

        trip_instance = DispatchTrip.objects.filter(id=request.GET.get('trip_id')).last()
        if not trip_instance:
            return get_response("'trip_id' | Invalid Trip id.", False)
        current_shipment = self.get_loading_shipment_by_trip_and_user(request.user, trip_instance)
        if not current_shipment:
            return get_response("There is no invoice currently being loaded in this trip. "
                                "Please scan the package to start loading.", False)
        self.queryset = self.queryset.filter(shipment=current_shipment)
        if trip_instance.trip_type == DispatchTrip.FORWARD:
            self.queryset = self.queryset.filter(movement_type__in=[
                ShipmentPackaging.DISPATCH, ShipmentPackaging.RESCHEDULED, ShipmentPackaging.NOT_ATTEMPT])
        if trip_instance.trip_type == DispatchTrip.BACKWARD:
            self.queryset = self.queryset.filter(movement_type=ShipmentPackaging.RETURNED)
        no_of_packages = self.queryset.count()

        serializer = self.serializer_class(self.queryset, many=True)
        msg = f"total count {no_of_packages}" if self.queryset.exists() else "no package found"
        return get_response(msg, serializer.data, True)


class UnloadVerifyPackageView(generics.GenericAPIView):
    """
       View to verify and unload packages from a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = UnloadVerifyPackageSerializer
    queryset = DispatchTripShipmentPackages.objects.all()

    def validate_trip_shipment_package(self, package_id, trip_id):
        trip_shipment_package = self.queryset.filter(shipment_packaging_id=package_id,
                                                     trip_shipment__trip__id=trip_id).last()
        if not trip_shipment_package:
            return {"error": "Package does not belong to this trip."}
        return {"data": trip_shipment_package}

    def put(self, request):
        """ POST API for Shipment Package Load Verification """
        info_logger.info("Load Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'package_id' not in modified_data:
            return get_response("'package_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)
        if 'status' not in modified_data:
            return get_response("'status' | This is required.", False)

        # validations for input
        shipment_validation = self.validate_trip_shipment_package(int(modified_data['package_id']),
                                                                  int(modified_data['trip_id']))
        if 'error' in shipment_validation:
            return get_response(shipment_validation['error'])
        trip_shipment_package = shipment_validation['data']

        serializer = self.serializer_class(instance=trip_shipment_package, data=modified_data)

        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Package unloaded Successfully.")
            return get_response('Package unloaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class RemoveInvoiceFromTripView(generics.GenericAPIView):
    """
       View to remove invoice from a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = TripShipmentMappingSerializer
    queryset = DispatchTripShipmentMapping.objects.all()

    def put(self, request):
        """ POST API for Shipment Package Load Verification """
        info_logger.info("Remove invoice PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'shipment_id' not in modified_data:
            return get_response("'shipment_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)

        # validations for input
        shipment_validation = self.validate_trip_invoice(int(modified_data['shipment_id']),
                                                         int(modified_data['trip_id']))
        if 'error' in shipment_validation:
            return get_response(shipment_validation['error'])
        trip_invoice_mapping = shipment_validation['data'].last()

        serializer = self.serializer_class(instance=trip_invoice_mapping, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            info_logger.info("Shipment removed successfully.")
            return get_response('Shipment removed successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def validate_trip_invoice(self, shipment_id, trip_id):
        if not self.queryset.filter(~Q(shipment_status=DispatchTripShipmentMapping.CANCELLED),
                                    trip_id=trip_id, shipment_id=shipment_id).exists():
            return {"error": "invalid Shipment"}
        return {"data": self.queryset.filter(~Q(shipment_status=DispatchTripShipmentMapping.CANCELLED),
                                             trip_id=trip_id, shipment_id=shipment_id)}


class LastMileTripCrudView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Trip.objects. \
        annotate(status=Case(
        When(trip_status__in=[Trip.READY, Trip.STARTED], then=Value("PENDING")),
        When(trip_status__in=[Trip.CANCELLED, Trip.PAYMENT_VERIFIED, Trip.RETURN_VERIFIED],
             then=Value("CLOSED")),
        default=F('trip_status'))). \
        select_related('seller_shop', 'source_shop', 'seller_shop__shop_owner', 'seller_shop__shop_type',
                       'seller_shop__shop_type__shop_sub_type', 'delivery_boy'). \
        only('id', 'dispatch_no', 'vehicle_no', 'seller_shop__id', 'seller_shop__status', 'seller_shop__shop_name',
             'seller_shop__shop_type', 'seller_shop__shop_type__shop_type', 'seller_shop__shop_type__shop_sub_type',
             'seller_shop__shop_type__shop_sub_type__retailer_type_name', 'seller_shop__shop_owner',
             'seller_shop__shop_owner__first_name', 'seller_shop__shop_owner__last_name',
             'seller_shop__shop_owner__phone_number', 'source_shop__id', 'source_shop__status',
             'source_shop__shop_name',
             'source_shop__shop_type', 'source_shop__shop_type__shop_type', 'source_shop__shop_type__shop_sub_type',
             'source_shop__shop_type__shop_sub_type__retailer_type_name', 'source_shop__shop_owner',
             'source_shop__shop_owner__first_name', 'source_shop__shop_owner__last_name',
             'source_shop__shop_owner__phone_number', 'delivery_boy__id', 'delivery_boy__first_name',
             'delivery_boy__last_name', 'delivery_boy__phone_number', 'trip_status', 'e_way_bill_no', 'starts_at',
             'completed_at', 'received_amount', 'opening_kms', 'closing_kms', 'no_of_crates', 'no_of_packets',
             'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check', 'created_at',
             'modified_at', ). \
        order_by('-id')
    serializer_class = LastMileTripCrudSerializers

    @check_whc_manager_dispatch_executive
    def get(self, request):
        """ GET API for Dispatch Trip """
        info_logger.info("Dispatch Trip GET api called.")
        if request.GET.get('id'):
            """ Get Dispatch Trip for specific ID """
            trip_total_count = self.queryset.count()
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            trips_data = id_validation['data']
        else:
            """ GET Dispatch Trip List """
            self.queryset = get_logged_user_wise_query_set_for_dispatch_trip(request.user, self.queryset)
            self.queryset = self.search_filter_trips_data()
            trip_total_count = self.queryset.count()
            trips_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(trips_data, many=True)
        msg = f"total count {trip_total_count}" if trips_data else "no trip found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_dispatch_executive
    @check_user_can_plan_trip
    def post(self, request):
        """ POST API for Last Mile Trip Creation with Image """

        info_logger.info("Last Mile Trip POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Last Mile Trip Created Successfully.")
            return get_response('trip created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_whc_manager_dispatch_executive
    @check_user_can_plan_trip
    def put(self, request):
        """ PUT API for Last Mile Trip Updation """

        info_logger.info("Last Mile Trip PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update trip', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        trip_instance = id_validation['data'].last()
        modified_data['dispatch_no'] = trip_instance.dispatch_no

        serializer = self.serializer_class(instance=trip_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Last Mile Trip Updated Successfully.")
            return get_response('trip updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    @check_whc_manager_dispatch_executive
    @check_user_can_plan_trip
    def delete(self, request):
        """ Delete Last Mile Trip """

        info_logger.info("Last Mile Trip DELETE api called.")
        if not request.data.get('trip_id'):
            return get_response('please provide trip_id', False)
        try:
            for z_id in request.data.get('trip_id'):
                trip_id = self.queryset.get(id=int(z_id))
                try:
                    trip_mappings = DispatchTripShipmentMapping.objects.filter(trip_id=trip_id)
                    if trip_mappings:
                        trip_mappings.delete()
                    trip_id.delete()
                except:
                    return get_response(f'can not delete dispatch trip | {trip_id.id} | getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid dispatch trip id {z_id}', False)
        return get_response('dispatch trip were deleted successfully!', True)

    def search_filter_trips_data(self):
        search_text = self.request.GET.get('search_text')
        seller_shop = self.request.GET.get('seller_shop')
        source_shop = self.request.GET.get('source_shop')
        delivery_boy = self.request.GET.get('delivery_boy')
        dispatch_no = self.request.GET.get('dispatch_no')
        vehicle_no = self.request.GET.get('vehicle_no')
        trip_status = self.request.GET.get('trip_status')
        t_status = self.request.GET.get('status')
        created_at = self.request.GET.get('date')
        data_days = self.request.GET.get('data_days')

        '''search using seller_shop name, source_shop's firstname  and destination_shop's firstname'''
        if search_text:
            self.queryset = trip_search(self.queryset, search_text)

        '''
            Filters using seller_shop, delivery_boy, dispatch_no, vehicle_no, trip_status
        '''
        if seller_shop:
            self.queryset = self.queryset.filter(seller_shop__id=seller_shop)

        if source_shop:
            self.queryset = self.queryset.filter(source_shop__id=source_shop)

        if delivery_boy:
            self.queryset = self.queryset.filter(delivery_boy__id=delivery_boy)

        if dispatch_no:
            self.queryset = self.queryset.filter(dispatch_no=dispatch_no)

        if vehicle_no:
            self.queryset = self.queryset.filter(vehicle_no=vehicle_no)

        if trip_status:
            self.queryset = self.queryset.filter(trip_status=trip_status)

        if t_status:
            self.queryset = self.queryset.filter(status=t_status)

        if created_at:
            if data_days:
                end_date = datetime.strptime(created_at, "%Y-%m-%d")
                start_date = end_date - timedelta(days=int(data_days))
                self.queryset = self.queryset.filter(
                    created_at__date__gte=start_date.date(), created_at__date__lte=end_date.date())
            else:
                created_at = datetime.strptime(created_at, "%Y-%m-%d")
                self.queryset = self.queryset.filter(created_at__date=created_at)

        return self.queryset.distinct('id')


class LastMileTripShipmentsView(generics.GenericAPIView):
    """
    View to get invoices ready for dispatch to dispatch center.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LastMileTripShipmentsSerializer
    queryset = OrderedProduct.objects.filter(~Q(shipment_status__in=[OrderedProduct.SHIPMENT_CREATED,
                                                                     OrderedProduct.QC_STARTED,
                                                                     OrderedProduct.QC_REJECTED,
                                                                     OrderedProduct.READY_TO_SHIP])). \
        select_related('order', 'order__seller_shop', 'order__shipping_address', 'order__shipping_address__city',
                       'invoice'). \
        only('id', 'order__order_no', 'order__seller_shop__id', 'order__seller_shop__shop_name',
             'order__buyer_shop__id', 'order__buyer_shop__shop_name', 'order__shipping_address__pincode',
             'order__dispatch_center__id', 'order__dispatch_center__shop_name', 'order__dispatch_delivery',
             'order__shipping_address__pincode_link_id', 'order__shipping_address__nick_name',
             'order__shipping_address__address_line1', 'order__shipping_address__address_contact_name',
             'order__shipping_address__address_contact_number', 'order__shipping_address__address_type',
             'order__shipping_address__city_id', 'order__shipping_address__city__city_name',
             'order__shipping_address__state__state_name', 'shipment_status', 'invoice__invoice_no', 'created_at'). \
        order_by('-id')

    def get(self, request):
        validation_response = self.validate_get_request()
        if "error" in validation_response:
            return get_response(validation_response["error"], False)
        # self.queryset = get_logged_user_wise_query_set_for_dispatch_trip(request.user, self.queryset)
        self.queryset = self.search_filter_invoice_data()
        shipment_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        data_dict = {
            'trip_id': self.request.GET.get('trip_id'),
            'invoices': shipment_data
        }
        serializer = self.serializer_class(data_dict)
        msg = "" if shipment_data else "no invoice found"
        return get_response(msg, serializer.data, True)

    def validate_get_request(self):
        try:
            if not self.request.GET.get('seller_shop', None):
                return {"error": "'seller_shop'| This is required"}
            elif not self.request.GET.get('availability') \
                    or int(self.request.GET.get('availability')) not in INVOICE_AVAILABILITY_CHOICES._db_values:
                return {"error": "'availability' | Invalid availability choice."}
            elif not self.request.GET.get('trip_id', None):
                return {"error": "'trip_id' | This is required."}
            elif not Trip.objects.filter(id=self.request.GET.get('trip_id')).exists():
                return {"error": "'trip_id' | Invalid trip."}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}

    def search_filter_invoice_data(self):
        """ Filters the Shipment data based on request"""
        search_text = self.request.GET.get('search_text')
        date = self.request.GET.get('date')
        shipment_status = self.request.GET.get('shipment_status')
        city = self.request.GET.get('city')
        city_name = self.request.GET.get('city_name')
        pincode = self.request.GET.get('pincode')
        pincode_no = self.request.GET.get('pincode_no')
        seller_shop = self.request.GET.get('seller_shop')
        buyer_shop = self.request.GET.get('buyer_shop')
        current_shop = self.request.GET.get('current_shop')
        dispatch_center = self.request.GET.get('dispatch_center')
        trip_id = self.request.GET.get('trip_id')
        availability = self.request.GET.get('availability')

        '''search using warehouse name, product's name'''
        if search_text:
            self.queryset = shipment_search(self.queryset, search_text)

        '''Filters using warehouse, product, zone, date, status, putaway_type_id'''

        if date:
            self.queryset = self.queryset.filter(created_at__date=date)

        if shipment_status:
            self.queryset = self.queryset.filter(shipment_status=shipment_status)

        if city:
            self.queryset = self.queryset.filter(order__shipping_address__city_id=city)

        if city_name:
            self.queryset = self.queryset.filter(order__shipping_address__city__city_name__icontains=city_name)

        if pincode_no:
            self.queryset = self.queryset.filter(order__shipping_address__pincode=pincode_no)

        if pincode:
            self.queryset = self.queryset.filter(order__shipping_address__pincode_link_id=pincode)

        if seller_shop:
            self.queryset = self.queryset.filter(order__seller_shop_id=seller_shop)

        if buyer_shop:
            self.queryset = self.queryset.filter(order__buyer_shop_id=buyer_shop)

        if current_shop:
            self.queryset = self.queryset.filter(current_shop_id=current_shop)

        if dispatch_center:
            self.queryset = self.queryset.filter(order__dispatch_center=dispatch_center)

        if trip_id:
            trip_source_shop = Trip.objects.filter(id=trip_id).last().source_shop
            self.queryset = self.queryset.filter(current_shop=trip_source_shop)
            if trip_source_shop.shop_type.shop_type == 'sp':
                self.queryset = self.queryset.filter(order__dispatch_center__isnull=True)
            if trip_source_shop.shop_type.shop_type == 'dc':
                self.queryset = self.queryset.filter(order__dispatch_center=trip_source_shop)

        if availability:
            try:
                availability = int(availability)
                if availability == INVOICE_AVAILABILITY_CHOICES.ADDED:
                    self.queryset = self.queryset.filter(~Q(shipment_status=OrderedProduct.MOVED_TO_DISPATCH)).filter(
                        Q(last_mile_trip_shipment__isnull=False,
                          last_mile_trip_shipment__shipment_status__in=[LastMileTripShipmentMapping.TO_BE_LOADED,
                                                                        LastMileTripShipmentMapping.LOADING_FOR_DC,
                                                                        LastMileTripShipmentMapping.LOADED_FOR_DC],
                          last_mile_trip_shipment__trip_id=trip_id) | Q(trip_id=trip_id))
                elif availability == INVOICE_AVAILABILITY_CHOICES.NOT_ADDED:
                    current_date = datetime.now().date()
                    self.queryset = self.queryset.filter(
                        Q((Q(last_mile_trip_shipment__isnull=True) |
                           Q(last_mile_trip_shipment__shipment_status=LastMileTripShipmentMapping.CANCELLED)),
                          shipment_status=OrderedProduct.MOVED_TO_DISPATCH) |
                        Q(~Q(last_mile_trip_shipment__trip__trip_status__in=[Trip.READY, Trip.STARTED, Trip.COMPLETED]),
                          shipment_status=OrderedProduct.NOT_ATTEMPT,
                          not_attempt_shipment__created_at__date__lt=current_date) |
                        Q(~Q(last_mile_trip_shipment__trip__trip_status__in=[Trip.READY, Trip.STARTED, Trip.COMPLETED]),
                          shipment_status=OrderedProduct.RESCHEDULED,
                          rescheduling_shipment__rescheduling_date__lte=current_date))
                elif availability == INVOICE_AVAILABILITY_CHOICES.ALL:
                    self.queryset = self.queryset.filter(
                        Q(last_mile_trip_shipment__trip_id=trip_id) | Q(last_mile_trip_shipment__isnull=True) |
                        Q(trip_id=trip_id))
            except:
                pass

        return self.queryset.distinct('id')


class LastMileTripStatusChangeView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Trip.objects. \
        select_related('seller_shop', 'seller_shop__shop_owner', 'seller_shop__shop_type',
                       'seller_shop__shop_type__shop_sub_type', 'delivery_boy'). \
        prefetch_related('rt_invoice_trip'). \
        only('id', 'dispatch_no', 'vehicle_no', 'seller_shop__id', 'seller_shop__status', 'seller_shop__shop_name',
             'seller_shop__shop_type', 'seller_shop__shop_type__shop_type', 'seller_shop__shop_type__shop_sub_type',
             'seller_shop__shop_type__shop_sub_type__retailer_type_name', 'seller_shop__shop_owner',
             'seller_shop__shop_owner__first_name', 'seller_shop__shop_owner__last_name',
             'seller_shop__shop_owner__phone_number', 'delivery_boy__id', 'delivery_boy__first_name',
             'delivery_boy__last_name', 'delivery_boy__phone_number', 'trip_status', 'e_way_bill_no', 'starts_at',
             'completed_at', 'received_amount', 'opening_kms', 'closing_kms', 'no_of_crates', 'no_of_packets',
             'no_of_sacks', 'no_of_crates_check', 'no_of_packets_check', 'no_of_sacks_check', 'created_at',
             'modified_at', ). \
        order_by('-id')
    serializer_class = LastMileTripStatusChangeSerializers

    @check_whc_manager_dispatch_executive
    @check_user_can_plan_trip
    def get(self, request):
        """ GET API for Dispatch Trip """
        info_logger.info("Dispatch Trip GET api called.")
        if request.GET.get('id'):
            """ Get Dispatch Trip for specific ID """
            trip_total_count = self.queryset.count()
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            trips_data = id_validation['data']
        else:
            """ GET Dispatch Trip List """
            self.queryset = get_logged_user_wise_query_set_for_dispatch_trip(request.user, self.queryset)
            self.queryset = self.search_filter_trips_data()
            trip_total_count = self.queryset.count()
            trips_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(trips_data, many=True)
        msg = f"total count {trip_total_count}" if trips_data else "no trip found"
        return get_response(msg, serializer.data, True)

    @check_whc_manager_dispatch_executive
    @check_user_can_plan_trip
    def put(self, request):
        """ PUT API for Last Mile Trip Updation """

        info_logger.info("Last Mile Trip PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update trip', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        trip_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=trip_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Last Mile Trip Updated Successfully.")
            return get_response('trip updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_trips_data(self):
        search_text = self.request.GET.get('search_text')
        seller_shop = self.request.GET.get('seller_shop')
        delivery_boy = self.request.GET.get('delivery_boy')
        dispatch_no = self.request.GET.get('dispatch_no')
        vehicle_no = self.request.GET.get('vehicle_no')
        trip_status = self.request.GET.get('trip_status')

        '''search using seller_shop name, source_shop's firstname  and destination_shop's firstname'''
        if search_text:
            self.queryset = trip_search(self.queryset, search_text)

        '''
            Filters using seller_shop, delivery_boy, dispatch_no, vehicle_no, trip_status
        '''
        if seller_shop:
            self.queryset = self.queryset.filter(seller_shop__id=seller_shop)

        if delivery_boy:
            self.queryset = self.queryset.filter(delivery_boy__id=delivery_boy)

        if dispatch_no:
            self.queryset = self.queryset.filter(dispatch_no=dispatch_no)

        if vehicle_no:
            self.queryset = self.queryset.filter(vehicle_no=vehicle_no)

        if trip_status:
            self.queryset = self.queryset.filter(trip_status=trip_status)

        return self.queryset.distinct('id')


class LastMileTripReturnOrderView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LastMileTripReturnOrdersBasicDetailSerializer

    def get(self, request):
        result = self.validate_get_request()
        if "error" in result:
            return get_response(result["error"], False)

        trip_id = self.request.GET.get('trip_id', None)
        seller_shop = self.request.GET.get('seller_shop', None)
        trip = Trip.objects.filter(id=trip_id).last()
        source_shop = trip.source_shop
        if source_shop.shop_type.shop_type == 'sp':
            returns = ReturnOrder.objects.filter(
                # return_status__in=[ReturnOrder.STORE_ITEM_PICKED],
                seller_shop_id=seller_shop,
                last_mile_trip_returns__trip_id=trip_id,
                shipment__order__dispatch_center__isnull=True,
            ).distinct('id')
        if source_shop.shop_type.shop_type == 'dc':
            returns = ReturnOrder.objects.filter(
                # return_status__in=[ReturnOrder.STORE_ITEM_PICKED],
                seller_shop_id=seller_shop,
                last_mile_trip_returns__trip_id=trip_id,
                shipment__order__dispatch_center=source_shop
            ).distinct('id')
        returns_data = SmallOffsetPagination().paginate_queryset(returns, request)
        return_serializer = self.serializer_class(returns_data, many=True)
        trip_serializer = LastMileTripSerializers(trip)
        data = {
            'trip': trip_serializer.data,
            'returns': return_serializer.data
        }
        msg = "" if returns_data else "no returns found"
        return get_response(msg, data, True)

    def validate_get_request(self):
        try:
            if not self.request.GET.get('seller_shop', None):
                return {"error": "'seller_shop'| This is required"}
            elif not self.request.GET.get('trip_id', None):
                return {"error": "'trip_id' | This is required."}
            elif not Trip.objects.filter(id=self.request.GET.get('trip_id')).exists():
                return {"error": "'trip_id' | Invalid trip."}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}


class LastMileTripDeliveryReturnOrderView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DeliveryReturnOrderSerializer

    def get(self, request):
        result = self.validate_get_request()
        if "error" in result:
            return get_response([result["error"]], False)

        trip_id = self.request.GET.get('trip_id', None)
        seller_shop = self.request.GET.get('seller_shop', None)
        buyer_shop = self.request.GET.get('buyer_shop', None)
        trip = Trip.objects.filter(id=trip_id).last()
        source_shop = trip.source_shop
        if source_shop.shop_type.shop_type == 'sp':
            returns = ReturnOrder.objects.filter(
                # return_status__in=[ReturnOrder.STORE_ITEM_PICKED],
                seller_shop_id=seller_shop,
                last_mile_trip_returns__trip_id=trip_id,
                shipment__order__dispatch_center__isnull=True,
                buyer_shop_id=buyer_shop
            ).distinct('id')
        if source_shop.shop_type.shop_type == 'dc':
            returns = ReturnOrder.objects.filter(
                # return_status__in=[ReturnOrder.STORE_ITEM_PICKED],
                seller_shop_id=seller_shop,
                last_mile_trip_returns__trip_id=trip_id,
                shipment__order__dispatch_center=source_shop,
                buyer_shop_id=buyer_shop
            ).distinct('id')
        returns_data = SmallOffsetPagination().paginate_queryset(returns, request)
        serializer = self.serializer_class(returns_data, many=True)
        msg = [] if returns_data else ["no returns found"]
        return get_response(msg, serializer.data, True)

    def validate_get_request(self):
        try:
            if not self.request.GET.get('seller_shop', None):
                return {"error": "'seller_shop'| This is required"}
            elif not self.request.GET.get('trip_id', None):
                return {"error": "'trip_id' | This is required."}
            elif not Trip.objects.filter(id=self.request.GET.get('trip_id')).exists():
                return {"error": "'trip_id' | Invalid trip."}
            if not self.request.GET.get('buyer_shop', None):
                return {"error": "'buyer_shop'| This is required"}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}

    def put(self, request):
        result = self.validate_put_request()
        if "error" in result:
            result = {"is_success": False, "message": [result["error"]], "response_data": ''}
            return Response(result, status=status.HTTP_200_OK)
        return_id = self.request.data.get('return_id', None)
        return_item_id = self.request.data.get('return_item_id', None)
        barcode = self.request.data.get('barcode', None).zfill(13)
        picked_quantity = self.request.data.get('picked_quantity', None)
        orderreturn = ReturnOrder.objects.filter(pk=return_id).last()
        trip_id = orderreturn.last_mile_trip_returns.last().trip.id
        if orderreturn.return_status != ReturnOrder.RETURN_INITIATED:
            result = {"is_success": False, "message": ["error: Return not found in initiated state"], "response_data":''}
            return Response(result, status=status.HTTP_200_OK)
        return_item = ReturnOrderProduct.objects.filter(id=return_item_id).last()
        return_item.return_shipment_barcode = barcode[:-1]
        return_item.delivery_picked_quantity = picked_quantity
        orderreturn.return_status = ReturnOrder.STORE_ITEM_PICKED
        code = Barcode.objects.filter(barcode_no=barcode[:-1]).last()
        code.is_available=False
        with transaction.atomic():
            return_item.save()
            orderreturn.save()
            code.save()
            update_trip_status(trip_id)
        return get_response(["return picked sucessfully"], '', True)

    def validate_put_request(self):
        try:
            if not self.request.data.get('return_id', None):
                return {"error": "'return_id'| This is required"}
            elif not self.request.data.get('return_item_id', None):
                return {"error": "'return_item_id' | This is required."}
            if not self.request.data.get('barcode', None):
                return {"error": "'barcode'| This is required"}
            else:
                barcode = self.request.data.get('barcode').zfill(13)
                code = Barcode.objects.filter(barcode_no=barcode[:-1]).last()
                if not code:
                    return {"error": "Invalid Barcode"}
                elif not code.is_available:
                    return {"error": "Barcode already used"}
            if not self.request.data.get('picked_quantity', None):
                return {"error": "'picked_quantity'| This is required"}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}


class DispatchPackageStatusList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get shipment package rejection reason list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in PACKAGE_VERIFY_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ReschedulingReasonsListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ReschedulingReasonsList """
        info_logger.info("ReschedulingReasonsList GET api called.")
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in ShipmentRescheduling.RESCHEDULING_REASON]
        msg = ""
        return get_response(msg, data, True)


class ReturnReasonsListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ReturnReasonsList """
        info_logger.info("ReturnReasonsList GET api called.")
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in OrderedProduct.RETURN_REASON]
        msg = ""
        return get_response(msg, data, True)


class ShipmentNotAttemptReasonsListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ShipmentNotAttemptReasonsList """
        info_logger.info("ShipmentNotAttemptReasonsList GET api called.")
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in ShipmentNotAttempt.NOT_ATTEMPT_REASON]
        msg = ""
        return get_response(msg, data, True)


class CrateRemarkReasonsListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for CrateRemarkReasonsList """
        info_logger.info("CrateRemarkReasonsList GET api called.")
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in ShipmentPackaging.RETURN_REMARK_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class DispatchTripStatusList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get shipment package rejection reason list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in DispatchTrip.DISPATCH_TRIP_STATUS]
        msg = ""
        return get_response(msg, data, True)


class LastMileTripStatusList(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in Trip.TRIP_STATUS]
        msg = ""
        return get_response(msg, data, True)


class LoadInvoiceView(generics.GenericAPIView):
    """
       View to mark invoice as added to a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DispatchTripShipmentMappingSerializer
    queryset = DispatchTripShipmentMapping.objects. \
        only('id', 'trip', 'shipment', 'shipment_status', 'shipment_health', 'trip_shipment_mapped_packages')

    def put(self, request):
        """ POST API for Shipment Package Load Verification """
        info_logger.info("Load Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        validated_shipment = validate_trip_shipment(modified_data['trip_id'], modified_data['shipment_id'])
        if 'error' in validated_shipment:
            return get_response(validated_shipment['error'])
        serializer = self.serializer_class(instance=validated_shipment['data'], data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Invoice added to the trip.")
            return get_response('Invoice added to the trip.', serializer.data)
        return get_response(serializer_error(serializer), False)


class PackagesUnderTripView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShipmentPackaging.objects.order_by('packaging_type')
    serializer_class = PackagesUnderTripSerializer

    # @check_whc_manager_dispatch_executive
    def get(self, request):
        '''
        API to get all the packages for a trip
        '''
        validated_request = self.validate_request()
        if 'error' in validated_request:
            return get_response(validated_request['error'])
        if not request.GET.get('trip_id'):
            return get_response("'trip_id' | This is mandatory")
        validated_trip = validate_trip(request.GET.get('trip_id'), request.GET.get('trip_type'))
        if 'error' in validated_trip:
            return get_response(validated_trip['error'])
        self.queryset = self.filter_packaging_items(validated_trip['data'])
        dispatch_items = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(dispatch_items, many=True)
        msg = "" if dispatch_items else "no packaging found"
        return get_response(msg, serializer.data, True)

    def validate_request(self):
        try:
            if self.request.GET.get('is_return_verified') and \
                    int(self.request.GET.get('is_return_verified')) not in [0, 1]:
                raise
        except:
            return {'error': "'is_return_verified' | Invalid value. Only 0 or 1 is allowed."}
        return {'request': self.request}

    def filter_packaging_items(self, trip_instance):
        shipment_id = self.request.GET.get('shipment_id')
        package_status = self.request.GET.get('package_status')
        trip_type = self.request.GET.get('trip_type')
        is_return_verified = self.request.GET.get('is_return_verified')
        if isinstance(trip_instance, DispatchTrip):

            package_ids = DispatchTripShipmentPackages.objects.filter(
                package_status__in=[DispatchTripShipmentPackages.LOADED,
                                    DispatchTripShipmentPackages.UNLOADED,
                                    DispatchTripShipmentPackages.VERIFIED,
                                    DispatchTripShipmentPackages.PARTIALLY_VERIFIED],
                trip_shipment__trip=trip_instance).values_list('shipment_packaging_id', flat=True)
            self.queryset = self.queryset.filter(id__in=package_ids,
                                                 shipment__trip_shipment__shipment_status__in=[
                                                     DispatchTripShipmentMapping.LOADING_FOR_DC,
                                                     DispatchTripShipmentMapping.LOADED_FOR_DC,
                                                     DispatchTripShipmentMapping.UNLOADING_AT_DC,
                                                     DispatchTripShipmentMapping.UNLOADED_AT_DC]
                                                 )
            if not trip_type or trip_type == TRIP_TYPE_CHOICE.DISPATCH_FORWARD:
                self.queryset = self.queryset.filter(shipment__trip_shipment__trip=trip_instance,
                                                     movement_type=ShipmentPackaging.DISPATCH)
            elif trip_type == TRIP_TYPE_CHOICE.DISPATCH_BACKWARD:
                self.queryset = self.queryset.filter(shipment__trip_shipment__trip=trip_instance,
                                                     movement_type=ShipmentPackaging.RETURNED)
        elif isinstance(trip_instance, Trip):
            package_ids = LastMileTripShipmentPackages.objects.filter(
                ~Q(package_status=LastMileTripShipmentPackages.CANCELLED),
                trip_shipment__trip=trip_instance,
                trip_shipment__shipment_status__in=[
                    LastMileTripShipmentMapping.TO_BE_LOADED,
                    LastMileTripShipmentMapping.LOADING_FOR_DC,
                    LastMileTripShipmentMapping.LOADED_FOR_DC]
            ) \
                .values_list('shipment_packaging_id', flat=True)
            self.queryset = self.queryset.filter(id__in=package_ids)

        if shipment_id:
            self.queryset = self.queryset.filter(shipment_id=shipment_id)

        if is_return_verified:
            is_return_verified = int(is_return_verified)
            if is_return_verified == 1:
                self.queryset = self.queryset.filter(
                    trip_packaging_details__package_status=DispatchTripShipmentPackages.VERIFIED)
            else:
                self.queryset = self.queryset.filter(trip_packaging_details__package_status__in=[
                    DispatchTripShipmentPackages.PARTIALLY_VERIFIED, DispatchTripShipmentPackages.UNLOADED])

        return self.queryset.distinct('id', 'packaging_type')


class BackWardTripReturnOrderQCView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = BackwardTripReturnItemsSerializer
    
    def get(self, request):
        validated_request = self.validate_request()
        if 'error' in validated_request:
            return get_response(validated_request['error'])
        if not request.GET.get('trip_id'):
            return get_response("'trip_id' | This is mandatory")
        if not request.GET.get('is_return_verified'):
            return get_response("'is_return_verified' | This is mandatory")
        validated_trip = validate_trip(request.GET.get('trip_id'), request.GET.get('trip_type'))
        return_items = self.filter_return_items(validated_trip['data'])
        return_items = SmallOffsetPagination().paginate_queryset(return_items, request)
        serializer = self.serializer_class(return_items, many=True)
        msg = "" if return_items else "no return items found"
        return get_response(msg, serializer.data, True)
        
    def validate_request(self):
        try:
            if self.request.GET.get('is_return_verified') and \
                    int(self.request.GET.get('is_return_verified')) not in [0, 1]:
                raise
        except:
            return {'error': "'is_return_verified' | Invalid value. Only 0 or 1 is allowed."}
        return {'request': self.request}


    def filter_return_items(self, trip_instance):
        is_return_verified = self.request.GET.get('is_return_verified')
        is_return_verified = int(is_return_verified)
        if is_return_verified == 1:
            disptach_trip_return_itens = trip_instance.return_order_details\
                .filter(return_order_status__in=[DispatchTripReturnOrderMapping.VERIFIED])
        else:
            disptach_trip_return_itens = trip_instance.return_order_details\
                .filter(return_order_status__in=[DispatchTripReturnOrderMapping.UNLOADED, 
                                                    DispatchTripReturnOrderMapping.PARTIALLY_VERIFIED])
        return disptach_trip_return_itens

                
class MarkShipmentPackageVerifiedView(generics.GenericAPIView):
    """
       View to mark shipment package verify
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = MarkShipmentPackageVerifiedSerializer
    queryset = DispatchTripShipmentPackages.objects.all()

    def get(self, request):
        '''
        API to get shipment package detail
        '''
        if not request.GET.get('package_id'):
            return get_response("'package_id' | This is mandatory")
        if not request.GET.get('trip_id'):
            return get_response("'trip_id' | This is mandatory")
        self.queryset = self.filter_package_data()
        dispatch_items = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(dispatch_items, many=True)
        msg = "" if dispatch_items else "no packaging found"
        return get_response(msg, serializer.data, True)

    def put(self, request):
        """ PUT API to mark shipment package verify """

        info_logger.info("Mark Shipment Package Verify PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'package_id' not in modified_data:
            return get_response("'package_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)

        validated_data = validate_trip_shipment_package(modified_data['trip_id'], modified_data['package_id'])
        if 'error' in validated_data:
            return get_response(validated_data['error'])
        trip_shipment_data = validated_data['data']

        serializer = self.serializer_class(instance=trip_shipment_data, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Package verified successfully.")
            return get_response('Package verified!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def filter_package_data(self):
        trip_id = self.request.GET.get('trip_id')
        package_id = self.request.GET.get('package_id')
        package_status = self.request.GET.get('package_status')

        if trip_id:
            self.queryset = self.queryset.filter(trip_shipment__trip_id=trip_id)

        if package_id:
            self.queryset = self.queryset.filter(shipment_packaging_id=package_id)

        if package_status:
            self.queryset = self.queryset.filter(status=package_status)

        return self.queryset


class MarkReturnOrderItemVerifiedView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = MarkReturnOrderItemVerifiedSerializer
    queryset = DispatchTripReturnOrderMapping.objects.all()
    
    def put(self, request):
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        if 'id' not in modified_data:
            return get_response("'id' | This is required.", False)
        
        try:
            trip_return_order_mapping = DispatchTripReturnOrderMapping.objects.get(id=modified_data['id'])
            serializer = self.serializer_class(instance=trip_return_order_mapping, data=modified_data)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                info_logger.info("Return Order verified successfully.")
                return get_response('Return Order verified!', serializer.data, True)
            return get_response(serializer_error(serializer), False)
        except DispatchTripReturnOrderMapping.DoesNotExist:
            return get_response("Return Order Item Not found, Invalid ID")
            
        
class ShipmentPackageProductsView(generics.GenericAPIView):
    """
       View to GET package products.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShipmentPackageProductsSerializer
    queryset = ShipmentPackagingMapping.objects.all()

    def get(self, request):
        """
            API to get all the products for a package
        """
        if not request.GET.get('package_id'):
            return get_response("'package_id' | This is mandatory")
        validated_shipment_label = validate_shipment_label(request.GET.get('package_id'))
        if 'error' in validated_shipment_label:
            return get_response(validated_shipment_label['error'])
        self.queryset = self.filter_shipment_products()
        dispatch_items = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(dispatch_items, many=True,
                                           context={'shop': validated_shipment_label['data'].warehouse})
        msg = "" if dispatch_items else "no product found"
        return get_response(msg, serializer.data, True)

    def filter_shipment_products(self):
        package_id = self.request.GET.get('package_id')
        product_id = self.request.GET.get('product_id')
        product_ean_code = self.request.GET.get('product_ean_code')
        batch_id = self.request.GET.get('batch_id')
        is_verified = self.request.GET.get('is_verified')

        if package_id:
            self.queryset = self.queryset.filter(shipment_packaging_id=package_id)

        if product_id:
            self.queryset = self.queryset.filter(ordered_product__product_id=product_id)

        if product_ean_code:
            self.queryset = self.queryset.filter(
                ordered_product__product__product_ean_code__startswith=product_ean_code)

        if batch_id:
            self.queryset = self.queryset.filter(ordered_product__rt_ordered_product_mapping__batch_id=batch_id)

        if is_verified:
            self.queryset = self.queryset.filter(is_verified=is_verified)

        return self.queryset


class LoadLastMileInvoiceView(generics.GenericAPIView):
    """
       View to mark invoice as added to a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LoadLastMileInvoiceSerializer
    queryset = LastMileTripShipmentMapping.objects.only('id', 'trip', 'shipment', 'shipment_status')

    @check_user_can_plan_trip
    def post(self, request):
        """ POST API to load invoice in Last mile trip """
        info_logger.info("Load invoice POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is mandatory.")
        validated_trip = validate_last_mile_trip_user(modified_data['trip_id'], request.user)
        if 'error' in validated_trip:
            return get_response(validated_trip['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Invoice added to the trip.")
            return get_response('Invoice added to the trip.', serializer.data)
        return get_response(serializer_error(serializer), False)


class RemoveLastMileInvoiceFromTripView(generics.GenericAPIView):
    """
       View to remove invoice from a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = RemoveLastMileInvoiceFromTripSerializer
    queryset = LastMileTripShipmentMapping.objects.all()

    def put(self, request):
        """ POST API for Shipment Package Load Verification """
        info_logger.info("Remove invoice PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'shipment_id' not in modified_data:
            return get_response("'shipment_id' | This is required.", False)
        if 'trip_id' not in modified_data:
            return get_response("'trip_id' | This is required.", False)

        # validations for input
        shipment_validation = self.validate_trip_invoice(int(modified_data['shipment_id']),
                                                         int(modified_data['trip_id']))
        if 'error' in shipment_validation:
            return get_response(shipment_validation['error'])
        trip_invoice_mapping = shipment_validation['data'].last()

        serializer = self.serializer_class(instance=trip_invoice_mapping, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            info_logger.info("Shipment removed successfully.")
            return get_response('Shipment removed successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def validate_trip_invoice(self, shipment_id, trip_id):
        if not self.queryset.filter(~Q(shipment_status=LastMileTripShipmentMapping.CANCELLED),
                                    trip_id=trip_id, shipment_id=shipment_id).exists():
            return {"error": "invalid Shipment"}
        return {"data": self.queryset.filter(~Q(shipment_status=LastMileTripShipmentMapping.CANCELLED),
                                             trip_id=trip_id, shipment_id=shipment_id)}


class LastMileTripSummaryView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LastMileTripSummarySerializer

    @check_whc_manager_dispatch_executive
    def get(self, request):
        """ GET API for Last mile trip summary """
        info_logger.info("Order Status Summary GET api called.")
        """ GET Trip Summary List """
        if not self.request.GET.get('trip_id', None):
            return get_response("'trip_id' | This is mandatory")
        trip_summary_data = {
            "trip_data": self.added_shipments_to_trip_summary(self.request),
            "non_trip_data": self.non_added_shipments_to_trip_summary(self.request)
        }
        serializer = self.serializer_class(trip_summary_data)
        msg = "" if trip_summary_data else "no trip found"
        return get_response(msg, serializer.data, True)

    def added_shipments_to_trip_summary(self, request):
        """ GET API for trip summary """
        info_logger.info("Added shipmets to Trip Summary called.")
        # self.queryset = get_logged_user_wise_query_set_for_trip(self.request.user, self.queryset)
        last_mile_trip_qs = Trip.objects. \
            select_related('seller_shop', 'source_shop', 'delivery_boy'). \
            prefetch_related('last_mile_trip_shipments_details'). \
            order_by('-id')
        last_mile_trip_qs = get_logged_user_wise_query_set_for_dispatch_trip(request.user, last_mile_trip_qs)
        last_mile_trip_qs = self.filter_trip_summary_data(last_mile_trip_qs)
        last_mile_trip_instance = last_mile_trip_qs.last()
        if last_mile_trip_instance:
            trip_summary_data = {
                'total_invoices': last_mile_trip_instance.no_of_shipments,
                'total_crates': last_mile_trip_instance.no_of_crates,
                'total_packets': last_mile_trip_instance.no_of_packets,
                'total_sack': last_mile_trip_instance.no_of_sacks,
                'weight': last_mile_trip_instance.get_trip_weight,
                'total_crates_check': last_mile_trip_instance.no_of_crates_check,
                'total_packets_check': last_mile_trip_instance.no_of_packets_check,
                'total_sack_check': last_mile_trip_instance.no_of_sacks_check,
                'remaining_crates': last_mile_trip_instance.no_of_crates - last_mile_trip_instance.no_of_crates_check,
                'remaining_packets': last_mile_trip_instance.no_of_packets - last_mile_trip_instance.no_of_packets_check,
                'remaining_sacks': last_mile_trip_instance.no_of_sacks - last_mile_trip_instance.no_of_sacks_check,
            }
        else:
            trip_summary_data = {
                'total_invoices': 0,
                'total_crates': 0,
                'total_packets': 0,
                'total_sack': 0,
                'weight': 0,
                'total_crates_check': 0,
                'total_packets_check': 0,
                'total_sack_check': 0,
                'remaining_crates': 0,
                'remaining_packets': 0,
                'remaining_sacks': 0
            }
        return trip_summary_data

    def non_added_shipments_to_trip_summary(self, request):
        """ GET API for trip summary """
        info_logger.info("Added shipmets to Trip Summary called.")
        # self.queryset = get_logged_user_wise_query_set_for_trip(self.request.user, self.queryset)
        current_date = datetime.now().date()
        shipment_qs = OrderedProduct.objects.filter(
            Q(shipment_status=OrderedProduct.MOVED_TO_DISPATCH) |
            Q(shipment_status=OrderedProduct.NOT_ATTEMPT, not_attempt_shipment__created_at__date__lt=current_date) |
            Q(shipment_status=OrderedProduct.RESCHEDULED, rescheduling_shipment__rescheduling_date__gte=current_date)). \
            select_related('order', 'order__seller_shop'). \
            order_by('-id')
        shipment_qs = get_logged_user_wise_query_set_for_trip_invoices(request.user, shipment_qs)
        shipment_qs = self.filter_non_added_in_trip_shipments_summary_data(shipment_qs)
        resp_data = shipment_qs.aggregate(no_of_invoices=Count('id'))
        resp_data['no_of_crates'] = 0
        resp_data['no_of_packets'] = 0
        resp_data['no_of_sacks'] = 0
        resp_data['weight'] = 0
        for ss in shipment_qs.all():
            smt_pack_data = ss.shipment_packaging. \
                exclude(last_mile_trip_packaging_details__trip_shipment__trip__trip_status=Trip.READY). \
                aggregate(no_of_crates=Count(Case(When(packaging_type=ShipmentPackaging.CRATE, then=1))),
                          no_of_packets=Count(Case(When(packaging_type=ShipmentPackaging.BOX, then=1))),
                          no_of_sacks=Count(Case(When(packaging_type=ShipmentPackaging.SACK, then=1)))
                          )
            if smt_pack_data:
                resp_data['no_of_crates'] += smt_pack_data['no_of_crates'] if smt_pack_data['no_of_crates'] else 0
                resp_data['no_of_packets'] += smt_pack_data['no_of_packets'] if smt_pack_data['no_of_packets'] else 0
                resp_data['no_of_sacks'] += smt_pack_data['no_of_sacks'] if smt_pack_data['no_of_sacks'] else 0
        trip_summary_data = {
            'total_invoices': resp_data['no_of_invoices'] if resp_data['no_of_invoices'] else 0,
            'total_crates': resp_data['no_of_crates'] if resp_data['no_of_crates'] else 0,
            'total_packets': resp_data['no_of_packets'] if resp_data['no_of_packets'] else 0,
            'total_sack': resp_data['no_of_sacks'] if resp_data['no_of_sacks'] else 0,
            'weight': resp_data['weight'] if resp_data['weight'] else 0,
            'total_crates_check': 0,
            'total_packets_check': 0,
            'total_sack_check': 0,
            'remaining_crates': 0,
            'remaining_packets': 0,
            'remaining_sacks': 0
        }
        return trip_summary_data

    def filter_trip_summary_data(self, queryset):
        trip_id = self.request.GET.get('trip_id')
        created_at = self.request.GET.get('date')
        data_days = self.request.GET.get('data_days')

        '''Filters using trip_id, created_at'''
        if trip_id:
            queryset = queryset.filter(id=trip_id)

        if created_at:
            if data_days:
                end_date = datetime.strptime(created_at, "%Y-%m-%d")
                start_date = end_date - timedelta(days=int(data_days))
                queryset = queryset.filter(
                    created_at__date__gte=start_date.date(), created_at__date__lte=end_date.date())
            else:
                created_at = datetime.strptime(created_at, "%Y-%m-%d")
                queryset = queryset.filter(created_at__date=created_at)

        return queryset

    def filter_non_added_in_trip_shipments_summary_data(self, queryset):
        trip_id = self.request.GET.get('trip_id')
        created_at = self.request.GET.get('date')
        data_days = self.request.GET.get('data_days')

        '''Filters using trip_id, created_at'''
        if trip_id:
            trip_source_shop = Trip.objects.filter(id=trip_id).last().source_shop
            queryset = queryset.filter(current_shop=trip_source_shop)
            if trip_source_shop.shop_type.shop_type == 'sp':
                queryset = queryset.filter(order__dispatch_center__isnull=True)
            if trip_source_shop.shop_type.shop_type == 'dc':
                queryset = queryset.filter(order__dispatch_center=trip_source_shop)

        if created_at:
            if data_days:
                end_date = datetime.strptime(created_at, "%Y-%m-%d")
                start_date = end_date - timedelta(days=int(data_days))
                queryset = queryset.filter(
                    created_at__date__gte=start_date.date(), created_at__date__lte=end_date.date())
            else:
                created_at = datetime.strptime(created_at, "%Y-%m-%d")
                queryset = queryset.filter(created_at__date=created_at)

        return queryset


class LastMileLoadVerifyPackageView(generics.GenericAPIView):
    """
       View to verify and load packages to a trip.
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LastMileLoadVerifyPackageSerializer

    def post(self, request):
        """ POST API for Shipment Package Load Verification """
        info_logger.info("Load Verify POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])
        validated_trip = validate_last_mile_trip_user(modified_data['trip_id'], request.user)
        if 'error' in validated_trip:
            return get_response(validated_trip['error'])
        serializer = self.serializer_class(data=modified_data, context={'current_user': request.user})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Package loaded Successfully.")
            return get_response('Package loaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class VerifyBackwardTripItems(generics.GenericAPIView):
    """
    API view to verify Packages reaching warehouse in backward dispatch trip
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = VerifyBackwardTripItemsSerializer
    queryset = ShipmentPackagingMapping.objects \
        .select_related('ordered_product', 'ordered_product__product') \
        .prefetch_related('shipment_packaging__trip_packaging_details__trip_shipment',
                          'ordered_product__rt_ordered_product_mapping') \
        .order_by('-id')

    def get(self, request):

        info_logger.info(f"VerifyBackwardTripItems | GET | user {request.user} | request {request.GET}")

        if request.GET.get('id'):
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            item_data = id_validation['data']

        else:
            """ Get Item Data for specific trip and batch/ean """
            if not request.GET.get('trip_id'):
                return get_response('trip_id is required', False)
            elif not request.GET.get('package_id'):
                return get_response('package_id is required', False)
            elif not (request.GET.get('batch_id') or request.GET.get('ean')):
                return get_response('please batch_id id / ean  is required', False)
            item_data = self.filter_item_data()

        serializer = self.serializer_class(item_data, many=True)
        msg = "" if item_data.exists() else "no item found"
        return get_response(msg, serializer.data, True)

    ## Permission to return executive only
    def put(self, request):

        info_logger.info(f"VerifyBackwardTripItems | GET | user {request.user} | request data {request.data}")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'trip_id' not in modified_data:
            return get_response('trip_id is required.', False)
        elif 'package_id' not in modified_data:
            return get_response('package_id is required.', False)
        elif 'id' not in modified_data:
            return get_response('id is required.', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        item_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=item_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('process_shipment updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def filter_item_data(self):
        """ Filters the Shipment data based on request"""
        trip_id = self.request.GET.get('trip_id')
        package_id = self.request.GET.get('package_id')
        batch_id = self.request.GET.get('batch_id')
        ean = self.request.GET.get('ean')

        if trip_id:
            self.queryset = self.queryset.filter(
                shipment_packaging__trip_packaging_details__trip_shipment__trip_id=trip_id)

        if package_id:
            self.queryset = self.queryset.filter(shipment_packaging_id=package_id)

        if batch_id:
            self.queryset = self.queryset.filter(ordered_product__rt_ordered_product_mapping__batch_id=batch_id)

        if ean:
            self.queryset = self.queryset.filter(ordered_product__product__product_ean_code__startswith=ean)

        return self.queryset.distinct('id')


class BackwardTripQCView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = DispatchTripShipmentPackages.objects.all()
    serializer_class = BackwardTripQCSerializer

    def get(self, request):
        if not request.GET.get('trip_id'):
            return get_response("'trip_id' | This is mandatory")
        validated_trip = validate_trip(request.GET.get('trip_id'), TRIP_TYPE_CHOICE.DISPATCH_BACKWARD)
        if 'error' in validated_trip:
            return get_response(validated_trip['error'])
        self.queryset = self.filter_packaging_items(validated_trip['data'])
        serializer = self.serializer_class(self.queryset)
        msg = "" if self.queryset.exists() else "no package pending for QC."
        return get_response(msg, serializer.data, True)

    def filter_packaging_items(self, trip_instance):
        self.queryset = self.queryset.filter(package_status=DispatchTripShipmentPackages.UNLOADED,
                                             trip_shipment__trip=trip_instance,
                                             trip_shipment__shipment_status=DispatchTripShipmentMapping.UNLOADED_AT_DC)
        return self.queryset


class PosOrderUserSearchView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = PosOrderUserSearchSerializer

    def get(self, request, *args, **kwargs):
        search = request.query_params.get('search')
        shop_id = request.META.get('HTTP_SHOP_ID')
        if search:
            orders = Order.objects.filter(seller_shop_id=shop_id)
            users = User.objects.filter(id__in=Subquery(orders.values('buyer_id')))
            if search.isnumeric() and len(search) >= 5:
                qs = users.filter(phone_number__istartswith=search)
            elif len(search) >= 3:
                qs = users.filter(first_name__istartswith=search)
            else:
                qs = None
            serializer = self.serializer_class(qs, many=True)
            msg = 'success'
            return get_response(msg, serializer.data, True)
        else:
            msg = 'Search to get Buyers.'
            return get_response(msg, '', True)


class GenerateBarcodes(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = (authentication.TokenAuthentication,)

    def post(self, request):
        validated_request = self.validate_request(request)
        if 'error' in validated_request:
            return get_response(validated_request['error'])
        batch_size = request.data.get('count')
        barcode_type = request.data.get('type')
        available_barcodes = Barcode.objects.filter(generator__barcode_type=barcode_type, is_available=True)[
                             :batch_size]
        available_barcodes_count = available_barcodes.count()
        if available_barcodes_count < batch_size:
            required_barcodes = batch_size - available_barcodes_count
            last_generated = BarcodeGenerator.objects.filter(barcode_type=barcode_type).last()
            if last_generated:
                sequence_no = last_generated.last_sequence
            else:
                sequence_no = 0
            last_sequence = sequence_no + required_barcodes
            barcode_no = int(str(barcode_type) + str(sequence_no).zfill(10))
            with transaction.atomic():
                generator = BarcodeGenerator.objects.create(barcode_type=barcode_type, batch_size=batch_size,
                                                            last_sequence=last_sequence, created_by=self.request.user)
                Barcode.objects.bulk_create([Barcode(generator=generator, barcode_no='0' + str(barcode_no + i))
                                             for i in range(1, required_barcodes + 1)],
                                            batch_size=BULK_CREATE_NO_OF_RECORDS)
            available_barcodes = Barcode.objects.filter(generator__barcode_type=barcode_type, is_available=True)[
                                 :batch_size]
        barcode_list = list(available_barcodes.values_list('barcode_no', flat=True))
        barcode_dict = {b: {"qty": 1, "data": None} for b in barcode_list}
        return merged_barcode_gen(barcode_dict, 'admin/retailer_to_sp/barcode.html')

    def validate_request(self, request):
        if 'count' not in request.data or request.data.get('count') <= 0:
            return {'error': 'Invalid count'}
        elif 'type' not in request.data or request.data.get('type') != 6:
            return {'error': 'Invalid type'}
        return {'data': self.request.data}


class ReturnRejection(generics.ListCreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ShipmentReschedulingSerializer

    def list(self, request, *args, **kwargs):
        data = [{'name': reason[0], 'display_name': reason[1]} for reason in ReturnOrder.REJECT_REASONS]
        msg = {'is_success': True, 'message': None, 'response_data': data}
        return Response(msg, status=status.HTTP_200_OK)

    def put(self, request):
        result = self.validate_put_request()
        if "error" in result:
            result = {"is_success": False, "message": [result["error"]], "response_data": ''}
            return Response(result, status=status.HTTP_200_OK)
        return_id = self.request.data.get('return_id', None)
        reject_reason = self.request.data.get('reject_reason', None)
        orderreturn = ReturnOrder.objects.filter(pk=return_id).last()
        trip_id = orderreturn.last_mile_trip_returns.last().trip.id
        if orderreturn.return_status != ReturnOrder.RETURN_INITIATED:
            result = {"is_success": False, "message": ["error: Return not found in initiated state"], "response_data": ''}
            return Response(result, status=status.HTTP_200_OK)
        orderreturn.reject_reason = reject_reason
        orderreturn.return_status = ReturnOrder.RETURN_REJECTED
        with transaction.atomic():
            orderreturn.save()
            update_trip_status(trip_id)
        return get_response(["return rejected"], '', True)

    def validate_put_request(self):
        try:
            if not self.request.data.get('return_id', None):
                return {"error": "'return_id'| This is required"}
            elif not self.request.data.get('return_item_id', None):
                return {"error": "'return_item_id' | This is required."}
            elif not self.request.data.get('reject_reason', None):
                return {"error": "'reject_reason'| This is required"}
            elif not any(self.request.data['reject_reason'] in reason for reason in ReturnOrder.REJECT_REASONS):
                return {"error": "'reject_reason'| Invalid"}
            return {"data": self.request.data}
        except Exception as e:
            return {"error": "Invalid Request"}


class PastPurchasedProducts(APIView):
    """
    API to get the products purchased by a user
    """

    authentication_classes = (TokenAuthentication,)
    serializer_class = PastPurchasedProductSerializer
    pagination_class = SmallOffsetPagination
    def get(self, request, *args, **kwargs):
        '''
        Get retailer products purchase by a user for specific shop
        '''
        shop = Shop.objects.filter(id=request.GET.get('shop_id',request.META.get('HTTP_SHOP_ID', None))).last()
        if not shop:
            return api_response("Shop not available!")
        shop_mapping =  getShopMapping(shop)
        products = Product.objects.filter(retail_products_sold__buyer_shop=shop_mapping.retailer, retail_products_sold__shop=shop_mapping.parent,).\
            order_by('-retail_products_sold__id')
        count = products.count()
        products = self.pagination_class().paginate_queryset(products, self.request)
        product_id_list = {"products_id" : [i.id for i in products]}
        #serializer = RetailPastPurchesSerlizer(products,many=True, context={'seller_shop':shop_mapping.parent})
        is_success, data, msg = True, product_id_list, f"{count} record/s found"
        return api_response(msg, data, status.HTTP_200_OK, is_success)