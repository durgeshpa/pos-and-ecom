import logging
import re
from decimal import Decimal
import json
import requests
from datetime import datetime, timedelta
from operator import itemgetter

from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Sum, Q
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.generics import GenericAPIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, generics, viewsets, permissions, authentication

from wkhtmltopdf.views import PDFTemplateResponse
from num2words import num2words

from retailer_backend.utils import SmallOffsetPagination
from retailer_backend.common_function import getShopMapping, checkNotShopAndMapping, getShop
from retailer_backend.messages import ERROR_MESSAGES

from audit.views import BlockUnblockProduct
from barCodeGenerator import barcodeGen
from wms.views import shipment_reschedule_inventory_change
from .serializers import (ProductsSearchSerializer, CartSerializer, OrderSerializer,
                          CustomerCareSerializer, OrderNumberSerializer, GramPaymentCodSerializer,
                          GramMappedCartSerializer, GramMappedOrderSerializer,
                          OrderDetailSerializer, OrderedProductSerializer, OrderedProductMappingSerializer,
                          RetailerShopSerializer, SellerOrderListSerializer, OrderListSerializer,
                          ReadOrderedProductSerializer, FeedBackSerializer, CancelOrderSerializer,
                          ShipmentDetailSerializer, TripSerializer, ShipmentSerializer, PickerDashboardSerializer,
                          ShipmentReschedulingSerializer, ShipmentReturnSerializer, ParentProductImageSerializer
                          )
from products.models import ProductPrice, ProductOption, Product
from sp_to_gram.models import OrderedProductReserved
from categories import models as categorymodel
from gram_to_brand.models import (GRNOrderProductMapping, OrderedProductReserved as GramOrderedProductReserved,
                                  PickList
                                  )
from retailer_to_sp.models import (Cart, CartProductMapping, Order, OrderedProduct, Payment, CustomerCare,
                                   Feedback, OrderedProductMapping as ShipmentProducts, Trip, PickerDashboard,
                                   ShipmentRescheduling, Note, OrderedProductBatch,
                                   OrderReturn, ReturnItems, Return)
from retailer_to_sp.common_function import check_date_range, capping_check
from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping,
                                     Order as GramMappedOrder
                                     )
from shops.models import Shop, ParentRetailerMapping, ShopUserMapping, ShopMigrationMapp
from brand.models import Brand
from addresses.models import Address
from wms.common_functions import OrderManagement, get_stock, is_product_not_eligible
from common.data_wrapper_view import DataWrapperViewSet
from common.data_wrapper import format_serializer_errors
from sp_to_gram.tasks import es_search, upload_shop_stock
from coupon.serializers import CouponSerializer
from coupon.models import Coupon, CusotmerCouponUsage
from common.constants import ZERO, PREFIX_INVOICE_FILE_NAME, INVOICE_DOWNLOAD_ZIP_NAME
from common.common_utils import (create_file_name, single_pdf_file, create_merge_pdf_name, merge_pdf_files,
                                 create_invoice_data, whatsapp_opt_in, whatsapp_order_cancel,
                                 whatsapp_order_refund)
from wms.models import WarehouseInternalInventoryChange, OrderReserveRelease, InventoryType, PosInventoryState,\
    PosInventoryChange
from pos.common_functions import api_response, delete_cart_mapping, ORDER_STATUS_MAP, RetailerProductCls, \
    update_pos_customer, PosInventoryCls, RewardCls, filter_pos_shop
from pos.offers import BasicCartOffers
from pos.api.v1.serializers import BasicCartSerializer, BasicCartListSerializer, CheckoutSerializer, \
    BasicOrderSerializer, BasicOrderListSerializer, OrderReturnCheckoutSerializer, OrderedDashBoardSerializer, \
    PosShopSerializer
from pos.models import RetailerProduct, PAYMENT_MODE_POS, Payment as PosPayment, UserMappedShop
from retailer_backend.settings import AWS_MEDIA_URL
from pos.tasks import update_es, order_loyalty_points
from pos import error_code
from accounts.api.v1.serializers import PosUserSerializer
from global_config.models import GlobalConfig
from elasticsearch import Elasticsearch
from pos.common_functions import check_pos_shop

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])

User = get_user_model()

logger = logging.getLogger('django')

