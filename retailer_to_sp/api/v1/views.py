import decimal
import logging
from decimal import Decimal
import json
import jsonpickle
from num2words import num2words
from datetime import datetime, timedelta

from audit.views import BlockUnblockProduct
from barCodeGenerator import barcodeGen
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Sum, Q
from wkhtmltopdf.views import PDFTemplateResponse
from django.shortcuts import get_object_or_404, get_list_or_404


from django_filters import rest_framework as filters
from rest_framework import permissions, authentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
import requests
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import serializers
from rest_framework import generics, viewsets
from retailer_backend.utils import SmallOffsetPagination
from num2words import num2words
import collections
from django.core.files.base import ContentFile
from django.shortcuts import redirect
from django.db import transaction

from wms.views import shipment_reschedule_inventory_change
from .serializers import (ProductsSearchSerializer, GramGRNProductsSearchSerializer,
                          CartProductMappingSerializer, CartSerializer, OrderSerializer,
                          CustomerCareSerializer, OrderNumberSerializer, PaymentCodSerializer,
                          PaymentNeftSerializer, GramPaymentCodSerializer, GramPaymentNeftSerializer,
                          GramMappedCartSerializer, GramMappedOrderSerializer, ProductDetailSerializer,
                          OrderDetailSerializer, OrderedProductSerializer, OrderedProductMappingSerializer,
                          RetailerShopSerializer, SellerOrderListSerializer, OrderListSerializer,
                          ReadOrderedProductSerializer, FeedBackSerializer, CancelOrderSerializer,
                          ShipmentDetailSerializer, TripSerializer, ShipmentSerializer, PickerDashboardSerializer,
                          ShipmentReschedulingSerializer, ShipmentReturnSerializer, ParentProductImageSerializer
                          )

from products.models import Product, ProductPrice, ProductOption, ProductImage, ProductTaxMapping
from sp_to_gram.models import (OrderedProductMapping, OrderedProductReserved,
                               OrderedProductMapping as SpMappedOrderedProductMapping,
                               OrderedProduct as SPOrderedProduct, StockAdjustment, create_credit_note)

from categories import models as categorymodel

from payments.models import Payment as PaymentDetail

from gram_to_brand.models import (GRNOrderProductMapping, CartProductMapping as GramCartProductMapping,
                                  OrderedProductReserved as GramOrderedProductReserved, PickList, PickListItems
                                  )
from retailer_to_sp.models import (Cart, CartProductMapping, Order,
                                   OrderedProduct, Payment, CustomerCare, Return, Feedback,
                                   OrderedProductMapping as ShipmentProducts, Trip, PickerDashboard,
                                   ShipmentRescheduling, Note, OrderedProductBatch
                                   )
from retailer_to_sp.common_function import check_date_range, capping_check
from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping,
                                     Order as GramMappedOrder, OrderedProduct as GramOrderedProduct,
                                     Payment as GramMappedPayment,
                                     CustomerCare as GramMappedCustomerCare
                                     )

from shops.models import Shop, ParentRetailerMapping, ShopMigrationMapp
from shops.models import Shop, ParentRetailerMapping, ShopUserMapping
from brand.models import Brand
from products.models import ProductCategory
from addresses.models import Address
from retailer_backend.common_function import getShopMapping, checkNotShopAndMapping, getShop
from retailer_backend.messages import ERROR_MESSAGES

from retailer_to_sp.tasks import (
    ordered_product_available_qty_update, release_blocking
)
from wms.common_functions import OrderManagement, get_stock, is_product_not_eligible
from .filters import OrderedProductMappingFilter, OrderedProductFilter
from retailer_to_sp.filters import PickerDashboardFilter
from common.data_wrapper_view import DataWrapperViewSet

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from common.data_wrapper import format_serializer_errors
from sp_to_gram.tasks import es_search, upload_shop_stock
from coupon.serializers import CouponSerializer
from coupon.models import Coupon, CusotmerCouponUsage

from products.models import Product
from common.constants import ZERO, PREFIX_INVOICE_FILE_NAME, INVOICE_DOWNLOAD_ZIP_NAME
from common.common_utils import (create_file_name, single_pdf_file, create_merge_pdf_name, merge_pdf_files,
                                 create_invoice_data)
from retailer_to_sp.views import pick_list_download
from celery.task import task
from wms.models import WarehouseInternalInventoryChange, OrderReserveRelease, InventoryType
from retailer_backend.settings import AWS_MEDIA_URL
from global_config.models import GlobalConfig

User = get_user_model()

logger = logging.getLogger('django')

today = datetime.today()
info_logger = logging.getLogger('file-info')


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
        msg = {'is_success': True, 'message': [''], 'response_data':{'results':[serializer.data]}}
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