today = datetime.today()
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


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
        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        if search_type == '1':
            results = self.rp_exact_search(shop_id)
        # Normal Search
        elif search_type == '2':
            results = self.rp_normal_search(shop_id)
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
        body = dict()
        if ean_code and ean_code != '':
            body["query"] = {"bool": {"filter": [{"term": {"ean": ean_code}}]}}
        return self.process_rp(output_type, body, shop_id)

    def rp_normal_search(self, shop_id):
        """
            Search Retailer Shop Catalogue On Similar Match
        """
        keyword = self.request.GET.get('keyword')
        output_type = self.request.GET.get('output_type', '1')
        body = dict()
        if keyword:
            keyword = keyword.strip()
            if keyword.isnumeric():
                body['query'] = {"query_string": {"query": keyword + "*", "fields": ["ean"]}}
            else:
                tokens = keyword.split()
                keyword = ""
                for word in tokens:
                    keyword += "*" + word + "* "
                keyword = keyword.strip()
                body['query'] = {
                    "query_string": {"query": "*" + keyword + "*", "fields": ["name"], "minimum_should_match": 2}}
        return self.process_rp(output_type, body, shop_id)

    @check_pos_shop
    def rp_gf_search(self, request, *args, **kwargs):
        """
            Search Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
        """
        shop_id = kwargs['shop'].id
        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        if search_type == '1':
            results = self.rp_gf_exact_search(shop_id)
        elif search_type == '2':
            results = self.rp_gf_normal_search(shop_id)
        else:
            return api_response("Provide a valid search type")
        if results:
            return api_response('Products Found', results, status.HTTP_200_OK, True)
        else:
            return api_response('No Products Found', None, status.HTTP_200_OK)

    def rp_gf_exact_search(self, shop_id):
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
            gf_results = self.gf_exact_search()
            if gf_results:
                response['product_type'] = 'gf_catalogue'
                response['products'] = gf_results
        return response

    def rp_gf_normal_search(self, shop_id):
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
            gf_results = self.gf_pos_normal_search()
            if gf_results:
                response['product_type'] = 'gf_catalogue'
                response['products'] = gf_results
        return response

    def process_rp(self, output_type, body, shop_id):
        """
            Modify Es results for response based on output_type - Raw OR Processed
        """
        body["from"] = int(self.request.GET.get('offset', 0))
        body["size"] = int(self.request.GET.get('pro_count', 50))
        body["sort"] = {"modified_at": "desc"}
        p_list = []
        # Raw Output
        if output_type == '1':
            body["_source"] = {"includes": ["id", "name", "ptr", "mrp", "margin", "ean", "status", "product_images",
                                            "description", "linked_product_id", "stock_qty"]}
            try:
                products_list = es_search(index='rp-{}'.format(shop_id), body=body)
                for p in products_list['hits']['hits']:
                    p_list.append(p["_source"])
            except Exception as e:
                error_logger.error(e)
        # Processed Output
        else:
            body["_source"] = {"includes": ["id", "name", "ptr", "mrp", "margin", "ean", "status", "product_images",
                                            "description", "linked_product_id", "stock_qty"]}
            try:
                products_list = es_search(index='rp-{}'.format(shop_id), body=body)
                for p in products_list['hits']['hits']:
                    # Combo Offers On Products
                    p["_source"]['coupons'] = BasicCartOffers.get_basic_combo_coupons([p["_source"]["id"]], shop_id, 10,
                                                                                      ["coupon_code", "coupon_type"])
                    p_list.append(p["_source"])
            except Exception as e:
                error_logger.error(e)
        return p_list

    def gf_search(self):
        """
            Search GramFactory Catalogue
        """
        search_type = self.request.GET.get('search_type', '2')
        app_type = self.request.GET.get('app_type', '0')
        if app_type != '2':
            # Normal Search
            if search_type == '2':
                results, is_store_active = self.gf_normal_search()
                if results:
                    return api_response(['Products Found'], results, status.HTTP_200_OK, True, is_store_active)
                else:
                    return api_response(['No Products Found'], None, status.HTTP_200_OK, False, is_store_active)
            else:
                return api_response(["Please Provide A Valid Search Type"])
        else:
            # Exact Search
            if search_type == '1':
                results = self.gf_exact_search()
            # Normal Search
            elif search_type == '2':
                results = self.gf_pos_normal_search()
            else:
                return api_response("Please Provide A Valid Search Type")
            if results:
                return api_response('Products Found', results, status.HTTP_200_OK, True)
            else:
                return api_response('Product not found in GramFactory catalog. Please add new Product.', None, status.HTTP_200_OK)

    def gf_exact_search(self):
        """
            Search GramFactory Catalogue Exact Ean
        """
        ean_code = self.request.GET.get('ean_code')
        body = dict()
        if ean_code and ean_code != '':
            body["query"] = {"bool": {"filter": [{"term": {"ean": ean_code}}]}}
        return self.process_gf(body)

    def gf_normal_search(self):
        """
            Search GramFactory Catalogue By Name, Brand, Category
            Full catalogue or for a particular parent shop
        """
        shop_id = self.request.GET.get('shop_id') if self.request.GET.get('shop_id') else None
        shop, parent_shop, cart_products, cart, cart_check = None, None, None, None, False
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
        body = {'query': query, }
        return self.process_gf(body, shop, parent_shop, cart_check, cart, cart_products), is_store_active

    def gf_pos_normal_search(self):
        """
            Search GramFactory Catalogue By Name
        """
        body = {'query': self.search_query(), }
        return self.process_gf(body)

    def process_gf(self, body, shop=None, parent_shop=None, cart_check=False, cart=None, cart_products=None):
        """
            Modify Es results for response based on shop
        """
        body["from"] = int(self.request.GET.get('offset', 0))
        body["size"] = int(self.request.GET.get('pro_count', 100))
        p_list = []
        # No Shop Id OR Store Inactive
        if not parent_shop:
            body["_source"] = {"includes": ["id", "name", "product_images", "pack_size", "weight_unit", "weight_value",
                                            "visible", "mrp", "ean"]}
            products_list = es_search(index='all_products', body=body)
            for p in products_list['hits']['hits']:
                p["_source"]["description"] = p["_source"]["name"]
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
        return p_list

    def search_query(self):
        """
            Search query for gf normal search
        """
        product_ids = self.request.GET.get('product_ids')
        brand = self.request.GET.get('brands')
        category = self.request.GET.get('categories')
        keyword = self.request.GET.get('keyword', None)
        filter_list = []
        if self.request.GET.get('app_type') != '2':
            filter_list = [
                {"term": {"status": True}},
                {"term": {"visible": True}},
                {"range": {"available": {"gt": 0}}}
            ]
        if product_ids:
            product_ids = product_ids.split(',')
            filter_list.append({"ids": {"type": "product", "values": product_ids}})
            query = {"bool": {"filter": filter_list}}
            return query
        query = {"bool": {"filter": filter_list}}
        if not (category or brand or keyword):
            return query
        if brand:
            brand = brand.split(',')
            brand_name = "{} -> {}".format(Brand.objects.filter(id__in=list(brand)).last(), keyword)
            filter_list.append({"match": {
                "brand": {"query": brand_name, "fuzziness": "AUTO", "operator": "and"}
            }})
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
                        p["_source"]["discounted_product_subtotal"] = i['discounted_product_subtotal']
                brand_offers = list(filter(lambda d: d['sub_type'] in ['discount_on_brand'], cart_offers))
                for j in p["_source"]["coupon"]:
                    for i in (brand_offers + product_offers):
                        if j['coupon_code'] == i['coupon_code']:
                            j['is_applied'] = True
            p["_source"]["user_selected_qty"] = c_p.qty or 0
            p["_source"]["ptr"] = c_p.applicable_slab_price
            p["_source"]["no_of_pieces"] = int(c_p.qty) * int(c_p.cart_product.product_inner_case_size)
            p["_source"]["sub_total"] = c_p.qty * c_p.item_effective_prices
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
        filter_list = [{"term": {"status": True}}, {"term": {"visible": True}}, {"range": {"available": {"gt": 0}}}]
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
                parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
                if parent_mapping.parent.shop_type.shop_type == 'sp':
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
                cart_type (retail-1 or basic-2)
        """
        cart_type = self.request.GET.get('cart_type', '1')
        if cart_type == '1':
            return self.get_retail_cart()
        elif cart_type == '2':
            if self.request.GET.get('cart_id'):
                return self.get_basic_cart(request, *args, **kwargs)
            else:
                return self.get_basic_cart_list(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid cart_type')

    def post(self, request, *args, **kwargs):
        """
            Add To Cart
            Inputs
                cart_type (retail-1 or basic-2)
                cart_product (Product for 'retail', RetailerProduct for 'basic'
                shop_id (Buyer shop id for 'retail', Shop id for selling shop in case of 'basic')
                qty (Quantity of product to be added)
        """
        cart_type = self.request.data.get('cart_type', '1')
        if cart_type == '1':
            return self.retail_add_to_cart()
        elif cart_type == '2':
            return self.basic_add_to_cart(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid cart_type')

    def put(self, request, *args, **kwargs):
        """
            Add/Update Item To Basic Cart
            Inputs
                cart_type (2)
                product_id
                shop_id
                cart_id
                qty
        """
        cart_type = self.request.data.get('cart_type')
        if cart_type == '2':
            return self.basic_add_to_cart(request, *args, **kwargs)
        else:
            return api_response('Please provide a valid cart_type')

    @check_pos_shop
    def delete(self, request, *args, **kwargs):
        """
            Update Cart Status To deleted For Basic Cart
        """
        # Check If Cart Exists
        try:
            cart = Cart.objects.get(id=kwargs['pk'], cart_status__in=['active', 'pending'],
                                    seller_shop=kwargs['shop'])
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
                self.update_cart_qty(cart, cart_products)
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
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None, status.HTTP_200_OK)

    @check_pos_shop
    def get_basic_cart(self, request, *args, **kwargs):
        """
            Get Cart
            For cart_type "basic"
        """
        try:
            cart = Cart.objects.get(seller_shop=kwargs['shop'], id=self.request.GET.get('cart_id'))
        except ObjectDoesNotExist:
            return api_response("Cart Not Found!")
        # Refresh cart prices
        self.refresh_cart_prices(cart)
        # Refresh - add/remove/update combo, get nearest cart offer over cart value
        next_offer = BasicCartOffers.refresh_offers_cart(cart)
        return api_response('Cart', self.get_serialize_process_basic(cart, next_offer), status.HTTP_200_OK, True)

    @staticmethod
    def refresh_cart_prices(cart):
        cart_products = cart.rt_cart_list.all()
        if cart_products:
            for product_mapping in cart_products:
                product_mapping.selling_price = product_mapping.retailer_product.selling_price
                product_mapping.save()

    @check_pos_shop
    def get_basic_cart_list(self, request, *args, **kwargs):
        """
            List active carts for seller shop
        """
        search_text = self.request.GET.get('search_text')
        carts = Cart.objects.select_related('buyer').prefetch_related('rt_cart_list').filter(seller_shop=kwargs['shop'],
                                                                                             cart_status__in=['active', 'pending']).order_by('-modified_at')
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
    def update_cart_qty(cart, cart_products):
        """
            Update number of pieces for all products in cart
        """
        for cart_product in cart_products:
            item_qty = CartProductMapping.objects.filter(cart=cart,
                                                         cart_product=cart_product.cart_product).last().qty
            updated_no_of_pieces = (item_qty * int(cart_product.cart_product.product_inner_case_size))
            CartProductMapping.objects.filter(cart=cart, cart_product=cart_product.cart_product).update(
                no_of_pieces=updated_no_of_pieces)

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
                                                       'delivery_message': self.delivery_message()})
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
            return api_response(['Sorry shop is not associated with any Gramfactory or any SP'], None, status.HTTP_200_OK)

    @check_pos_shop
    def basic_add_to_cart(self, request, *args, **kwargs):
        """
            Add To Cart
            For cart type 'basic'
        """
        with transaction.atomic():
            # basic validations for inputs
            cart_id = kwargs['pk'] if 'pk' in kwargs else None
            shop = kwargs['shop']
            initial_validation = self.post_basic_validate(shop, cart_id)
            if 'error' in initial_validation:
                e_code = initial_validation['error_code'] if 'error_code' in initial_validation else None
                extra_params = {'error_code': e_code} if e_code else {}
                return api_response(initial_validation['error'], None, status.HTTP_406_NOT_ACCEPTABLE, False,
                                    extra_params)
            product = initial_validation['product']
            qty = initial_validation['quantity']
            cart = initial_validation['cart']

            # Update or create cart for shop
            cart = self.post_update_basic_cart(shop, cart)
            # Check if product has to be removed
            if int(qty) == 0:
                delete_cart_mapping(cart, product, 'basic')
            else:
                # Check if price needs to be updated and return selling price
                selling_price = self.get_basic_cart_product_price(product)
                # Add quantity to cart
                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, retailer_product=product,
                                                                           product_type=1)
                cart_mapping.selling_price = selling_price
                cart_mapping.qty = qty
                cart_mapping.no_of_pieces = int(qty)
                cart_mapping.save()
            # serialize and return response
            return api_response('Added To Cart', self.post_serialize_process_basic(cart), status.HTTP_200_OK, True)

    def post_retail_validate(self):
        """
            Add To Cart
            Input validation for cart type 'retail'
        """
        qty = self.request.data.get('qty')
        shop_id = self.request.data.get('shop_id')
        # Added Quantity check
        if qty is None or qty == '':
            return {'error': "Qty Not Found!"}
        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        # Check if product exists
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

    def post_basic_validate(self, shop, cart_id=None):
        """
            Add To Cart
            Input validation for add to cart for cart type 'basic'
        """
        # Added Quantity check
        qty = self.request.data.get('qty')
        if qty is None or not str(qty).isdigit() or qty < 0 or (qty == 0 and not cart_id):
            return {'error': "Qty Invalid!"}

        if not self.request.data.get('product_id'):
            name, sp, ean = self.request.data.get('product_name'), self.request.data.get('selling_price'), \
                            self.request.data.get('product_ean_code')
            if not (name and sp and ean):
                return {'error': "Please provide product_id OR product_name, product_ean_code, selling_price!"}
            linked_pid = self.request.data.get('linked_product_id') if self.request.data.get(
                'linked_product_id') else None
            mrp, linked = 0, 1
            if linked_pid:
                linked_product = Product.objects.filter(id=linked_pid).last()
                if not linked_product:
                    return {'error': f"GramFactory product not found for given {linked_pid}"}
                mrp, linked = linked_product.product_mrp, 2
            product = RetailerProductCls.create_retailer_product(shop.id, name, mrp, sp, linked_pid, linked, None, ean)
            PosInventoryCls.stock_inventory(product.id, PosInventoryState.NEW, PosInventoryState.AVAILABLE, 0,
                                            self.request.user, product.sku, PosInventoryChange.STOCK_ADD)
        else:
            try:
                product = RetailerProduct.objects.get(id=self.request.data.get('product_id'), shop=shop)
            except ObjectDoesNotExist:
                return {'error': "Product Not Found!"}
        # Check if existing or new cart
        cart = None
        if cart_id:
            cart = Cart.objects.filter(id=cart_id, seller_shop=shop).last()
            if not cart:
                return {'error': "Cart Doesn't Exist!"}
            elif cart.cart_status == Cart.ORDERED:
                return {'error': "Order already placed on this cart!", 'error_code': error_code.CART_NOT_ACTIVE}
            elif cart.cart_status == Cart.DELETED:
                return {'error': "This cart was deleted!", 'error_code': error_code.CART_NOT_ACTIVE}
            elif cart.cart_status not in [Cart.ACTIVE, Cart.PENDING]:
                return {'error': "Active Cart Doesn't Exist!"}
        # Check if selling price is less than equal to mrp if price change
        price_change = self.request.data.get('price_change')
        if price_change in [1, 2]:
            selling_price = self.request.data.get('selling_price')
            if not selling_price:
                return {'error': "Please provide selling price to change price"}
            if product.mrp and Decimal(selling_price) > product.mrp:
                return {'error': "Selling Price should be equal to OR less than MRP"}
        # activate product in cart
        if product.status != 'active':
            product.status = 'active'
            product.save()
        return {'product': product, 'quantity': qty, 'cart': cart}

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
        available_qty = shop_products_dict[int(product.id)] // int(cart_mapping.cart_product.product_inner_case_size)
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

    def get_basic_cart_product_price(self, product):
        """
            Check if retail product price needs to be changed on checkout
            price_change - 1 (change for all), 2 (change for current cart only)
        """
        # Check If Price Change
        price_change = self.request.data.get('price_change')
        selling_price = None
        if price_change in [1, 2]:
            selling_price = self.request.data.get('selling_price')
            if price_change == 1 and selling_price:
                RetailerProductCls.update_price(product.id, selling_price)
        return selling_price if selling_price else product.selling_price

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
        customer = User.objects.filter(phone_number=phone_no).last()
        if customer:
            data, msg = PosUserSerializer(customer).data, 'Customer Detail Success'
        return api_response(msg, data, status.HTTP_200_OK, True)


class CartUserView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    def put(self, request, *args, **kwargs):
        """
            Update buyer in cart
        """
        cart_type = request.data.get('cart_type', '1')
        if cart_type == '2':
            # Input validation
            initial_validation = self.put_basic_validate(kwargs['pk'], kwargs['shop'])
            if 'error' in initial_validation:
                e_code = initial_validation['error_code'] if 'error_code' in initial_validation else None
                extra_params = {'error_code': e_code} if e_code else {}
                return api_response(initial_validation['error'], None, status.HTTP_406_NOT_ACCEPTABLE, False,
                                    extra_params)
            cart = initial_validation['cart']
            customer = update_pos_customer(self.request.data.get('phone_number'), cart.seller_shop.id,
                                           self.request.data.get('email'), self.request.data.get('name'),
                                           self.request.data.get('is_whatsapp'))
            cart.buyer = customer
            cart.last_modified_by = self.request.user
            cart.save()
            data = PosUserSerializer(customer).data
            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, 0)
            # Reward detail for customer
            data['reward_detail'] = RewardCls.reward_detail_cart(cart, 0)
            return api_response('Customer Detail Success', data, status.HTTP_200_OK, True)
        else:
            return api_response('Provide a valid cart_type')

    def put_basic_validate(self, cart_id, shop):
        """
            Add To Cart
            Input validation for add to cart for cart type 'basic'
        """
        # Check cart
        cart = Cart.objects.filter(id=cart_id, seller_shop=shop).last()
        if not cart:
            return {'error': "Cart Doesn't Exist!"}
        elif cart.cart_status == Cart.ORDERED:
            return {'error': "Order already placed on this cart!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status == Cart.DELETED:
            return {'error': "This cart was deleted!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status not in [Cart.ACTIVE, Cart.PENDING]:
            return {'error': "Active Cart Doesn't Exist!"}
        phone_no = self.request.data.get('phone_number')
        if not phone_no:
            return api_response("Please provide phone number")
        if not re.match(r'^[6-9]\d{9}$', phone_no):
            return api_response("Please provide a valid phone number")
        return {'cart': cart}


class CartCheckout(APIView):
    """
        Checkout after items added
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    def post(self, request, *args, **kwargs):
        """
            Checkout
            Apply Any Available Cart Offer - Either coupon or spot discount
            Inputs
            cart_id
            coupon_id
            spot_discount
            is_percentage (spot discount type)
        """
        # Input validation
        initial_validation = self.post_validate(kwargs['shop'])
        if 'error' in initial_validation:
            return api_response(initial_validation['error'])
        cart = initial_validation['cart']
        # Check spot discount
        spot_discount = self.request.data.get('spot_discount')
        with transaction.atomic():
            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, cart.redeem_points)
            if spot_discount:
                offers = BasicCartOffers.apply_spot_discount(cart, spot_discount,
                                                             self.request.data.get('is_percentage'))
            else:
                # Get offers available now and apply coupon if applicable
                offers = BasicCartOffers.refresh_offers_checkout(cart, False, self.request.data.get('coupon_id'))
            if 'error' in offers:
                return api_response(offers['error'], None, offers['code'])
            if offers['applied']:
                return api_response('Applied Successfully', self.serialize(cart), status.HTTP_200_OK, True)
            else:
                return api_response('Not Applicable', self.serialize(cart), status.HTTP_200_OK)

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
            Get Checkout Amount Info, Offers Applied-Applicable
        """
        cart_id = self.request.GET.get('cart_id')
        try:
            cart = Cart.objects.get(pk=cart_id, seller_shop=kwargs['shop'], cart_status__in=['active', 'pending'])
        except ObjectDoesNotExist:
            return api_response("Cart Does Not Exist / Already Closed")
        # Auto apply highest applicable discount
        auto_apply = self.request.GET.get('auto_apply')
        with transaction.atomic():
            # Get Offers Applicable, Verify applied offers, Apply highest discount on cart if auto apply
            offers = BasicCartOffers.refresh_offers_checkout(cart, auto_apply, None)
            # Redeem reward points on order
            redeem_points = self.request.GET.get('redeem_points')
            redeem_points = redeem_points if redeem_points else cart.redeem_points
            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, int(redeem_points))
            return api_response("Cart Checkout", self.serialize(cart, offers), status.HTTP_200_OK, True)

    @check_pos_shop
    def delete(self, request, *args, **kwargs):
        """
            Checkout
            Delete any applied cart offers
        """
        try:
            cart = Cart.objects.get(pk=kwargs['pk'], seller_shop=kwargs['shop'], cart_status__in=['active', 'pending'])
        except ObjectDoesNotExist:
            return api_response("Cart Does Not Exist / Already Closed")
        # Refresh redeem reward
        RewardCls.checkout_redeem_points(cart, cart.redeem_points)
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        for product_map in cart_products:
            cart_value += product_map.selling_price * product_map.qty
        with transaction.atomic():
            offers_list = BasicCartOffers.update_cart_offer(cart.offers, cart_value)
            Cart.objects.filter(pk=cart.id).update(offers=offers_list)
            return api_response("Removed Offer From Cart Successfully", self.serialize(cart), status.HTTP_200_OK, True)

    def post_validate(self, shop):
        """
            Add cart offer in checkout
            Input validation
        """
        cart_id = self.request.data.get('cart_id')
        try:
            cart = Cart.objects.get(pk=cart_id, seller_shop=shop, cart_status__in=['active', 'pending'])
        except ObjectDoesNotExist:
            return {'error': "Cart Does Not Exist / Already Closed"}
        if not self.request.data.get('coupon_id') and not self.request.data.get('spot_discount'):
            return {'error': "Please Provide Coupon Id/Spot Discount"}
        if self.request.data.get('coupon_id') and self.request.data.get('spot_discount'):
            return {'error': "Please Provide Only One Of Coupon Id, Spot Discount"}
        if self.request.data.get('spot_discount') and self.request.data.get('is_percentage') not in [0, 1]:
            return {'error': "Please Provide A Valid Spot Discount Type"}
        return {'cart': cart}

    def serialize(self, cart, offers=None):
        """
            Checkout serializer
            Payment Info plus Offers
        """
        serializer = CheckoutSerializer(Cart.objects.prefetch_related('rt_cart_list').get(pk=cart.id))
        response = serializer.data
        if offers:
            response['available_offers'] = offers['total_offers']
            if offers['spot_discount']:
                response['spot_discount'] = offers['spot_discount']
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
                coupon_codes_list = []
                array = list(filter(lambda d: d['sub_type'] in 'discount_on_product', cart.offers))

                cart_products = CartProductMapping.objects.select_related(
                    'cart_product'
                ).filter(
                    cart=cart
                )

                # Check and remove if any product blocked for audit
                for p in cart_products:
                    is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
                                                                                            parent_mapping.parent)
                    if is_blocked_for_audit:
                        p.delete()

                # Check if products available in cart
                if cart_products.count() <= 0:
                    msg = {'is_success': False,
                           'message': ['No product is available in cart'],
                           'response_data': None,
                           'is_shop_time_entered': False}
                    return Response(msg, status=status.HTTP_200_OK)
                # Check if any product blocked for audit
                # for p in cart_products:
                #     is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
                #                                                                             parent_mapping.parent)
                #     if is_blocked_for_audit:
                #         msg['message'] = [ERROR_MESSAGES['4019'].format(p)]
                #         return Response(msg, status=status.HTTP_200_OK)

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
                    if len(array) is 0:
                        pass
                    else:
                        for i in array:
                            if cart_product.cart_product.id == i['item_id']:
                                customer_coupon_usage = CusotmerCouponUsage(coupon_id=i['coupon_id'], cart=cart)
                                customer_coupon_usage.shop = parent_mapping.retailer
                                customer_coupon_usage.product = cart_product.cart_product
                                customer_coupon_usage.times_used += coupon_usage_count + 1
                                customer_coupon_usage.save()

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

    # def sp_mapping_order_reserve(self):
    #     pass
    # def gf_mapping_order_reserve(self):
    #     pass


class OrderCentral(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
            Get Order Details
            Inputs
            cart_type
            order_id
        """
        cart_type = request.GET.get('cart_type', '1')
        if cart_type == '1':
            return self.get_retail_order()
        elif cart_type == '2':
            return self.get_basic_order(request, *args, **kwargs)
        else:
            return api_response('Provide a valid cart_type')

    def put(self, request, *args, **kwargs):
        """
            allowed updates to order status
        """
        cart_type = request.data.get('cart_type', '1')
        if cart_type == '1':
            return self.put_retail_order(kwargs['pk'])
        elif cart_type == '2':
            return self.put_basic_order(request, *args, **kwargs)
        else:
            return api_response('Provide a valid cart_type')

    @check_pos_shop
    def put_basic_order(self, request, *args, **kwargs):
        """
            Cancel POS order
        """
        with transaction.atomic():
            # Check if order exists
            try:
                order = Order.objects.get(pk=kwargs['pk'], seller_shop=kwargs['shop'], order_status='ordered')
            except ObjectDoesNotExist:
                return api_response('Order Not Found To Cancel!')
            # check input status validity
            allowed_updates = [Order.CANCELLED]
            order_status = self.request.data.get('status')
            if order_status not in allowed_updates:
                return api_response("Please Provide A Valid Status To Update Order")
            # cancel order
            order.order_status = order_status
            order.last_modified_by = self.request.user
            order.save()
            # cancel shipment
            ordered_product = OrderedProduct.objects.filter(order=order).last()
            ordered_product.shipment_status = 'CANCELLED'
            ordered_product.last_modified_by = self.request.user
            ordered_product.save()
            # Update inventory
            ordered_products = ShipmentProducts.objects.filter(ordered_product=ordered_product)
            for op in ordered_products:
                PosInventoryCls.order_inventory(op.retailer_product.id, PosInventoryState.ORDERED,
                                                PosInventoryState.AVAILABLE, op.shipped_qty, self.request.user,
                                                order.order_no, PosInventoryChange.CANCELLED)
            order_number = order.order_no
            shop_name = order.seller_shop.shop_name
            phone_number = order.buyer.phone_number
            # whatsapp api call for order cancellation
            whatsapp_order_cancel.delay(order_number, shop_name, phone_number)
            return api_response("Order cancelled successfully!", None, status.HTTP_200_OK, True)

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
            cart_type (retail-1 or basic-2)
                retail
                    shop_id (Buyer shop id)
                    billing_address_id
                    shipping_address_id
                    total_tax_amount
                basic
                    shop_id (Seller shop id)
        """
        cart_type = self.request.data.get('cart_type', '1')
        if cart_type == '1':
            return self.post_retail_order()
        elif cart_type == '2':
            return self.post_basic_order(request, *args, **kwargs)
        else:
            return api_response('Provide a valid cart_type')

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
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None, status.HTTP_200_OK)

    @check_pos_shop
    def get_basic_order(self, request, *args, **kwargs):
        """
            Get Order
            For Basic Cart
        """
        try:
            order = Order.objects.get(pk=self.request.GET.get('order_id'), seller_shop=kwargs['shop'])
        except ObjectDoesNotExist:
            return api_response("Order Not Found!")
        return api_response('Order', self.get_serialize_process_basic(order), status.HTTP_200_OK, True)

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
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None, status.HTTP_200_OK)

    @check_pos_shop
    def post_basic_order(self, request, *args, **kwargs):
        """
            Place Order
            For basic cart
        """
        shop = kwargs['shop']
        # basic validations for inputs
        initial_validation = self.post_basic_validate(shop)
        if 'error' in initial_validation:
            e_code = initial_validation['error_code'] if 'error_code' in initial_validation else None
            extra_params = {'error_code': e_code} if e_code else {}
            return api_response(initial_validation['error'], None, status.HTTP_406_NOT_ACCEPTABLE, False, extra_params)
        cart = initial_validation['cart']
        payment_method = initial_validation['payment_method']

        with transaction.atomic():
            # Update Cart To Ordered
            self.update_cart_basic(cart)
            # Refresh redeem reward
            RewardCls.checkout_redeem_points(cart, cart.redeem_points)
            order = self.create_basic_order(cart, shop)
            self.auto_process_order(order, payment_method)
            return api_response('Ordered Successfully!', BasicOrderListSerializer(Order.objects.get(id=order.id)).data,
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
        cart = Cart.objects.filter(id=cart_id, seller_shop=shop).last()
        if not cart:
            return {'error': "Cart Doesn't Exist!"}
        elif cart.cart_status == Cart.ORDERED:
            return {'error': "Order already placed on this cart!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status == Cart.DELETED:
            return {'error': "This cart was deleted!", 'error_code': error_code.CART_NOT_ACTIVE}
        elif cart.cart_status not in [Cart.ACTIVE, Cart.PENDING]:
            return {'error': "Active Cart Doesn't Exist!"}
        # Check if products available in cart
        cart_products = CartProductMapping.objects.select_related('retailer_product').filter(cart=cart, product_type=1)
        if cart_products.count() <= 0:
            return {'error': 'No product is available in cart'}
        # Check payment method
        payment_method = self.request.data.get('payment_method')
        if not payment_method or payment_method not in dict(PAYMENT_MODE_POS):
            return {'error': 'Please provide a valid payment method'}
        # check customer phone_number
        phone_no = self.request.data.get('phone_number')
        if not phone_no:
            return {'error': "Please provide customer phone number"}
        if not re.match(r'^[6-9]\d{9}$', phone_no):
            return {'error': "Please provide a valid customer phone number"}
        email = self.request.data.get('email')
        if email:
            try:
                validators.validate_email(email)
            except:
                return {'error': "Please provide a valid customer email"}
        return {'cart': cart, 'payment_method': payment_method}

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
            return {'is_success': False, 'message': "Some products in cart aren’t available anymore, please update cart"
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
        # Check Customer - Update Or Create
        customer = update_pos_customer(self.request.data.get('phone_number'), cart.seller_shop.id,
                                       self.request.data.get('email'), self.request.data.get('name'),
                                       self.request.data.get('is_whatsapp'))
        # Update customer as buyer in cart
        cart.buyer = customer
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

    def create_basic_order(self, cart, shop):
        user = self.request.user
        order, _ = Order.objects.get_or_create(last_modified_by=user, ordered_by=user, ordered_cart=cart)
        order.buyer = cart.buyer
        order.seller_shop = shop
        order.received_by = cart.buyer
        # order.total_tax_amount = float(self.request.data.get('total_tax_amount', 0))
        order.order_status = Order.ORDERED
        order.save()
        return order

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
        serializer = BasicOrderSerializer(order, context={'current_url': self.request.get_host(),
                                                          'invoice': 1})
        return serializer.data

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

    def auto_process_order(self, order, payment_method):
        """
            Auto process add payment, shipment, invoice for retailer and customer
        """
        # Redeem loyalty points
        redeem_factor = order.ordered_cart.redeem_factor
        redeem_points = order.ordered_cart.redeem_points
        if redeem_points:
            RewardCls.redeem_points_on_order(redeem_points, redeem_factor, order.buyer, self.request.user, order.order_no)
        # Add free products
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
        # Create payment
        PosPayment.objects.create(
            order=order,
            payment_mode=payment_method,
            paid_by=order.buyer,
            processed_by=self.request.user
        )
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
        # Invoice Number Generate
        shipment.shipment_status = OrderedProduct.READY_TO_SHIP
        shipment.save()
        # Complete Shipment
        shipment.shipment_status = 'FULLY_DELIVERED_AND_VERIFIED'
        shipment.save()
        pdf_generation_retailer(self.request, order.id)
        order_loyalty_points.delay(order.order_amount, order.buyer.id, order.order_no, 'order_credit',
                                   'order_direct_credit', 'order_indirect_credit', self.request.user.id)


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
#                                 "Some products in cart arenâ€™t available anymore, please update cart and remove product from cart upon revisiting it"]
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
            cart_type
            shop_id
        """
        cart_type = request.GET.get('cart_type', '1')
        if cart_type == '1':
            return self.get_retail_order_list()
        elif cart_type == '2':
            return self.get_basic_order_list(request, *args, **kwargs)
        else:
            return api_response('Provide a valid cart_type')

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
            return api_response(['Sorry shop is not associated with any GramFactory or any SP'], None, status.HTTP_200_OK)

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
            For Basic Cart
        """
        # Search, Paginate, Return Orders
        search_text = self.request.GET.get('search_text')
        order_status = self.request.GET.get('order_status')
        qs = Order.objects.select_related('buyer').filter(seller_shop=kwargs['shop'])
        if order_status:
            order_status_actual = ORDER_STATUS_MAP.get(int(order_status), None)
            qs = qs.filter(order_status=order_status_actual) if order_status_actual else qs
        if search_text:
            qs = qs.filter(Q(order_no__icontains=search_text) |
                           Q(buyer__first_name__icontains=search_text) |
                           Q(buyer__phone_number__icontains=search_text))
        return api_response('Order', self.get_serialize_process_basic(qs), status.HTTP_200_OK, True)

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
        cart_type = request.GET.get('app_type')
        if cart_type == '1':
            return self.get_retail_order_overview()
        elif cart_type == '2':
            return self.get_basic_order_overview(request, *args, **kwargs)
        else:
            return api_response('Provide a valid app_type')

    @check_pos_shop
    def get_basic_order_overview(self, request, *args, **kwargs):
        """
            Get Shop Name, Order, Product, & User Counts
            For Basic Cart
        """
        order = self.get_basic_orders_count(kwargs['shop'])
        return api_response('Dashboard', self.get_serialize_process(order), status.HTTP_200_OK, True)

    def get_basic_orders_count(self, shop):
        """
          Get Basic Order Overview based on filters
        """
        # orders for shop
        orders = Order.objects.prefetch_related('rt_return_order').filter(seller_shop=shop).exclude(
            order_status=Order.CANCELLED)
        # products for shop
        products = RetailerProduct.objects.filter(shop=shop)

        # order status filter
        order_status = self.request.GET.get('order_status')
        if order_status:
            order_status_actual = ORDER_STATUS_MAP.get(int(order_status), None)
            orders = orders.filter(order_status=order_status_actual) if order_status_actual else orders

        # filter for date range
        filters = int(self.request.GET.get('filters')) if self.request.GET.get('filters') else None
        today_date = datetime.today()
        if filters == 1:  # today
            orders = orders.filter(created_at__date=today_date)
            products = products.filter(created_at__date=today_date)
        elif filters == 2:  # yesterday
            yesterday = today_date - timedelta(days=1)
            orders = orders.filter(created_at__date=yesterday)
            products = products.filter(created_at__date=yesterday)
        elif filters == 3:  # this week
            orders = orders.filter(created_at__week=today_date.isocalendar()[1])
            products = products.filter(created_at__week=today_date.isocalendar()[1])
        elif filters == 4:  # last week
            last_week = today_date - timedelta(weeks=1)
            orders = orders.filter(created_at__week=last_week.isocalendar()[1])
            products = products.filter(created_at__week=last_week.isocalendar()[1])
        elif filters == 5:  # this month
            orders = orders.filter(created_at__month=today_date.month)
            products = products.filter(created_at__month=today_date.month)
        elif filters == 6:  # last month
            last_month = today_date - timedelta(days=30)
            orders = orders.filter(created_at__month=last_month.month)
            products = products.filter(created_at__month=last_month.month)
        elif filters == 7:  # this year
            orders = orders.filter(created_at__year=today_date.year)
            products = products.filter(created_at__year=today_date.year)

        total_final_amount = 0
        for order in orders:
            order_amt = order.order_amount
            returns = order.rt_return_order.all()
            if returns:
                for ret in returns:
                    if ret.status == 'completed':
                        order_amt -= ret.refund_amount if ret.refund_amount > 0 else 0
            total_final_amount += order_amt

        # counts of order for shop_id with total_final_amount & products
        order_count = orders.count()
        products_count = products.count()
        overview = [{"shop_name": shop.shop_name, "orders": order_count, "products": products_count,
                     "revenue": total_final_amount}]
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
        return api_response('Dashboard', self.get_serialize_process(order), status.HTTP_200_OK, True)

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
           Cart type basic & Retail
        """
        serializer = OrderedDashBoardSerializer(order, many=True).data
        return serializer


class OrderReturns(APIView):
    """
        Place return for an order
    """

    @check_pos_shop
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
                changed_sp = return_product['changed_sp']
                price_change = return_product['price_change']
                # if return quantity of product is greater than zero
                if return_qty > 0 or price_change:
                    changed_products += [product_id]
                    self.return_item(order_return, ordered_product_map, return_qty, changed_sp)
                    if product_id in product_combo_map and return_qty > 0:
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
                    new_cart_value += (ordered_product_map.shipped_qty - return_qty - previous_ret_qty) * changed_sp
                # elif price_change:
                #     self.return_item(order_return, ordered_product_map, 0, changed_sp)
                #     new_cart_value += ordered_product_map.shipped_qty * changed_sp
                else:
                    ReturnItems.objects.filter(return_id=order_return, ordered_product=ordered_product_map).delete()
                    if product_id in product_combo_map:
                        for offer in product_combo_map[product_id]:
                            free_returns = self.get_updated_free_returns(free_returns, offer['free_item_id'], 0)
                    new_cart_value += (ordered_product_map.shipped_qty - previous_ret_qty) * changed_sp
            # check and update refund amount
            self.update_refund_amount(order, new_cart_value, order_return)
            # check if free product offered on order value is still valid
            free_returns, free_qty_product_map = self.check_cart_free_product(cart_free_product, free_returns,
                                                                              new_cart_value, free_qty_product_map)
            self.process_free_products(ordered_product, order_return, free_returns)
            order_return.free_qty_map = free_qty_product_map
            order_return.save()
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
            order = Order.objects.prefetch_related('rt_return_order').get(pk=order_id, seller_shop=shop,
                                                                          order_status__in=['ordered',
                                                                                            Order.PARTIALLY_RETURNED])
        except ObjectDoesNotExist:
            return {'error': "Order Not Valid For Return"}
        # check return reason is valid
        return_reason = self.request.data.get('return_reason', '')
        if return_reason and return_reason not in dict(OrderReturn.RETURN_REASON):
            return {'error': 'Provide a valid return reason'}
        # Check return item details
        ordered_product = OrderedProduct.objects.get(order=order)
        all_products = ordered_product.rt_order_product_order_product_mapping.filter(product_type=1)
        given_products = []
        for item in return_items:
            given_products += [item['product_id']]
        for prod in all_products:
            if prod.retailer_product_id not in given_products:
                return_items.append({
                    "product_id": int(prod.retailer_product_id),
                    "qty": 0,
                    "new_sp": float(prod.selling_price)
                })
                # return {'error': 'Please provide details for all purchased products'}
        modified = 0
        return_details = []
        for return_product in return_items:
            product_validate = self.validate_product(ordered_product, return_product, order.order_status)
            if 'error' in product_validate:
                return product_validate
            else:
                if product_validate['return_qty'] > 0 or product_validate['price_change']:
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
        prev_refund_amount = 0
        prev_refund_points = 0
        if order.order_status == Order.PARTIALLY_RETURNED:
            previous_returns = order.rt_return_order.filter(status='completed')
            for ret in previous_returns:
                prev_refund_amount += ret.refund_amount if ret.refund_amount > 0 else 0
                prev_refund_points += ret.refund_points
        prev_refund_points_value = round(prev_refund_points / redeem_factor, 2) if prev_refund_points else 0
        prev_refund_total = prev_refund_points_value + prev_refund_amount

        # Order values
        cart_redeem_points = order.ordered_cart.redeem_points
        redeem_value = round(cart_redeem_points / redeem_factor, 2) if cart_redeem_points else 0
        order_amount = float(order.order_amount)
        order_total = order_amount + redeem_value

        # Current total refund value
        total_refund_value = round(order_total - prev_refund_total - float(new_cart_value), 2)

        if total_refund_value < 0:
            refund_amount = total_refund_value
            refund_points = 0
        # Refund cash first, then points
        else:
            refund_amount = min(order_amount - prev_refund_total, total_refund_value)
            refund_amount = max(refund_amount, 0)
            refund_points_value = total_refund_value - refund_amount
            refund_points = int(refund_points_value * redeem_factor)

        order_return.refund_amount = refund_amount
        order_return.refund_points = refund_points
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

    def return_item(self, order_return, ordered_product_map, return_qty, changed_sp=0):
        """
            Update return for a product
        """
        return_item, _ = ReturnItems.objects.get_or_create(return_id=order_return,
                                                           ordered_product=ordered_product_map)
        return_item.new_sp = changed_sp
        return_item.return_qty = return_qty
        return_item.save()

    def update_return(self, order, return_reason):
        """
            Create/update retun for an order
        """
        order_return, _ = OrderReturn.objects.get_or_create(order=order, status='created')
        order_return.processed_by = self.request.user
        order_return.return_reason = return_reason
        order_return.save()
        return order_return

    def validate_product(self, ordered_product, return_product, order_status):
        """
            Validate return detail - product_id, qty, amt (refund amount) - provided for a product
        """
        # product id
        if 'product_id' not in return_product or 'qty' not in return_product or 'new_sp' not in return_product:
            return {'error': "Provide product product_id, qty, new_sp for each product"}
        product_id = return_product['product_id']
        qty = return_product['qty']
        new_sp = float(return_product['new_sp'])
        if qty < 0 or new_sp < 0:
            return {'error': "Provide valid qty and new_sp for product {}".format(product_id)}
        # ordered product
        try:
            ordered_product_map = ShipmentProducts.objects.get(ordered_product=ordered_product, product_type=1,
                                                               retailer_product_id=product_id)
        except:
            return {'error': "{} is not a purchased product in this order".format(product_id)}
        # Last selling price, previous returns account
        order_sp = float(ordered_product_map.selling_price)
        previous_ret_qty = 0
        if order_status == Order.PARTIALLY_RETURNED:
            previous_returns = ReturnItems.objects.filter(return_id__status='completed',
                                                          ordered_product=ordered_product_map)
            if previous_returns.exists():
                previous_ret_qty = previous_returns.aggregate(qty=Sum('return_qty'))['qty']
                order_sp = previous_returns.last().new_sp
        # New total return quantity should be greater than equal to sum of previous return qty
        # if qty < previous_ret_qty:
        #     return {'error': "{} quantity of product {} have already been returned.".format(previous_ret_qty,
        #                                                                                     product_id)}
        price_change = 0
        changed_sp = new_sp
        if new_sp > order_sp:
            return {'error': "New selling price cannot be greater than ordered product's last selling price for product"
                             " {}".format(product_id)}
        elif new_sp < order_sp:
            if (qty + previous_ret_qty) == ordered_product_map.shipped_qty:
                return {
                    'error': "Total Returned Quantity Equals Purchase Quantity. No item left to change selling price for"
                             " product {}".format(product_id)}
            # if qty != 0:
            #     return {'error': "Either of return qty or new selling price can be changed. Error in return details "
            #                      "for product {}".format(product_id)}
            price_change = 1
        # check return qty
        if qty + previous_ret_qty > ordered_product_map.shipped_qty:
            return {'error': "Product {} - total return qty cannot be greater than sold quantity".format(product_id)}
        # qty = qty - previous_ret_qty
        return {'ordered_product_map': ordered_product_map, 'return_qty': qty, 'product_id': product_id,
                'changed_sp': changed_sp, 'price_change': price_change, 'previous_ret_qty': previous_ret_qty}

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
            free_return.new_sp = ordered_product_map_free.selling_price
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
            order = Order.objects.prefetch_related('rt_return_order').get(pk=order_id, seller_shop=shop,
                                                                          order_status__in=['ordered',
                                                                                            Order.PARTIALLY_RETURNED])
        except ObjectDoesNotExist:
            return {'error': "Order Does Not Exist / Still Open / Already Returned"}
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