class GramGRNProductsList(APIView):
    permission_classes = (AllowAny,)
    serializer_class = GramGRNProductsSearchSerializer

    def search_query(self, request):
        filter_list = [
            {"term": {"status": True}},
            {"term": {"visible": True}},
            {"range": {"available": {"gt": 0}}}
        ]
        if self.product_ids:
            filter_list.append({"ids": {"type": "product", "values": self.product_ids}})
            query = {"bool": {"filter": filter_list}}
            return query
        query = {"bool": {"filter": filter_list}}
        if not (self.category or self.brand or self.keyword):
            return query
        if self.brand:
            brand_name = "{} -> {}".format(Brand.objects.filter(id__in=list(self.brand)).last(), self.keyword)
            filter_list.append({"match": {
                "brand": {"query": brand_name, "fuzziness": "AUTO", "operator": "and"}
            }})

        elif self.keyword:
            q = {
                    "multi_match": {
                        "query":     self.keyword,
                        "fields":    ["name^5", "category", "brand"],
                        "type":      "cross_fields"
                    }
                }
            query["bool"]["must"] = [q]
        if self.category:
            category_filter = str(categorymodel.Category.objects.filter(id__in=self.category, status=True).last())
            filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})

        return query

    def post(self, request, format=None):
        self.product_ids = request.data.get('product_ids')
        self.brand = request.data.get('brands')
        self.category = request.data.get('categories')
        self.keyword = request.data.get('product_name', None)
        shop_id = request.data.get('shop_id')
        offset = int(request.data.get('offset', 0))
        page_size = int(request.data.get('pro_count', 50))
        grn_dict = None
        cart_check = False
        is_store_active = True
        sort_preference = request.GET.get('sort_by_price')

        '''1st Step
            Check If Shop Is exists then 2nd pt else 3rd Pt
        '''
        query = self.search_query(request)

        try:
            shop = Shop.objects.get(id=shop_id, status=True)
        except ObjectDoesNotExist:
            '''3rd Step
                If no shop found then
            '''
            message = "Shop not active or does not exists"
            is_store_active = False
        else:
            '''2nd Step
                Check if shop found then check whether it is sp 4th Step or retailer 5th Step
            '''
            if not shop.shop_approved:
                message = "Shop Mapping Not Found"
                is_store_active = False
            # try:
            #     parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
            # except ObjectDoesNotExist:
            else:
                parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
                if parent_mapping.parent.shop_type.shop_type == 'sp':
                    '''4th Step
                        SP mapped data shown
                    '''
                    body = {"from": offset, "size": page_size, "query": query}
                    products_list = es_search(index=parent_mapping.parent.id, body=body)
                    info_logger.info("user {} ".format(self.request.user))
                    info_logger.info("shop {} ".format(shop_id))

                    cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop_id=shop_id,
                                               cart_status__in=['active', 'pending']).last()
                    if cart:
                        cart_products = cart.rt_cart_list.all()
                        cart_check = True
                else:
                    is_store_active = False
        p_list = []
        if not is_store_active:
            body = {
                "from": offset,
                "size": page_size,
                "query": query,
                "_source": {"includes": ["name", "product_images", "pack_size", "weight_unit", "weight_value", "visible"]}
            }
            products_list = es_search(index="all_products", body=body)

        for p in products_list['hits']['hits']:
            if is_store_active:
                counter = 0
                try:
                    price_details = p["_source"]["price_details"]
                    if str(shop_id) in price_details['store'].keys():
                        p["_source"]["price_details"] = price_details['store'][str(shop_id)]
                    elif str(shop.get_shop_pin_code) in price_details['pincode'].keys():
                        p["_source"]["price_details"] = price_details['pincode'][str(shop.get_shop_pin_code)]
                    elif str(shop.get_shop_city.id) in price_details['city'].keys():
                        p["_source"]["price_details"] = price_details['city'][str(shop.get_shop_city.id)]
                    elif str(parent_mapping.parent_id) in price_details['store'].keys():
                        p["_source"]["price_details"] = price_details['store'][str(parent_mapping.parent_id)]

                    for price_detail in p["_source"]["price_details"]:
                        p["_source"]["price_details"][counter]["ptr"] = round(
                            p["_source"]["price_details"][counter]["ptr"], 2)
                        p["_source"]["price_details"][counter]["margin"] = round(
                            p["_source"]["price_details"][counter]["margin"], 2)
                        counter += 1
                except:
                    continue

                if not Product.objects.filter(id=p["_source"]["id"]).exists():
                    logger.info("No product found in DB matching for ES product with id: {}".format(p["_source"]["id"]))
                    continue
                product = Product.objects.get(id=p["_source"]["id"])
                product_coupons = product.getProductCoupons()
                coupons_queryset1 = Coupon.objects.filter(coupon_code__in=product_coupons, coupon_type='catalog')
                coupons_queryset2 = Coupon.objects.filter(coupon_code__in=product_coupons,
                                                          coupon_type='brand').order_by(
                    'rule__cart_qualifying_min_sku_value')
                coupons_queryset = coupons_queryset1 | coupons_queryset2
                coupons = CouponSerializer(coupons_queryset, many=True).data
                p["_source"]["coupon"] = coupons
                # check in case of multiple coupons
                if coupons_queryset:
                    for coupon in coupons_queryset:
                        for product_coupon in coupon.rule.product_ruleset.filter(purchased_product=product):
                            if product_coupon.max_qty_per_use > 0:
                                max_qty = product_coupon.max_qty_per_use
                                for i in coupons:
                                    if i['coupon_type'] == 'catalog':
                                        i['max_qty'] = max_qty

            if cart_check == True:
                for c_p in cart_products:
                    if c_p.cart_product_id == p["_source"]["id"]:
                        keyValList2 = ['discount_on_product']
                        keyValList3 = ['discount_on_brand']
                        if cart.offers:
                            exampleSet2 = cart.offers
                            array2 = list(filter(lambda d: d['sub_type'] in keyValList2, exampleSet2))
                            for i in array2:
                                if i['item_sku'] == c_p.cart_product.product_sku:
                                    discounted_product_subtotal = i['discounted_product_subtotal']
                                    p["_source"]["discounted_product_subtotal"] = discounted_product_subtotal
                            array3 = list(filter(lambda d: d['sub_type'] in keyValList3, exampleSet2))
                            for j in coupons:
                                for i in (array3 + array2):
                                    if j['coupon_code'] == i['coupon_code']:
                                        j['is_applied'] = True
                        user_selected_qty = c_p.qty or 0
                        no_of_pieces = int(c_p.qty) * int(c_p.cart_product.product_inner_case_size)
                        p["_source"]["user_selected_qty"] = user_selected_qty
                        p["_source"]["ptr"] = c_p.applicable_slab_price
                        p["_source"]["no_of_pieces"] = no_of_pieces
                        p["_source"]["sub_total"] = c_p.qty * c_p.item_effective_prices

            p_list.append(p["_source"])

        msg = {'is_store_active': is_store_active,
               'is_success': True,
               'message': ['Products found'],
               'response_data': p_list}
        if not p_list:
            msg = {'is_store_active': is_store_active,
                   'is_success': False,
                   'message': ['Sorry! No product found'],
                   'response_data': None}
        return Response(msg,
                        status=200)


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


class AddToCart(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        cart_product = self.request.POST.get('cart_product')
        qty = self.request.POST.get('qty')
        shop_id = self.request.POST.get('shop_id')
        msg = {'is_success': False, 'message': ['Sorry no any mapping with any shop!'], 'response_data': None}

        if Shop.objects.filter(id=shop_id).exists():
            # get Product
            try:
                product = Product.objects.get(id=cart_product)
            except ObjectDoesNotExist:
                msg['message'] = ["Product not Found"]
                return Response(msg, status=status.HTTP_200_OK)

            if checkNotShopAndMapping(shop_id):
                return Response(msg, status=status.HTTP_200_OK)

            parent_mapping = getShopMapping(shop_id)
            if parent_mapping is None:
                return Response(msg, status=status.HTTP_200_OK)
            if qty is None or qty == '':
                msg['message'] = ["Qty not Found"]
                return Response(msg, status=status.HTTP_200_OK)
            # Check if product blocked for audit
            is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(
                                                                                Product.objects.get(id=cart_product),
                                                                                parent_mapping.parent)
            if is_blocked_for_audit:
                msg['message'] = [ERROR_MESSAGES['4019'].format(Product.objects.get(id=cart_product))]
                return Response(msg, status=status.HTTP_200_OK)

            if is_product_not_eligible(cart_product):
                msg['message'] = ["Product Not Eligible To Order"]
                return Response(msg, status=status.HTTP_200_OK)

            #  if shop mapped with SP
            # available = get_stock(parent_mapping.parent).filter(sku__id=cart_product, quantity__gt=0).values(
            #     'sku__id').annotate(quantity=Sum('quantity'))
            #
            # shop_products_dict = collections.defaultdict(lambda: 0,
            #                                              {g['sku__id']: int(g['quantity']) for g in available})
            type_normal = InventoryType.objects.filter(inventory_type='normal').last()
            available = get_stock(parent_mapping.parent, type_normal, [cart_product])
            shop_products_dict = available
            if parent_mapping.parent.shop_type.shop_type == 'sp':
                ordered_qty = 0
                product = Product.objects.get(id=cart_product)
                # to check capping is exist or not for warehouse and product with status active
                capping = product.get_current_shop_capping(parent_mapping.parent, parent_mapping.retailer)
                if Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
                                       cart_status__in=['active', 'pending']).exists():
                    cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
                                               cart_status__in=['active', 'pending']).last()
                    cart.cart_type = 'RETAIL'
                    cart.approval_status = False
                    cart.cart_status = 'active'
                    cart.seller_shop = parent_mapping.parent
                    cart.buyer_shop = parent_mapping.retailer
                    cart.save()
                else:
                    cart = Cart(last_modified_by=self.request.user, cart_status='active')
                    cart.cart_type = 'RETAIL'
                    cart.approval_status = False
                    cart.seller_shop = parent_mapping.parent
                    cart.buyer_shop = parent_mapping.retailer
                    cart.save()

                if capping:
                    # to get the start and end date according to capping type
                    start_date, end_date = check_date_range(capping)
                    capping_start_date = start_date
                    capping_end_date = end_date
                    if capping_start_date.date() == capping_end_date.date():
                        capping_range_orders = Order.objects.filter(buyer_shop=parent_mapping.retailer,
                                                                    created_at__gte=capping_start_date.date(),
                                                                    ).exclude(order_status='CANCELLED')
                    else:
                        capping_range_orders = Order.objects.filter(buyer_shop=parent_mapping.retailer,
                                                                    created_at__gte=capping_start_date,
                                                                    created_at__lte=capping_end_date).exclude(
                            order_status='CANCELLED')
                    if capping_range_orders:
                        for order in capping_range_orders:
                            if order.ordered_cart.rt_cart_list.filter(cart_product=product).exists():
                                ordered_qty += order.ordered_cart.rt_cart_list.filter(cart_product=product).last().qty
                    if capping.capping_qty > ordered_qty:
                        if (capping.capping_qty - ordered_qty) >= int(qty):
                            if int(qty) == 0:
                                if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                                    CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

                            else:
                                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
                                                                                           cart_product=product)
                                cart_mapping.qty = qty
                                available_qty = shop_products_dict[int(cart_product)] // int(
                                    cart_mapping.cart_product.product_inner_case_size)
                                if int(qty) <= available_qty:
                                    cart_mapping.no_of_pieces = int(qty) * int(product.product_inner_case_size)
                                    cart_mapping.capping_error_msg = ''
                                    cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(
                                        int(available_qty))
                                    cart_mapping.save()
                                else:
                                    cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(
                                        int(available_qty))
                                    cart_mapping.save()
                        else:
                            serializer = CartSerializer(Cart.objects.get(id=cart.id),
                                                        context={'parent_mapping_id': parent_mapping.parent.id,
                                                                 'buyer_shop_id': shop_id})
                            if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                                cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
                                                                                           cart_product=product)
                                if (capping.capping_qty - ordered_qty) > 0:
                                    cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
                                            capping.capping_qty - ordered_qty)]
                                else:
                                    cart_mapping.capping_error_msg = ['You have already exceeded the purchase limit of this product']
                                cart_mapping.save()
                            else:
                                msg = {'is_success': True, 'message': ['The Purchase Limit of the Product is %s #%s' % (
                                    capping.capping_qty - ordered_qty, cart_product)], 'response_data': serializer.data}
                                return Response(msg, status=status.HTTP_200_OK)

                    else:
                        if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                            cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                            if (capping.capping_qty - ordered_qty) > 0:
                                if (capping.capping_qty - ordered_qty) < 0:
                                    cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
                                            0)]
                                else:
                                    cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
                                            capping.capping_qty - ordered_qty)]
                            else:
                                cart_mapping.capping_error_msg = ['You have already exceeded the purchase limit of this product']
                                CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
                            # cart_mapping.save()
                        else:
                            serializer = CartSerializer(Cart.objects.get(id=cart.id),
                                                        context={'parent_mapping_id': parent_mapping.parent.id,
                                                                 'buyer_shop_id': shop_id})
                            if (capping.capping_qty - ordered_qty) < 0:
                                msg = {'is_success': True, 'message': ['You have already exceeded the purchase limit of this product #%s' % (
                                    cart_product)], 'response_data': serializer.data}
                            else:
                                msg = {'is_success': True, 'message': ['You have already exceeded the purchase limit of this product #%s' % (
                                    cart_product)], 'response_data': serializer.data}
                            return Response(msg, status=status.HTTP_200_OK)
                else:
                    if int(qty) == 0:
                        if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                            CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

                    else:
                        cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                        available_qty = shop_products_dict.get(int(cart_product),0) // int(
                            cart_mapping.cart_product.product_inner_case_size)
                        cart_mapping.qty = qty
                        if int(qty) <= available_qty:
                            cart_mapping.no_of_pieces = int(qty) * int(product.product_inner_case_size)
                            cart_mapping.capping_error_msg = ''
                            cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(int(available_qty))
                            cart_mapping.save()
                        else:
                            cart_mapping.qty_error_msg = ERROR_MESSAGES['AVAILABLE_QUANTITY'].format(int(available_qty))
                            cart_mapping.save()

                if cart.rt_cart_list.count() <= 0:
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                           'response_data': None}
                else:
                    serializer = CartSerializer(Cart.objects.get(id=cart.id),
                                                context={'parent_mapping_id': parent_mapping.parent.id,
                                                         'buyer_shop_id': shop_id})
                    for i in serializer.data['rt_cart_list']:
                        if i['cart_product']['price_details']['mrp'] == False:
                            CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
                            msg = {'is_success': True, 'message': ['Data added to cart'],
                                   'response_data': serializer.data}
                        else:
                            msg = {'is_success': True, 'message': ['Data added to cart'],
                                   'response_data': serializer.data}
                return Response(msg, status=status.HTTP_200_OK)

            #  if shop mapped with gf
            elif parent_mapping.parent.shop_type.shop_type == 'gf':
                if GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                 cart_status__in=['active', 'pending']).exists():
                    cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                         cart_status__in=['active', 'pending']).last()
                    cart.cart_status = 'active'
                    cart.save()
                else:
                    cart = GramMappedCart(last_modified_by=self.request.user, cart_status='active')
                    cart.save()

                if int(qty) == 0:
                    if GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                        GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

                else:
                    cart_mapping, _ = GramMappedCartProductMapping.objects.get_or_create(cart=cart,
                                                                                         cart_product=product)
                    cart_mapping.qty = qty
                    cart_mapping.save()

                if cart.rt_cart_list.count() <= 0:
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                           'response_data': None}
                else:
                    serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id),
                                                          context={'parent_mapping_id': parent_mapping.parent.id})

                    msg = {'is_success': True, 'message': ['Data added to cart'], 'response_data': serializer.data}
                return Response(msg, status=status.HTTP_200_OK)

            else:
                msg = {'is_success': False,
                       'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                       'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)


        else:
            return Response(msg, status=status.HTTP_200_OK)

    def sp_mapping_cart(self, qty, product):
        pass

    def gf_mapping_cart(self, qty, product):
        pass


class CartDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def delivery_message(self, shop_type):
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

    def get(self, request, *args, **kwargs):
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Sorry shop or shop mapping not found'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with sp
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            if Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
                                   cart_status__in=['active', 'pending']).exists():
                cart = Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
                                           cart_status__in=['active', 'pending']).last()
                Cart.objects.filter(id=cart.id).update(offers=cart.offers_applied())
                cart_products = CartProductMapping.objects.select_related(
                    'cart_product'
                ).filter(
                    cart=cart
                )

                # Check and remove if any product blocked for audit
                cart_product_to_be_deleted = []
                for p in cart_products:
                    is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
                                                                                            parent_mapping.parent)
                    if is_blocked_for_audit:
                        cart_product_to_be_deleted.append(p.id)
                if len(cart_product_to_be_deleted) > 0:
                    CartProductMapping.objects.filter(id__in=cart_product_to_be_deleted).delete()
                    cart_products = CartProductMapping.objects.select_related('cart_product').filter(cart=cart)

                # available = get_stock(parent_mapping.parent).filter(sku__id__in=cart_products.values('cart_product'),
                #                                                     quantity__gt=0).values('sku__id').annotate(
                #     quantity=Sum('quantity'))
                # shop_products_dict = collections.defaultdict(lambda: 0,
                #                                              {g['sku__id']: int(g['quantity']) for g in available})

                for cart_product in cart_products:
                    item_qty = CartProductMapping.objects.filter(cart=cart,
                                                                 cart_product=cart_product.cart_product).last().qty
                    updated_no_of_pieces = (item_qty * int(cart_product.cart_product.product_inner_case_size))
                    CartProductMapping.objects.filter(cart=cart, cart_product=cart_product.cart_product).update(
                        no_of_pieces=updated_no_of_pieces)
                if cart.rt_cart_list.count() <= 0:
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                           'response_data': None}
                else:
                    for i in Cart.objects.get(id=cart.id).rt_cart_list.all():
                        if i.cart_product.getMRP(cart.seller_shop.id, cart.buyer_shop.id) == False:
                            CartProductMapping.objects.filter(cart__id=cart.id,
                                                              cart_product__id=i.cart_product.id).delete()


                    serializer = CartSerializer(
                        Cart.objects.get(id=cart.id),
                        context={'parent_mapping_id': parent_mapping.parent.id,
                                 'buyer_shop_id': shop_id,
                                 'delivery_message': self.delivery_message(parent_mapping.parent.shop_type)}
                    )
                    for i in serializer.data['rt_cart_list']:
                        if not i['cart_product']['product_pro_image']:
                            product = Product.objects.get(id=i['cart_product']['id'])
                            if product.use_parent_image:
                                for im in product.parent_product.parent_product_pro_image.all():
                                    parent_image_serializer = ParentProductImageSerializer(im)
                                    i['cart_product']['product_pro_image'].append(parent_image_serializer.data)

                        if i['cart_product']['price_details']['mrp'] == False:
                            i['qty'] = 0
                            CartProductMapping.objects.filter(cart__id=i['cart']['id'],
                                                              cart_product__id=i['cart_product']['id']).delete()
                            msg = {
                                'is_success': True,
                                'message': [''],
                                'response_data': serializer.data
                            }
                        else:
                            msg = {
                                'is_success': True,
                                'message': [''],
                                'response_data': serializer.data
                            }

                return Response(msg, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                       'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with gf
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            if GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                             cart_status__in=['active', 'pending']).exists():
                cart = GramMappedCart.objects.filter(last_modified_by=self.request.user,
                                                     cart_status__in=['active', 'pending']).last()
                if cart.rt_cart_list.count() <= 0:
                    msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                           'response_data': None}
                else:
                    serializer = GramMappedCartSerializer(
                        GramMappedCart.objects.get(id=cart.id),
                        context={'parent_mapping_id': parent_mapping.parent.id,
                                 'delivery_message': self.delivery_message(parent_mapping.parent.shop_type)}
                    )
                    msg = {'is_success': True, 'message': [
                        ''], 'response_data': serializer.data}
                return Response(msg, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False, 'message': ['Sorry no any product yet added to this cart'],
                       'response_data': None}
                return Response(msg, status=status.HTTP_200_OK)

        else:
            msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)


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
                        'transaction_id': cart.order_id,
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
        return Response(msg, status=status.HTTP_200_OK)

    # def sp_mapping_order_reserve(self):
    #     pass
    # def gf_mapping_order_reserve(self):
    #     pass