class OrderReturnComplete(APIView):
    """
        Complete created return on an order
    """

    @check_pos_shop
    def post(self, request, *args, **kwargs):
        """
            Complete return on order
        """
        # check order
        order_id = self.request.data.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, seller_shop=kwargs['shop'],
                                      order_status__in=['ordered', Order.PARTIALLY_RETURNED])
        except ObjectDoesNotExist:
            return api_response("Order Does Not Exist / Still Open / Already Returned")
        # check if return created
        try:
            order_return = OrderReturn.objects.get(order=order, status='created')
        except ObjectDoesNotExist:
            return api_response("Order Return Does Not Exist / Already Closed")
        # Check refund method
        refund_method = self.request.data.get('refund_method')
        if not refund_method or refund_method not in dict(PAYMENT_MODE_POS):
            return api_response('Please provide a valid refund method')

        with transaction.atomic():
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
            RewardCls.adjust_points_on_return(order_return, self.request.user)
            # Update inventory
            returned_products = ReturnItems.objects.filter(return_id=order_return)
            for rp in returned_products:
                PosInventoryCls.order_inventory(rp.ordered_product.retailer_product.id, PosInventoryState.ORDERED,
                                                PosInventoryState.AVAILABLE, rp.return_qty, self.request.user, rp.id,
                                                PosInventoryChange.RETURN)
            # complete return
            order_return.status = 'completed'
            order_return.refund_mode = refund_method
            order_return.save()
            # whatsapp api call for refund notification
            order_number = order.order_no
            order_status = order.order_status
            phone_number = order.buyer.phone_number
            refund_amount = order_return.refund_amount if order_return.refund_amount > 0 else 0
            whatsapp_order_refund.delay(order_number, order_status, phone_number, refund_amount)
            return api_response("Return Completed Successfully!", OrderReturnCheckoutSerializer(order).data,
                                status.HTTP_200_OK, True)


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
    filename = create_file_name(file_prefix, ordered_product)
    # we will be changing based on shop name
    template_name = 'admin/invoice/invoice_sp.html'
    if type(request) is str:
        request = None
        ordered_product = get_object_or_404(OrderedProduct, pk=ordered_product)
    else:
        request = request
        ordered_product = ordered_product

    try:
        if ordered_product.invoice.invoice_pdf.url:
            pass
    except Exception as e:
        logger.exception(e)
        barcode = barcodeGen(ordered_product.invoice_no)

        buyer_shop_id = ordered_product.order.buyer_shop_id
        paid_amount = 0
        invoice_details = OrderedProduct.objects.filter(order__buyer_shop_id=buyer_shop_id)
        for invoice_amount in invoice_details:
            date_time = invoice_amount.created_at
            date = date_time.strftime("%d")
            month = date_time.strftime("%m")
            year = date_time.strftime("%Y")
            # print(str(date) + " " + str(month) + " " + str(year) + " " + str(invoice_amount.invoice_amount) + " " + str(invoice_amount.shipment_status))
            if int(month) > 2 and int(year) > 2019:
                if invoice_amount.invoice_amount is None:
                    paid_amount += 0
                else:
                    paid_amount += invoice_amount.invoice_amount
        # print(paid_amount)

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
                shop_document_type='gstin').exists() else 'unregistered'

        if ordered_product.order.ordered_cart.buyer_shop.shop_name_documents.exists():
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
        tcs_rate = 0
        tcs_tax = 0
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
                "product_short_description": m.product.product_short_description,
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

        total_amount = ordered_product.invoice_amount

        total_tax_amount = ordered_product.sum_amount_tax()

        if float(paid_amount) > 5000000:
            if buyer_shop_gistin == 'unregistered':
                tcs_rate = 1
                tcs_tax = total_amount * float(tcs_rate / 100)
            else:
                tcs_rate = 0.1
                tcs_tax = total_amount * float(tcs_rate / 100)

        tcs_tax = round(tcs_tax, 2)
        product_special_cess = round(m.total_product_cess_amount)
        amount = total_amount
        total_amount = total_amount + tcs_tax
        total_amount_int = round(total_amount)
        total_tax_amount_int = round(total_tax_amount)

        amt = [num2words(i) for i in str(total_amount_int).split('.')]
        rupees = amt[0]

        tax_amt = [num2words(i) for i in str(total_tax_amount_int).split('.')]
        tax_rupees = tax_amt[0]

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
                "pincode_gram": pincode_gram, "cin": cin, "hsn_list": list1}

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