class CreateOrder(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        cart_id = self.request.POST.get('cart_id')
        billing_address_id = self.request.POST.get('billing_address_id')
        shipping_address_id = self.request.POST.get('shipping_address_id')
        total_tax_amount = self.request.POST.get('total_tax_amount', 0)
        shop_id = self.request.POST.get('shop_id')

        msg = {'is_success': False, 'message': ['Have some error in shop or mapping'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        shop = getShop(shop_id)
        if shop is None:
            return Response(msg, status=status.HTTP_200_OK)

        if shop.shop_type.shop_type == 'r':
            order_config = GlobalConfig.objects.filter(key='retailer_order_count').last()

        elif shop.shop_type.shop_type == 'f':
            if str(shop.shop_type.shop_sub_type) == 'fofo':
                order_config = GlobalConfig.objects.filter(key='fofo_order_count').last()
            elif str(shop.shop_type.shop_sub_type) == 'foco':
                order_config = GlobalConfig.objects.filter(key='foco_order_count').last()

        if order_config.value is not None:
            msg = {'is_success': False, 'message': [
                'Because of the current surge in orders, we are not taking any more orders for today. We will '
                'start taking orders again tomorrow. We regret the inconvenience caused to you'],
                   'response_data': None}
            if shop.shop_type.shop_type == 'r':
                if not Order.objects.filter(buyer_shop__shop_type=shop.shop_type, created_at__date=datetime.today()).exclude(
                        order_status='CANCELLED').count() < order_config.value:
                    return Response(msg, status=status.HTTP_200_OK)
            if shop.shop_type.shop_type == 'f':
                if not Order.objects.filter(buyer_shop__shop_type__shop_sub_type=shop.shop_type.shop_sub_type, created_at__date=datetime.today()).exclude(
                        order_status='CANCELLED').count() < order_config.value:
                    return Response(msg, status=status.HTTP_200_OK)

        # get billing address
        try:
            billing_address = Address.objects.get(id=billing_address_id)
        except ObjectDoesNotExist:
            msg['message'] = ['Billing address not found']
            return Response(msg, status=status.HTTP_200_OK)

        # get shipping address
        try:
            shipping_address = Address.objects.get(id=shipping_address_id)
        except ObjectDoesNotExist:
            msg['message'] = ['Shipping address not found']
            return Response(msg, status=status.HTTP_200_OK)

        current_url = request.get_host()
        # if shop mapped with sp
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            ordered_qty = 0
            # self.sp_mapping_order_reserve()
            with transaction.atomic():
                if Cart.objects.filter(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
                                       id=cart_id).exists():
                    cart = Cart.objects.get(last_modified_by=self.request.user, buyer_shop=parent_mapping.retailer,
                                            id=cart_id)
                    # Check and remove if any product blocked for audit
                    for p in cart.rt_cart_list.all():
                        is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(p.cart_product,
                                                                                                parent_mapping.parent)
                        if is_blocked_for_audit:
                            p.delete()

                    orderitems = []
                    for i in cart.rt_cart_list.all():
                        orderitems.append(i.get_cart_product_price(cart.seller_shop, cart.buyer_shop))
                    if len(orderitems) == 0:
                        CartProductMapping.objects.filter(cart__id=cart.id, cart_product_price=None).delete()
                        for cart_price in cart.rt_cart_list.all():
                            cart_price.cart_product_price = None
                            cart_price.save()
                        msg['message'] = [
                            "Some products in cart aren’t available anymore, please update cart and remove product from cart upon revisiting it"]
                        return Response(msg, status=status.HTTP_200_OK)
                    else:
                        cart.offers=cart.offers_applied()
                        cart.cart_status = 'ordered'
                        cart.buyer_shop = shop
                        cart.seller_shop = parent_mapping.parent
                        cart.save()

                    for cart_product in cart.rt_cart_list.all():
                        # to check capping is exist or not for warehouse and product with status active
                        capping = cart_product.cart_product.get_current_shop_capping(parent_mapping.parent,
                                                                                     parent_mapping.retailer)
                        product_qty = int(cart_product.qty)
                        if capping:
                            cart_products = cart_product.cart_product
                            msg = capping_check(capping, parent_mapping, cart_products, product_qty, ordered_qty)
                            if msg[0] is False:
                                msg = {'is_success': True,
                                       'message': msg[1], 'response_data': None}
                                return Response(msg, status=status.HTTP_200_OK)
                        else:
                            pass

                    order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=shop.get_shop_parent.id,
                                                                           transaction_id=cart.order_id,
                                                                           warehouse_internal_inventory_release=None,
                                                                           ).last()

                    if order_reserve_obj:
                        order, _ = Order.objects.get_or_create(last_modified_by=request.user, ordered_by=request.user,
                                                               ordered_cart=cart, order_no=cart.order_id)

                        order.billing_address = billing_address
                        order.shipping_address = shipping_address
                        order.buyer_shop = shop
                        order.seller_shop = parent_mapping.parent
                        order.total_tax_amount = float(total_tax_amount)
                        order.order_status = Order.ORDERED
                        order.save()

                        # Changes OrderedProductReserved Status
                        for ordered_reserve in OrderedProductReserved.objects.filter(cart=cart,
                                                                                     reserve_status=OrderedProductReserved.RESERVED):
                            ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
                            ordered_reserve.order_product_reserved.save()
                            ordered_reserve.reserve_status = OrderedProductReserved.ORDERED
                            ordered_reserve.save()
                        sku_id = [i.cart_product.id for i in cart.rt_cart_list.all()]
                        reserved_args = json.dumps({
                            'shop_id': parent_mapping.parent.id,
                            'transaction_id': cart.order_id,
                            'transaction_type': 'ordered',
                            'order_status': order.order_status
                        })
                        order_result = OrderManagement.release_blocking_from_order(reserved_args, sku_id)
                        if order_result is False:
                            order.delete()
                            msg = {'is_success': False, 'message': ['No item in this cart.'], 'response_data': None}
                            return Response(msg, status=status.HTTP_200_OK)
                        serializer = OrderSerializer(order,
                                                     context={'parent_mapping_id': parent_mapping.parent.id,
                                                              'buyer_shop_id': shop_id,
                                                              'current_url': current_url})
                        msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                        # try:
                        #     request = jsonpickle.encode(request, unpicklable=False)
                        #     order = jsonpickle.encode(order, unpicklable=False)
                        #     pick_list_download.delay(request, order)
                        # except:
                        #     msg = {'is_success': False, 'message': ['Pdf is not uploaded for Order'],
                        #            'response_data': None}
                        #     return Response(msg, status=status.HTTP_200_OK)
                    else:
                        msg = {'is_success': False, 'message': ['Sorry! your session has timed out.'], 'response_data': None}
                        return Response(msg, status=status.HTTP_200_OK)

                return Response(msg, status=status.HTTP_200_OK)

        # if shop mapped with gf
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            if GramMappedCart.objects.filter(last_modified_by=self.request.user, id=cart_id).exists():
                cart = GramMappedCart.objects.get(last_modified_by=self.request.user, id=cart_id)
                cart.cart_status = 'ordered'
                cart.save()

                if GramOrderedProductReserved.objects.filter(cart=cart).exists():
                    order, _ = GramMappedOrder.objects.get_or_create(last_modified_by=request.user,
                                                                     ordered_by=request.user, ordered_cart=cart,
                                                                     order_no=cart.order_id)

                    order.billing_address = billing_address
                    order.shipping_address = shipping_address
                    order.buyer_shop = shop
                    order.seller_shop = parent_mapping.parent
                    order.order_status = 'ordered'
                    order.save()

                    pick_list = PickList.objects.get(cart=cart)
                    pick_list.order = order
                    pick_list.status = True
                    pick_list.save()

                    # Remove Data From OrderedProductReserved
                    for ordered_reserve in GramOrderedProductReserved.objects.filter(cart=cart):
                        ordered_reserve.order_product_reserved.ordered_qty = ordered_reserve.reserved_qty
                        ordered_reserve.order_product_reserved.save()
                        ordered_reserve.reserve_status = 'ordered'
                        ordered_reserve.save()

                    serializer = GramMappedOrderSerializer(order,
                                                           context={'parent_mapping_id': parent_mapping.parent.id,
                                                                    'current_url': current_url})
                    msg = {'is_success': True, 'message': [''], 'response_data': serializer.data}
                else:
                    msg = {'is_success': False, 'message': ['available_qty is none'], 'response_data': None}
                    return Response(msg, status=status.HTTP_200_OK)

        else:
            msg = {'is_success': False, 'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)
        return Response(msg, status=status.HTTP_200_OK)


# OrderedProductMapping.objects.filter()

class OrderList(generics.ListAPIView):
    serializer_class = OrderListSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        user = self.request.user
        # queryset = self.get_queryset()
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        current_url = request.get_host()
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            queryset = Order.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')[:10]
            serializer = OrderListSerializer(
                queryset, many=True,
                context={'parent_mapping_id': parent_mapping.parent.id,
                         'current_url': current_url,
                         'buyer_shop_id': shop_id})
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            queryset = GramMappedOrder.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
            serializer = GramMappedOrderSerializer(
                queryset, many=True,
                context={'parent_mapping_id': parent_mapping.parent.id,
                         'current_url': current_url,
                         'buyer_shop_id': shop_id})

        if serializer.data:
            msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        shop_id = self.request.GET.get('shop_id')
        msg = {'is_success': False, 'message': ['Data Not Found'], 'response_data': None}

        if checkNotShopAndMapping(shop_id):
            return Response(msg, status=status.HTTP_200_OK)

        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return Response(msg, status=status.HTTP_200_OK)

        current_url = request.get_host()
        if parent_mapping.parent.shop_type.shop_type == 'sp':
            queryset = Order.objects.get(id=pk)
            serializer = OrderDetailSerializer(
                queryset,
                context={'parent_mapping_id': parent_mapping.parent.id,
                         'current_url': current_url,
                         'buyer_shop_id': shop_id})
        elif parent_mapping.parent.shop_type.shop_type == 'gf':
            queryset = GramMappedOrder.objects.get(id=pk)
            serializer = GramMappedOrderSerializer(queryset, context={'parent_mapping_id': parent_mapping.parent.id,
                                                                      'current_url': current_url})

        if serializer.data:
            msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)


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
        #print(paid_amount)

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
            igst, cgst, sgst, cess, surcharge = sum(gst_tax_list), (sum(gst_tax_list)) / 2, (sum(gst_tax_list)) / 2, sum(
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
                "igst": igst, "cgst": cgst, "sgst": sgst, "product_special_cess":product_special_cess, "tcs_tax": tcs_tax, "tcs_rate": tcs_rate, "cess": cess,
                "surcharge": surcharge, "total_amount": total_amount, "amount": amount,
                "barcode": barcode, "product_listing": product_listing, "rupees": rupees, "tax_rupees": tax_rupees,
                "seller_shop_gistin": seller_shop_gistin, "buyer_shop_gistin": buyer_shop_gistin,
                "open_time": open_time, "close_time": close_time, "sum_qty": sum_qty, "sum_basic_amount": sum_basic_amount,
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
                        i["product_special_cess"] = i["product_special_cess"] + m.product.product_special_cess if m.product.product_special_cess else 0
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
                'transaction_id': cart.order_id,
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


class CancelOrder(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def put(self, request, format=None):
        """
        Return error message
        """
        msg = {'is_success': False,
               'message': ['Sorry! Order cannot be cancelled from the APP'],
               'response_data': None}
        return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        # try:
        #     order = Order.objects.get(buyer_shop__shop_owner=request.user,
        #                               pk=request.data['order_id'])
        # except ObjectDoesNotExist:
        #     msg = {'is_success': False,
        #            'message': ['Order is not associated with the current user'],
        #            'response_data': None}
        #     return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        #
        # serializer = CancelOrderSerializer(order, data=request.data,
        #                                    context={'order': order})
        # if serializer.is_valid():
        #     serializer.save()
        #     msg = {'is_success': True,
        #            'message': ["Order Cancelled Successfully!"],
        #            'response_data': serializer.data}
        #     return Response(msg, status=status.HTTP_200_OK)
        # else:
        #     return format_serializer_errors(serializer.errors)


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
        return ShopUserMapping.objects.filter(manager__in=self.get_manager(), shop__shop_type__shop_type__in=['r', 'f', 'sp'],
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