def pdf_generation_retailer(request, order_id):
    """
    :param request: request object
    :param order_id: Order id
    :return: pdf instance
    """
    file_prefix = PREFIX_INVOICE_FILE_NAME
    order = Order.objects.filter(id=order_id).last()
    ordered_product = order.rt_order_order_product.all()[0]
    filename = create_file_name(file_prefix, ordered_product)
    template_name = 'admin/invoice/invoice_retailer.html'

    try:
        # Don't create pdf if already created
        if ordered_product.invoice.invoice_pdf.url:
            pass
    except Exception as e:
        logger.exception(e)
        barcode = barcodeGen(ordered_product.invoice_no)
        # Products
        product_listing = []
        # Total invoice qty
        sum_qty = 0
        # Total Ordered Amount
        total = 0
        for m in ordered_product.rt_order_product_order_product_mapping.filter(shipped_qty__gt=0):
            sum_qty += m.shipped_qty
            cart_product_map = ordered_product.order.ordered_cart.rt_cart_list.filter(
                retailer_product=m.retailer_product,
                product_type=m.product_type
            ).last()
            product_pro_price_ptr = cart_product_map.selling_price
            ordered_p = {
                "id": cart_product_map.id,
                "product_short_description": m.retailer_product.product_short_description,
                "mrp": m.retailer_product.mrp,
                "qty": m.shipped_qty,
                "rate": float(product_pro_price_ptr),
                "product_sub_total": float(m.shipped_qty) * float(product_pro_price_ptr)
            }
            total += ordered_p['product_sub_total']
            product_listing.append(ordered_p)
        product_listing = sorted(product_listing, key=itemgetter('id'))
        # Total payable amount
        total_amount = ordered_product.order.order_amount
        total_amount_int = round(total_amount)
        # Total discount
        discount = total - total_amount
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

        data = {"shipment": ordered_product, "order": ordered_product.order, "url": request.get_host(),
                "scheme": request.is_secure() and "https" or "http", "total_amount": total_amount, 'total': total,
                'discount': discount, "barcode": barcode, "product_listing": product_listing, "rupees": rupees,
                "sum_qty": sum_qty, "nick_name": nick_name, "address_line1": address_line1, "city": city,
                "state": state,
                "pincode": pincode, "address_contact_number": address_contact_number}

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        try:
            # create_invoice_data(ordered_product)
            ordered_product.invoice.invoice_pdf.save("{}".format(filename), ContentFile(response.rendered_content),
                                                     save=True)
            phone_number = order.buyer.phone_number
            shop_name = order.seller_shop.shop_name
            media_url = ordered_product.invoice.invoice_pdf.url
            file_name = ordered_product.invoice.invoice_no
            # whatsapp api call for sending an invoice
            whatsapp_opt_in.delay(phone_number, shop_name, media_url, file_name)
        except Exception as e:
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
        for gs in credit_note.shipment.order.seller_shop.shop_name_documents.all():
            gstinn3 = gs.shop_document_number if gs.shop_document_type == 'gstin' else 'Unregistered'
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
        tcs_rate = 0
        tcs_tax = 0
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
            delivered_qty = m.delivered_qty
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
            "gstinn3": gstinn3, "rupees": rupees, "credit_note_type": credit_note_type, "pan_no": pan_no, "cin": cin,
            "hsn_list": list1}
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
        data = {"object": order_obj, "order": order_obj.order, "products": products}

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
        shipment_details = ShipmentSerializer(shipments, many=True)
        msg = {'is_success': True, 'message': ['Shipment Details'], 'response_data': shipment_details.data}
        return Response(msg, status=status.HTTP_201_CREATED)


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
                    ShipmentProducts.objects.filter(ordered_product__id=shipment_id, product=product).update(
                        returned_qty=returned_qty, returned_damage_qty=damaged_qty, delivered_qty=delivered_qty,
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
        queryset = Order.objects.filter(buyer_shop__id__in=shop_list).order_by(
            '-created_at') if self.is_manager else Order.objects.filter(buyer_shop__id__in=shop_list,
                                                                        ordered_by=request.user).order_by('-created_at')
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
            msg = {'is_success': False, 'message': ['A shipment cannot be rescheduled more than once.'], 'response_data': None}
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
            msg = {'is_success': True, 'message': ['Reschedule successfully done.'], 'response_data': [serializer.data]}
        else:
            msg = {'is_success': False, 'message': ['have some issue'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        shipment = OrderedProduct.objects.get(pk=self.request.data.get('shipment'))
        return serializer.save(created_by=self.request.user, trip=shipment.trip)

    def update_shipment(self, id):
        shipment = OrderedProduct.objects.get(pk=id)
        shipment.shipment_status = OrderedProduct.RESCHEDULED
        shipment.trip = None
        shipment.save()
        shipment_reschedule_inventory_change([shipment])


def update_trip_status(trip_id):
    shipment_status_list = ['FULLY_DELIVERED_AND_COMPLETED', 'PARTIALLY_DELIVERED_AND_COMPLETED',
                            'FULLY_RETURNED_AND_COMPLETED', 'RESCHEDULED']
    order_product = OrderedProduct.objects.filter(trip_id=trip_id)
    if order_product.exclude(shipment_status__in=shipment_status_list).count() == 0:
        Trip.objects.filter(pk=trip_id).update(trip_status=Trip.COMPLETED, completed_at=datetime.now())
        # updating order status when trip is completed
        trip_instance = Trip.objects.get(id=trip_id)
        trip_shipments = trip_instance.rt_invoice_trip.values_list('id', flat=True)
        Order.objects.filter(rt_order_order_product__in=trip_shipments).update(order_status=Order.COMPLETED)


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


class RefreshEsRetailer(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
            Refresh retailer Products Es
        """
        shop_id = self.request.GET.get('shop_id')
        try:
            shop = Shop.objects.get(id=shop_id, shop_type__shop_type='f')
        except ObjectDoesNotExist:
            return api_response("Shop Not Found")
        from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix
        index = "{}-{}".format(es_prefix, 'rp-{}'.format(shop_id))
        es.indices.delete(index=index, ignore=[400, 404])
        info_logger.info('RefreshEsRetailer | shop {}, Started'.format(shop_id))
        all_products = RetailerProduct.objects.filter(shop=shop)
        try:
            update_es(all_products, shop_id)
        except Exception as e:
            info_logger.info("error in retailer shop index creation")
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
        shops_qs = filter_pos_shop(user)
        if search_text:
            shops_qs = shops_qs.filter(shop_name__icontains=search_text)
        shops = shops_qs.distinct('id')
        request_shops = self.pagination_class().paginate_queryset(shops, self.request)
        data = PosShopSerializer(request_shops, many=True).data
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
        data['shop_owner'] = PosUserSerializer(shop.shop_owner).data
        related_users = shop.related_users.filter(is_staff=False)
        request_users = self.pagination_class().paginate_queryset(related_users, self.request)
        data['related_users'] = PosUserSerializer(request_users, many=True).data
        return api_response("Shop Users", data, status.HTTP_200_OK, True)
