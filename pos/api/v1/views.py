import codecs
import csv
import datetime
import json
import logging
import sys
from copy import deepcopy
from decimal import Decimal
from io import BytesIO

import requests
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Sum, F, Count, Subquery, OuterRef, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce
from products.common_function import get_response
from rest_framework import status, permissions, mixins, viewsets
from rest_auth import authentication
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon

from pos.models import (RetailerProduct, RetailerProductImage, ShopCustomerMap, Vendor, PosCart, PosGRNOrder,
                        PaymentType, MeasurementCategory, PosReturnGRNOrder, BulkRetailerProduct, Payment,
                        PosCartProductMapping)
from pos.tasks import update_es
from pos.common_functions import (RetailerProductCls, OffersCls, serializer_error, api_response, PosInventoryCls,
                                  check_pos_shop, ProductChangeLogs, pos_check_permission_delivery_person,
                                  pos_check_permission, check_return_status, pos_check_user_permission)

from pos.common_validators import compareList, validate_user_type_for_pos_shop, validate_id
from pos.models import RetailerProduct, RetailerProductImage, ShopCustomerMap, Vendor, PosCart, PosGRNOrder, \
    PaymentType, PosReturnGRNOrder,Payment
from pos.views import products_image
from pos.services import grn_product_search, grn_return_search, non_grn_return_search
from products.models import Product
from retailer_backend.utils import SmallOffsetPagination, OffsetPaginationDefault50
from retailer_to_sp.models import OrderedProduct, Order, OrderReturn
from shops.models import Shop
from wms.models import PosInventoryChange, PosInventoryState, PosInventory
from .serializers import (BulkCreateUpdateRetailerProductsSerializer, PaymentTypeSerializer, RetailerProductCreateSerializer, RetailerProductUpdateSerializer,
                          RetailerProductResponseSerializer, CouponOfferSerializer, FreeProductOfferSerializer,
                          ComboOfferSerializer, CouponOfferUpdateSerializer, ComboOfferUpdateSerializer,
                          CouponListSerializer, FreeProductOfferUpdateSerializer, OfferCreateSerializer,
                          OfferUpdateSerializer, CouponGetSerializer, OfferGetSerializer, ImageFileSerializer,
                          InventoryReportSerializer, InventoryLogReportSerializer, SalesReportResponseSerializer,
                          SalesReportSerializer, CustomerReportSerializer, CustomerReportResponseSerializer,
                          CustomerReportDetailResponseSerializer, UpdateRetailerProductCsvSerializer, VendorSerializer, VendorListSerializer,
                          POSerializer, POGetSerializer, POProductInfoSerializer, POListSerializer,
                          PosGrnOrderCreateSerializer, PosGrnOrderUpdateSerializer, GrnListSerializer,
                          GrnOrderGetSerializer, MeasurementCategorySerializer, ReturnGrnOrderSerializer,
                          GrnOrderGetListSerializer, PRNOrderSerializer, BulkProductUploadSerializers, ContectUs,
                          RetailerProductListSerializer, DownloadRetailerProductsCsvShopWiseSerializer, DownloadUploadRetailerProductsCsvSampleFileSerializer,
                          CreateRetailerProductCsvSerializer, LinkRetailerProductCsvSerializer, LinkRetailerProductsBulkUploadSerializer,
                          RetailerProductImageSerializer, RetailerProductImageBulkUploadSerializer, PosShopListSerializer)
from global_config.views import get_config
from ...forms import RetailerProductsStockUpdateForm
from ...views import stock_update
from global_config.models import GlobalConfig
from pos.payU_payment import *

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')

OFFER_SERIALIZERS_MAP = {
    1: CouponOfferSerializer,
    2: ComboOfferSerializer,
    3: FreeProductOfferSerializer
}

OFFER_UPDATE_SERIALIZERS_MAP = {
    1: CouponOfferUpdateSerializer,
    2: ComboOfferUpdateSerializer,
    3: FreeProductOfferUpdateSerializer
}


class PosProductView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    @pos_check_permission
    def post(self, request, *args, **kwargs):
        """
            Create Product
        """
        shop = kwargs['shop']
        modified_data = self.validate_create(shop.id)
        if 'error' in modified_data:
            return api_response(modified_data['error'])
        serializer = RetailerProductCreateSerializer(data=modified_data)
        if serializer.is_valid():
            data = serializer.data
            name, ean, mrp, sp, offer_price, offer_sd, offer_ed, linked_pid, description, stock_qty, online_enabled, online_price = \
                data[
                    'product_name'], data['product_ean_code'], data['mrp'], data['selling_price'], data[
                    'offer_price'], data['offer_start_date'], data['offer_end_date'], data[
                    'linked_product_id'], data['description'], data['stock_qty'], data['online_enabled'], data.get(
                    'online_price', None)
            with transaction.atomic():
                # Decide sku_type 2 = using GF product, 1 = new product
                sku_type = 2 if linked_pid else 1
                # sku_type = self.get_sku_type(mrp, name, ean, linked_pid)
                # Create product
                product = RetailerProductCls.create_retailer_product(shop.id, name, mrp, sp, linked_pid, sku_type,
                                                                     description, ean, self.request.user, 'product',
                                                                     data['product_pack_type'],
                                                                     data['measurement_category_id'],
                                                                     None, 'active', offer_price, offer_sd, offer_ed,
                                                                     None, online_enabled, online_price,
                                                                     data['purchase_pack_size'],
                                                                     add_offer_price=data['add_offer_price'])
                # Upload images
                if 'images' in modified_data:
                    RetailerProductCls.create_images(product, modified_data['images'])
                product.save()
                # Add Inventory
                PosInventoryCls.app_stock_inventory(product.id, PosInventoryState.NEW, PosInventoryState.AVAILABLE,
                                                    round(Decimal(stock_qty), 3), self.request.user, product.sku,
                                                    PosInventoryChange.STOCK_ADD)
                serializer = RetailerProductResponseSerializer(product)
                return api_response('Product has been created successfully!', serializer.data, status.HTTP_200_OK,
                                    True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    @pos_check_permission_delivery_person
    @pos_check_user_permission
    def put(self, request, *args, **kwargs):
        """
            Update product
        """
        shop = kwargs['shop']
        modified_data, success_msg = self.validate_update(shop.id)
        if 'error' in modified_data:
            return api_response(modified_data['error'])

        if not compareList(list(modified_data.keys()), ['product_id', 'stock_qty', 'shop_id', 'reason_for_update']):
            pos_shop_user_obj = validate_user_type_for_pos_shop(shop, request.user)
            if 'error' in pos_shop_user_obj:
                return api_response(pos_shop_user_obj['error'])
        serializer = RetailerProductUpdateSerializer(data=modified_data)
        if serializer.is_valid():
            data = serializer.data
            product = RetailerProduct.objects.get(id=data['product_id'], shop_id=shop.id)
            name, ean, mrp, sp, description, stock_qty, online_enabled, online_price, product_pack_type = data[
                                                                                                              'product_name'], \
                                                                                                          data[
                                                                                                              'product_ean_code'], \
                                                                                                          data[
                                                                                                              'mrp'], \
                                                                                                          data[
                                                                                                              'selling_price'], \
                                                                                                          data[
                                                                                                              'description'], \
                                                                                                          data[
                                                                                                              'stock_qty'], \
                                                                                                          data[
                                                                                                              'online_enabled'] if 'online_enabled' in data else None, data.get(
                'online_price', None), data.get('product_pack_type', product.product_pack_type)
            measurement_category_id = data.get("measurement_category_id", product.measurement_category_id)
            offer_price, offer_sd, offer_ed = data['offer_price'], data['offer_start_date'], data['offer_end_date']
            add_offer_price = data['add_offer_price']
            ean_not_available = data['ean_not_available']
            remarks = data['reason_for_update']

            with transaction.atomic():
                old_product = deepcopy(product)
                # Update product
                if ean_not_available is not None:
                    product.product_ean_code = ean
                product.mrp = mrp if mrp else product.mrp
                product.name = name if name else product.name
                product.selling_price = sp if sp else product.selling_price
                product.purchase_pack_size = data['purchase_pack_size'] if data[
                    'purchase_pack_size'] else product.purchase_pack_size
                if add_offer_price is not None:
                    product.offer_price = offer_price
                    product.offer_start_date = offer_sd
                    product.offer_end_date = offer_ed
                product.status = data['status'] if data['status'] else product.status
                product.description = description if description else product.description
                if online_enabled is not None:
                    product.online_enabled = online_enabled
                    if online_enabled is True and float(online_price) == 0.0 and add_offer_price is True:
                        product.online_price = offer_price
                    elif online_enabled is True and float(online_price) == 0.0:
                        product.online_price = sp if sp else product.selling_price
                    else:
                        product.online_price = online_price if online_price else sp
                else:
                    product.online_price = online_price if online_price else sp
                product.product_pack_type = product_pack_type
                product.measurement_category_id = measurement_category_id
                # Update images
                if 'image_ids' in modified_data:
                    RetailerProductImage.objects.filter(product=product).exclude(
                        id__in=modified_data['image_ids']).delete()
                if 'images' in modified_data:
                    RetailerProductCls.update_images(product, modified_data['images'])
                product.save()
                if 'stock_qty' in modified_data:
                    # Update Inventory
                    PosInventoryCls.app_stock_inventory(product.id, PosInventoryState.AVAILABLE,
                                                        PosInventoryState.AVAILABLE, stock_qty, self.request.user,
                                                        product.sku, PosInventoryChange.STOCK_UPDATE, remarks)
                # Change logs
                ProductChangeLogs.product_update(product, old_product, self.request.user, 'product', product.sku)
                serializer = RetailerProductResponseSerializer(product)
                if data['is_discounted']:
                    discounted_price = data['discounted_price']
                    discounted_stock = data['discounted_stock']
                    product_status = 'active' if Decimal(discounted_stock) > 0 else 'deactivated'

                    initial_state = PosInventoryState.AVAILABLE
                    tr_type = PosInventoryChange.STOCK_UPDATE

                    discounted_product = RetailerProduct.objects.filter(product_ref=product).last()
                    if not discounted_product:

                        initial_state = PosInventoryState.NEW
                        tr_type = PosInventoryChange.STOCK_ADD

                        discounted_product = RetailerProductCls.create_retailer_product(product.shop.id, product.name,
                                                                                        product.mrp,
                                                                                        discounted_price,
                                                                                        product.linked_product_id, 4,
                                                                                        product.description,
                                                                                        product.product_ean_code,
                                                                                        self.request.user, 'product',
                                                                                        product.product_pack_type,
                                                                                        product.measurement_category_id,
                                                                                        None, product_status,
                                                                                        None, None, None, product,
                                                                                        False, None)
                    else:
                        RetailerProductCls.update_price(discounted_product.id, discounted_price, product_status,
                                                        self.request.user, 'product', discounted_product.sku)

                    PosInventoryCls.app_stock_inventory(discounted_product.id, initial_state,
                                                        PosInventoryState.AVAILABLE, discounted_stock,
                                                        self.request.user,
                                                        discounted_product.sku, tr_type, remarks)
                return api_response(success_msg, serializer.data, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    def validate_create(self, shop_id):
        # Validate product data
        try:
            p_data = json.loads(self.request.data["data"])
        except:
            return {'error': "Invalid Data Format"}
        image_files = self.request.FILES.getlist('images')
        if 'image_urls' in p_data:
            try:
                validate = URLValidator()
                for image_url in p_data['image_urls']:
                    validate(image_url)
            except ValidationError:
                return {"error": "Invalid Image Url / Urls"}
            for image_url in p_data['image_urls']:
                try:
                    response = requests.get(image_url)
                    image = BytesIO(response.content)
                    image = InMemoryUploadedFile(image, 'ImageField', "gmfact_image.jpeg", 'image/jpeg',
                                                 sys.getsizeof(image),
                                                 None)
                    serializer = ImageFileSerializer(data={'image': image})
                    if serializer.is_valid():
                        image_files.append(image)
                except:
                    pass
        p_data['images'] = image_files
        p_data['shop_id'] = shop_id
        return p_data

    def validate_update(self, shop_id):
        # Validate product data
        success_msg = 'Product has been updated successfully!'
        try:
            p_data = json.loads(self.request.data["data"])
        except (KeyError, ValueError):
            return {'error': "Invalid Data Format"}, "error_msg"
        if 'product_name' not in p_data:
            updated_fields = []
            if 'selling_price' in p_data:
                updated_fields.append('Price')
            if 'status' in p_data:
                updated_fields.append('Status')
            if 'stock_qty' in p_data:
                updated_fields.append('Quantity')

            if len(updated_fields) > 1:
                success_msg = ', '.join(updated_fields[:-1]) + \
                              f' and {updated_fields[-1]} has been updated successfully!'
            elif len(updated_fields) == 1:
                success_msg = ', '.join(updated_fields) + ' has been updated successfully!'
            else:
                success_msg = 'Product has been updated successfully!'
        # Update product data with shop id and images
        p_data['shop_id'] = shop_id
        if self.request.FILES.getlist('images'):
            p_data['images'] = self.request.FILES.getlist('images')
        return p_data, success_msg

    @staticmethod
    def get_sku_type(mrp, name, ean, linked_pid=None):
        """
            sku_type 3 = using GF product changed detail, 2 = using GF product same detail, 1 = new product
        """
        sku_type = 1
        if linked_pid:
            linked_product = Product.objects.get(id=linked_pid)
            sku_type = 2
            if Decimal(mrp) != linked_product.product_mrp or name != linked_product.product_name or \
                    ean != linked_product.product_ean_code:
                sku_type = 3
        return sku_type


class CouponOfferCreation(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
            Get Offer / Offers List
        """
        shop, coupon_id = kwargs['shop'], request.GET.get('id')
        if coupon_id:
            serializer = OfferGetSerializer(data={'id': coupon_id, 'shop_id': shop.id})
            if serializer.is_valid():
                return self.get_offer(coupon_id)
            else:
                return api_response(serializer_error(serializer))
        else:
            return self.get_offers_list(request, shop.id)

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post(self, request, *args, **kwargs):
        """
            Create Any Offer
        """
        serializer = OfferCreateSerializer(data=request.data)
        if serializer.is_valid():
            return self.create_offer(serializer.data, kwargs['shop'].id)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    @pos_check_permission_delivery_person
    def put(self, request, *args, **kwargs):
        """
           Update Any Offer
        """
        shop = kwargs['shop']
        data = request.data
        data['shop_id'] = shop.id
        serializer = OfferUpdateSerializer(data=data)
        if serializer.is_valid():
            return self.update_offer(serializer.data, shop.id)
        else:
            return api_response(serializer_error(serializer))

    def create_offer(self, data, shop_id):
        offer_type = data['offer_type']
        serializer_class = OFFER_SERIALIZERS_MAP[data['offer_type']]
        serializer = serializer_class(data=self.request.data)
        if serializer.is_valid():
            with transaction.atomic():
                data.update(serializer.data)
                if offer_type == 1:
                    return self.create_coupon(data, shop_id)
                elif offer_type == 2:
                    return self.create_combo_offer(data, shop_id)
                else:
                    return self.create_free_product_offer(data, shop_id)
        else:
            return api_response(serializer_error(serializer))

    def update_offer(self, data, shop_id):
        offer_type = data['offer_type']
        serializer_class = OFFER_UPDATE_SERIALIZERS_MAP[data['offer_type']]
        serializer = serializer_class(data=self.request.data)
        if serializer.is_valid():
            with transaction.atomic():
                data.update(serializer.data)
                success_msg = 'Offer has been updated successfully!'
                if 'coupon_name' not in data and 'is_active' in data:
                    success_msg = 'Offer has been activated successfully!' if data[
                        'is_active'] else 'Offer has been deactivated successfully!'
                if offer_type == 1:
                    return self.update_coupon(data, shop_id, success_msg)
                elif offer_type == 2:
                    return self.update_combo(data, shop_id, success_msg)
                else:
                    return self.update_free_product_offer(data, shop_id, success_msg)
        else:
            return api_response(serializer_error(serializer))

    @staticmethod
    def get_offer(coupon_id):
        coupon = CouponGetSerializer(Coupon.objects.filter(id=coupon_id).last()).data
        coupon.update(coupon['details'])
        coupon.pop('details')
        return api_response("Offers", coupon, status.HTTP_200_OK, True)

    def get_offers_list(self, request, shop_id):
        """
          Get Offers List
       """
        shop = Shop.objects.filter(shop_name="Wherehouse").last()
        app_type = request.META.get('HTTP_APP_TYPE', None)
        if app_type == '2':
            coupon = Coupon.objects.select_related('rule').filter(Q(shop=shop_id)|Q(shop=shop))\
                .filter(Q(coupon_enable_on='pos')|Q(coupon_enable_on='all'))
        elif app_type == '3':
            coupon = Coupon.objects.select_related('rule').filter(Q(shop=shop_id)|Q(shop=shop))\
                .filter(Q(coupon_enable_on='online')|Q(coupon_enable_on='all'))
        if request.GET.get('search_text'):
            coupon = coupon.filter(coupon_name__icontains=request.GET.get('search_text'))
        coupon = coupon.order_by('-updated_at')
        objects = self.pagination_class().paginate_queryset(coupon, self.request)
        data = CouponListSerializer(objects, many=True).data
        for coupon in data:
            coupon.update(coupon['details'])
            coupon.pop('details')
        return api_response("Offers List", data, status.HTTP_200_OK, True)

    @staticmethod
    def create_coupon(data, shop_id):
        """
            Discount on order
        """
        shop = Shop.objects.filter(id=shop_id).last()
        start_date, expiry_date, discount_value, discount_amount = data['start_date'], data['end_date'], data[
            'discount_value'], data['order_value']
        discount_value_str = str(discount_value).rstrip('0').rstrip('.')
        discount_amount_str = str(discount_amount).rstrip('0').rstrip('.')
        if data['is_percentage']:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value,
                                                        max_discount=data['max_discount'], is_percentage=True)
            if discount_obj.max_discount and float(discount_obj.max_discount) > 0:
                max_discount_str = str(discount_obj.max_discount).rstrip('0').rstrip('.')
                coupon_code = discount_value_str + "% off upto ₹" + max_discount_str + " on orders above ₹" + discount_amount_str
            else:
                coupon_code = discount_value_str + "% off on orders above ₹" + discount_amount_str
            rule_set_name_with_shop_id = str(shop_id) + "_" + coupon_code
        elif data['is_point']:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value,
                                                        max_discount=data['max_discount'], is_percentage=False, is_point=True)
            coupon_code = "get " + discount_value_str + " points on orders above ₹" + discount_amount_str
            rule_set_name_with_shop_id = str(shop_id) + "_" + coupon_code
        else:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value, is_percentage=False)
            coupon_code = "₹" + discount_value_str + " off on orders above ₹" + discount_amount_str
            rule_set_name_with_shop_id = str(shop_id) + "_" + coupon_code

        coupon_obj = OffersCls.rule_set_creation(rule_set_name_with_shop_id, start_date, expiry_date, discount_amount,
                                                 discount_obj)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)
        else:
            coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', data['coupon_name'], coupon_code, shop,
                                                     start_date, expiry_date, data.get('limit_of_usages_per_customer', None))
            data['id'] = coupon.id
            coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get('coupon_enable_on') else 'all'
            coupon.froms = data.get('froms') if data.get('froms') else 0
            coupon.to = data.get('to') if data.get('to') else 0
            coupon.category = data.get('category') if data.get('category') else []
            coupon.save()
            data['coupon_enable_on'] = coupon.coupon_enable_on
            return api_response("Coupon Offer has been created successfully!", data, status.HTTP_200_OK, True)

    @staticmethod
    def create_combo_offer(data, shop_id):
        """
            Buy X Get Y Free
        """
        shop = Shop.objects.filter(id=shop_id).last()
        retailer_primary_product = data['primary_product_id']
        try:
            retailer_primary_product_obj = RetailerProduct.objects.get(~Q(sku_type=4), id=retailer_primary_product,
                                                                       shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Primary product not found")
        retailer_free_product = data['free_product_id']
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=retailer_free_product, shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Free product not found")

        combo_offer_name, start_date, expiry_date, purchased_product_qty, free_product_qty = data['coupon_name'], data[
            'start_date'], data['end_date'], data['primary_product_qty'], data['free_product_qty']
        offer = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                     retailer_primary_product=retailer_primary_product_obj,
                                                     rule__coupon_ruleset__is_active=True)
        if offer:
            return api_response("Offer already exists for this Primary Product")

        offer = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                     retailer_primary_product=retailer_free_product_obj,
                                                     rule__coupon_ruleset__is_active=True)

        if offer and offer[0].retailer_free_product.id == data['primary_product_id']:
            return api_response("Offer already exists for this Primary Product as a free product for same free product")

        combo_code = f"Buy {purchased_product_qty} {retailer_primary_product_obj.name}" \
                     f" + Get {free_product_qty} {retailer_free_product_obj.name} Free"
        combo_rule_name = str(shop_id) + "_" + combo_code
        coupon_obj = OffersCls.rule_set_creation(combo_rule_name, start_date, expiry_date)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)

        OffersCls.rule_set_product_mapping(coupon_obj.id, retailer_primary_product_obj, purchased_product_qty,
                                           retailer_free_product_obj, free_product_qty, combo_offer_name, start_date,
                                           expiry_date)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'catalog', combo_offer_name, combo_code, shop,
                                                 start_date, expiry_date, data.get('limit_of_usages_per_customer',None))
        data['id'] = coupon.id
        coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get('coupon_enable_on') else 'all'
        coupon.froms = data.get('froms') if data.get('froms') else 0
        coupon.to = data.get('to') if data.get('to') else 0
        coupon.category = data.get('category') if data.get('category') else []
        coupon.save()
        data['coupon_enable_on'] = coupon.coupon_enable_on
        return api_response("Combo Offer has been created successfully!", data, status.HTTP_200_OK, True)

    @staticmethod
    def create_free_product_offer(data, shop_id):
        """
            Cart Free Product
        """
        shop, free_product = Shop.objects.filter(id=shop_id).last(), data['free_product_id']
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=free_product, shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Free product not found")

        coupon_name, discount_amount, start_date, expiry_date, free_product_qty = data['coupon_name'], data[
            'order_value'], data['start_date'], data['end_date'], data['free_product_qty']
        coupon_rule_discount_amount = Coupon.objects.filter(rule__cart_qualifying_min_sku_value=discount_amount,
                                                            shop=shop_id, rule__coupon_ruleset__is_active=True)
        if coupon_rule_discount_amount:
            return api_response(f"Offer already exists for Order Value {discount_amount}")

        coupon_rule_product_qty = Coupon.objects.filter(rule__free_product=retailer_free_product_obj,
                                                        rule__free_product_qty=free_product_qty,
                                                        shop=shop_id, rule__coupon_ruleset__is_active=True)
        if coupon_rule_product_qty:
            return api_response("Offer already exists for same quantity of free product")

        discount_amount_str = str(discount_amount).rstrip('0').rstrip('.')
        coupon_code = str(free_product_qty) + " " + str(
            retailer_free_product_obj.name) + " free on orders above ₹" + discount_amount_str
        rule_name = str(shop_id) + "_" + coupon_code
        coupon_obj = OffersCls.rule_set_creation(rule_name, start_date, expiry_date, discount_amount, None,
                                                 retailer_free_product_obj, free_product_qty)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', coupon_name, coupon_code, shop, start_date,
                                                 expiry_date, data.get('limit_of_usages_per_customer',None))
        coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get('coupon_enable_on') else 'all'
        coupon.froms = data.get('froms') if data.get('froms') else 0
        coupon.to = data.get('to') if data.get('to') else 0
        coupon.category = data.get('category') if data.get('category') else []
        coupon.save()
        data['coupon_enable_on'] = coupon.coupon_enable_on
        data['id'] = coupon.id
        return api_response("Free Product Offer has been created successfully!", data, status.HTTP_200_OK, True)

    @staticmethod
    def update_coupon(data, shop_id, success_msg):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Coupon Id Invalid")
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            error_logger.error("Coupon RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Coupon RuleSet not found")

        coupon.coupon_name = data['coupon_name'] if 'coupon_name' in data else coupon.coupon_name
        if 'start_date' in data:
            rule.start_date = coupon.start_date = data['start_date']
        if 'end_date' in data:
            rule.expiry_date = coupon.expiry_date = data['end_date']
        if 'is_active' in data:
            rule.is_active = coupon.is_active = data['is_active']
        rule.save()
        coupon.limit_of_usages_per_customer = data.get('limit_of_usages_per_customer',coupon.limit_of_usages_per_customer)
        coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get('coupon_enable_on') else coupon.coupon_enable_on
        coupon.save()
        return api_response(success_msg, None, status.HTTP_200_OK, True)

    @staticmethod
    def update_combo(data, shop_id, success_msg):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Coupon Id Invalid")
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            error_logger.error("Coupon RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Coupon RuleSet not found")
        try:
            rule_set_product_mapping = RuleSetProductMapping.objects.get(rule=coupon.rule)
        except ObjectDoesNotExist:
            error_logger.error("Product RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Product mapping Not Found with Offer")

        if 'coupon_name' in data:
            coupon.coupon_name = rule_set_product_mapping.combo_offer_name = data['coupon_name']
        if 'start_date' in data:
            rule.start_date = rule_set_product_mapping.start_date = coupon.start_date = data['start_date']
        if 'end_date' in data:
            rule.expiry_date = rule_set_product_mapping.expiry_date = coupon.expiry_date = data['end_date']
        if 'is_active' in data:
            rule_set_product_mapping.is_active = rule.is_active = coupon.is_active = data['is_active']
        rule.save()
        rule_set_product_mapping.save()
        coupon.limit_of_usages_per_customer = data.get('limit_of_usages_per_customer',coupon.limit_of_usages_per_customer)
        coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get(
            'coupon_enable_on') else coupon.coupon_enable_on
        coupon.save()
        return api_response(success_msg, None, status.HTTP_200_OK, True)

    @staticmethod
    def update_free_product_offer(data, shop_id, success_msg):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Coupon Id Invalid")
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            error_logger.error("Coupon RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Coupon RuleSet not found")

        coupon.coupon_name = data['coupon_name'] if 'coupon_name' in data else coupon.coupon_name
        if 'start_date' in data:
            rule.start_date = coupon.start_date = data['start_date']
        if 'expiry_date' in data:
            rule.expiry_date = coupon.expiry_date = data['end_date']
        if 'is_active' in data:
            rule.is_active = coupon.is_active = data['is_active']
        rule.save()
        coupon.limit_of_usages_per_customer = data.get('limit_of_usages_per_customer',coupon.limit_of_usages_per_customer)
        coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get(
            'coupon_enable_on') else coupon.coupon_enable_on
        coupon.save()
        return api_response(success_msg, None, status.HTTP_200_OK, True)


class InventoryReport(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
            Get Products Available Inventory report for shop
        """
        shop = kwargs['shop']
        if request.GET.get('product_id'):
            return self.product_inventory_log(shop, request.GET.get('search_text'), request.GET.get('product_id'))
        else:
            return self.inventory_list(shop, request.GET.get('search_text'))

    def inventory_list(self, shop, search_text):
        inv_available = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        inv = PosInventory.objects.filter(product__shop=shop, inventory_state=inv_available)

        # Search by product name
        if search_text:
            inv = inv.filter(product__name__icontains=search_text)

        inv = inv.order_by('-modified_at')
        objects = self.pagination_class().paginate_queryset(inv, self.request)
        data = InventoryReportSerializer(objects, many=True).data
        msg = "Inventory Report Fetched Successfully!" if data else "No Product Inventory Found For This Shop!"
        return api_response(msg, data, status.HTTP_200_OK, True)

    def product_inventory_log(self, shop, search_text, pk):
        # Validate product
        try:
            product = RetailerProduct.objects.get(pk=pk, shop=shop)
        except ObjectDoesNotExist:
            return api_response("Product Id Invalid")

        # Inventory
        inv_available = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        inv = PosInventory.objects.filter(product=product, inventory_state=inv_available).last()
        inv_data = InventoryReportSerializer(inv).data

        # Inventory Logs
        logs = PosInventoryChange.objects.filter(product_id=pk)

        # Search
        # if search_text:
        #     logs = logs.filter(Q(transaction_type__icontains=search_text) | Q(transaction_id__icontains=search_text))
        logs = logs.order_by('-modified_at')
        objects = self.pagination_class().paginate_queryset(logs, self.request)
        logs_data = InventoryLogReportSerializer(objects, many=True).data

        # Merge data
        data = dict()
        data['product_inventory'] = inv_data
        data['logs'] = logs_data
        return api_response("Inventory Log Report Fetched Successfully!", data, status.HTTP_200_OK, True)


class SalesReport(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
        Get Sales Report for a POS shop
        """
        # Validate input
        serializer = SalesReportSerializer(data=request.GET)
        if not serializer.is_valid():
            return api_response(serializer_error(serializer))

        # Generate daily, monthly OR Invoice wise report
        request_data, shop = serializer.data, kwargs['shop']
        report_type = request_data['report_type']

        if report_type == 'daily':
            return self.daily_report(shop, report_type, request_data)
        # elif report_type == 'monthly':
        #     return self.monthly_report(shop, report_type, request_data)
        # else:
        #     return self.invoice_report(shop, report_type, request_data)

    def invoice_report(self, shop, report_type, request_data):
        # Shop Filter
        qs = OrderedProduct.objects.select_related('order', 'invoice').filter(order__seller_shop=shop)

        # Date / Date Range Filter
        date_filter = request_data['date_filter']
        if date_filter:
            qs = self.filter_by_date_filter(date_filter, qs)
        else:
            start_date = datetime.datetime.strptime(request_data['start_date'], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(request_data['end_date'], '%Y-%m-%d')
            qs = qs.filter(created_at__date__gte=start_date.date, created_at__date__lte=end_date.date)

        # Sale, returns, effective sale for all orders
        qs = qs.annotate(sale=F('order__order_amount'))
        qs = qs.annotate(returns=Coalesce(Sum('order__rt_return_order__refund_amount',
                                              filter=Q(order__rt_return_order__status='completed')), 0))
        qs = qs.annotate(effective_sale=F('sale') - F('returns'), invoice_no=F('invoice__invoice_no'))
        data = qs.values('sale', 'returns', 'effective_sale', 'created_at__date', 'invoice_no')

        return self.get_response(report_type, data, request_data['sort_by'], request_data['sort_order'])

    def daily_report(self, shop, report_type, request_data):
        # Get start date and end date based on offset and limit
        offset, limit = request_data['offset'], request_data['limit']
        date_today = datetime.datetime.today()
        end_date = date_today - datetime.timedelta(days=offset)
        start_date = end_date - datetime.timedelta(days=limit - 1)

        # Filter Orders for sales
        # Shop Filter
        qss = Order.objects.filter(seller_shop=shop).exclude(order_status='CANCELLED')
        # Date Filter
        qss = qss.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        # Sale, order count
        qss = qss.values('created_at__date').annotate(sale=Sum('order_amount'), order_count=Coalesce(Count('id'), 0))
        sales_data = qss.values('sale', 'order_count', 'created_at__date', effective_sale=F('sale')).order_by(
            '-created_at__date')

        # Filter returns for returns
        # Shop Filter
        qsr = OrderReturn.objects.filter(order__seller_shop=shop, status='completed')
        # Date Filter
        qsr = qsr.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        # Returns
        qsr = qsr.values('created_at__date').annotate(
            returns=Coalesce(Sum('refund_amount', filter=Q(refund_amount__gt=0)), 0))
        returns_data = qsr.values('returns', 'created_at__date')

        # Merge sales and returns
        result_set = self.get_default_result_set(limit, end_date)
        for sale in sales_data:
            key = str(sale['created_at__date'])
            sale['date'] = sale['created_at__date'].strftime("%b %d, %Y")
            del sale['created_at__date']
            result_set[key] = sale
        for ret in returns_data:
            key = str(ret['created_at__date'])
            ret['date'] = ret['created_at__date'].strftime("%b %d, %Y")
            del ret['created_at__date']
            result_set[key].update(ret)
            result_set[key]['effective_sale'] = result_set[key]['effective_sale'] - ret['returns']
        report_type = report_type.capitalize()
        msg = report_type + ' Sales Report Fetched Successfully!'
        return api_response(msg, result_set.values(), status.HTTP_200_OK, True)

    @staticmethod
    def get_default_result_set(limit, end_date):
        result_set = dict()
        for i in range(0, limit):
            date = end_date - datetime.timedelta(days=i)
            date = date.date()
            result_set[str(date)] = {'sale': 0, 'order_count': 0, 'effective_sale': 0, 'returns': 0,
                                     'date': date.strftime("%b %d, %Y")}
        return result_set

    def daily_report_prev(self, shop, report_type, request_data):
        # Shop Filter
        qs = Order.objects.prefetch_related('rt_return_order').filter(seller_shop=shop)

        # Date / Date Range Filter
        date_filter = request_data['date_filter']
        if date_filter:
            qs = self.filter_by_date_filter(date_filter, qs)
        else:
            start_date = datetime.datetime.strptime(request_data['start_date'], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(request_data['end_date'], '%Y-%m-%d')
            qs = qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        # Sale, returns, effective sale for all days
        qs = qs.values('created_at__date').annotate(sale=Sum('order_amount'))
        qs = qs.annotate(order_count=Coalesce(Count('id'), 0))
        qs = qs.annotate(returns=Coalesce(Sum('rt_return_order__refund_amount'), 0))
        qs = qs.annotate(effective_sale=F('sale') - F('returns')).order_by('created_at__date')
        data = qs.values('sale', 'returns', 'effective_sale', 'order_count', 'created_at__date')

        return self.get_response(report_type, data, request_data['sort_by'], request_data['sort_order'])

    def monthly_report(self, shop, report_type, request_data):
        # Shop Filter
        qs = Order.objects.prefetch_related('rt_return_order').filter(seller_shop=shop)

        # Date / Date Range Filter
        date_filter = request_data['date_filter']
        if date_filter:
            qs = self.filter_by_date_filter(date_filter, qs)
        else:
            start_date = datetime.datetime.strptime(request_data['start_date'], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(request_data['end_date'], '%Y-%m-%d')
            qs = qs.filter(created_at__month__gte=start_date.month, created_at__month__lte=end_date.month)

        # Sale, returns, effective sale for all months
        qs = qs.values('created_at__month').annotate(sale=Sum('order_amount'))
        qs = qs.annotate(order_count=Coalesce(Count('id'), 0))
        qs = qs.annotate(returns=Coalesce(Sum('rt_return_order__refund_amount'), 0))
        qs = qs.annotate(effective_sale=F('sale') - F('returns')).order_by('created_at__month')
        data = qs.values('sale', 'returns', 'effective_sale', 'order_count', 'created_at__month', 'created_at__year')

        return self.get_response(report_type, data, request_data['sort_by'], request_data['sort_order'])

    @staticmethod
    def filter_by_date_filter(date_filter, qs):
        date_today = datetime.datetime.today()
        if date_filter == 'today':
            qs = qs.filter(created_at__date=date_today)
        elif date_filter == 'yesterday':
            date_yesterday = date_today - datetime.timedelta(days=1)
            qs = qs.filter(created_at__date=date_yesterday)
        elif date_filter == 'this_week':
            qs = qs.filter(created_at__week=date_today.isocalendar()[1])
        elif date_filter == 'last_week':
            last_week = date_today - datetime.timedelta(weeks=1)
            qs = qs.filter(created_at__week=last_week.isocalendar()[1])
        elif date_filter == 'this_month':
            qs = qs.filter(created_at__month=date_today.month)
        elif date_filter == 'last_month':
            last_month = date_today - datetime.timedelta(days=30)
            qs = qs.filter(created_at__month=last_month.month)
        elif date_filter == 'this_year':
            qs = qs.filter(created_at__year=date_today.year)
        return qs

    @staticmethod
    def sort(sort_by, sort_order, invoices):
        sort_by = '-' + sort_by if sort_order == -1 else sort_by
        return invoices.order_by(sort_by)

    def get_response(self, report_type, data, sort_by, sort_order):
        # Sort
        data = self.sort(sort_by, sort_order, data)
        # Paginate
        data = self.pagination_class().paginate_queryset(data, self.request)
        # Serialize
        data = SalesReportResponseSerializer(data, many=True).data
        # Return HTTP Response
        report_type = report_type.capitalize()
        msg = report_type + ' Sales Report Fetched Successfully!' if data else 'No Sales Found For Selected Filters!'
        return api_response(msg, data, status.HTTP_200_OK, True)


class CustomerReport(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
        Get Customer Report for a POS shop
        """
        # Validate input
        serializer = CustomerReportSerializer(data=request.GET)
        if not serializer.is_valid():
            return api_response(serializer_error(serializer))

        request_data, shop = serializer.data, kwargs['shop']
        if request.GET.get('phone_number'):
            return self.customer_order_log(shop, request.GET.get('search_text'), request.GET.get('phone_number'),
                                           request_data)
        else:
            return self.customer_list(shop, request.GET.get('search_text'), request_data)

    def customer_order_log(self, shop, search_text, phone_no, request_data):
        # Validate customer
        try:
            shop_user_map = ShopCustomerMap.objects.get(user__phone_number=phone_no, shop=shop)
        except ObjectDoesNotExist:
            return api_response("Phone Number Invalid For This Shop!")

        qs = Order.objects.filter(buyer_id=shop_user_map.user_id, seller_shop_id=shop_user_map.shop_id)

        # Date / Date Range Filter
        date_filter = request_data['date_filter']
        if date_filter:
            qs = self.filter_by_date_filter(date_filter, qs)
        # else:
        #     start_date = datetime.datetime.strptime(request_data['start_date'], '%Y-%m-%d')
        #     end_date = datetime.datetime.strptime(request_data['end_date'], '%Y-%m-%d')
        #     qs = qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        # Loyalty points added, redeemed, order value, return value
        qs = qs.values('id', 'created_at__date', 'points_added', order_id=F('order_no'),
                       points_redeemed=F('ordered_cart__redeem_points'),
                       sale=F('order_amount')).annotate(
            returns=Coalesce(Sum('rt_return_order__refund_amount', filter=Q(rt_return_order__status='completed') and Q(
                rt_return_order__refund_amount__gt=0)), 0))
        qs = qs.annotate(effective_sale=F('sale') - F('returns'))

        # Search
        if search_text:
            qs = qs.filter(Q(order_no__icontains=search_text))

        # Sort
        sort_by = '-' + request_data['sort_by'] if request_data['sort_order'] == -1 else request_data['sort_by']
        qs = qs.order_by(sort_by)

        # Paginate
        data = self.pagination_class().paginate_queryset(qs, self.request)
        # Serialize
        data = CustomerReportDetailResponseSerializer(data, many=True).data
        msg = 'Customer Orders Report Fetched Successfully!' if data else 'No Orders Found For Selected Filters!'
        return api_response(msg, data, status.HTTP_200_OK, True)

    def customer_list(self, shop, search_text, request_data):
        # Shop Filter
        qs = ShopCustomerMap.objects.filter(shop=shop)

        # Date / Date Range Filter
        date_filter = request_data['date_filter']
        if date_filter:
            qs = self.filter_by_date_filter(date_filter, qs)
        # else:
        #     start_date = datetime.datetime.strptime(request_data['start_date'], '%Y-%m-%d')
        #     end_date = datetime.datetime.strptime(request_data['end_date'], '%Y-%m-%d')
        #     qs = qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        # Loyalty points, sale, returns, effective sale for all users for shop
        qs = qs.annotate(loyalty_points=Coalesce(F('user__reward_user_mlm__direct_earned') - F(
            'user__reward_user_mlm__indirect_earned') - F('user__reward_user_mlm__points_used'), 0))
        qs = qs.annotate(sale=Coalesce(Subquery(
            Order.objects.filter(buyer=OuterRef('user'), seller_shop=shop).values('buyer').annotate(
                sale=Sum('order_amount')).order_by('buyer').values('sale')), 0))
        qs = qs.annotate(order_count=Coalesce(Subquery(
            Order.objects.filter(buyer=OuterRef('user'), seller_shop=shop).values('buyer').annotate(
                order_count=Count('id')).order_by('buyer').values('order_count')), 0))
        qs = qs.annotate(returns=Coalesce(Subquery(
            OrderReturn.objects.filter(order__buyer=OuterRef('user'), order__seller_shop=shop).values(
                'order__buyer').annotate(
                returns=Sum('refund_amount', filter=Q(refund_amount__gt=0) and Q(status='completed'))).order_by(
                'order__buyer').values('returns')), 0))
        qs = qs.annotate(effective_sale=ExpressionWrapper(F('sale') - F('returns'), output_field=FloatField()))
        qs = qs.filter(order_count__gt=0)
        qs = qs.values('order_count', 'sale', 'returns', 'effective_sale', 'created_at', 'loyalty_points',
                       'user__first_name', 'user__last_name', phone_number=F('user__phone_number'),
                       date=F('created_at'))

        # Search
        if search_text:
            qs = qs.filter(Q(user__first_name__icontains=search_text) | Q(user__first_name__icontains=search_text) |
                           Q(phone_number__icontains=search_text))

        # Sort
        sort_by = '-' + request_data['sort_by'] if request_data['sort_order'] == -1 else request_data['sort_by']
        qs = qs.order_by(sort_by)

        # Paginate
        data = self.pagination_class().paginate_queryset(qs, self.request)
        # Serialize
        data = CustomerReportResponseSerializer(data, many=True).data
        msg = 'Customer Sales Report Fetched Successfully!' if data else 'No Customers Added For Selected Filters!'
        return api_response(msg, data, status.HTTP_200_OK, True)

    @staticmethod
    def filter_by_date_filter(date_filter, qs):
        date_today = datetime.datetime.today()
        if date_filter == 'today':
            qs = qs.filter(created_at__date=date_today)
        elif date_filter == 'yesterday':
            date_yesterday = date_today - datetime.timedelta(days=1)
            qs = qs.filter(created_at__date=date_yesterday)
        elif date_filter == 'this_week':
            qs = qs.filter(created_at__week=date_today.isocalendar()[1])
        elif date_filter == 'last_week':
            last_week = date_today - datetime.timedelta(weeks=1)
            qs = qs.filter(created_at__week=last_week.isocalendar()[1])
        elif date_filter == 'this_month':
            qs = qs.filter(created_at__month=date_today.month)
        elif date_filter == 'last_month':
            last_month = date_today - datetime.timedelta(days=30)
            qs = qs.filter(created_at__month=last_month.month)
        elif date_filter == 'this_year':
            qs = qs.filter(created_at__year=date_today.year)
        return qs


class VendorView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = VendorSerializer

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        vendor_obj = Vendor.objects.filter(retailer_shop=kwargs['shop'], id=kwargs['pk']).last()
        if vendor_obj:
            return api_response('', self.serializer_class(vendor_obj).data, status.HTTP_200_OK, True)
        else:
            return api_response("Vendor not found")

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post(self, request, *args, **kwargs):
        data = request.data
        data['retailer_shop'] = kwargs['shop'].id
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return api_response('Vendor created successfully!', serializer.data, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    @pos_check_permission_delivery_person
    def put(self, request, *args, **kwargs):
        data = request.data
        data['id'] = kwargs['pk']
        serializer = self.serializer_class(data=data,
                                           context={'user': self.request.user, 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.update(kwargs['pk'], serializer.data)
            return api_response('Vendor updated Successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))


class VendorListView(ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination
    serializer_class = VendorListSerializer
    shop = None

    def get_queryset(self):
        queryset = Vendor.objects.filter(retailer_shop=self.shop).order_by('-modified_at')

        vendor_status = self.request.GET.get('status', None)
        if vendor_status in ['1', '0']:
            queryset = queryset.filter(status=int(vendor_status))

        search_text = self.request.GET.get('search_text', None)
        if search_text:
            queryset = queryset.filter(Q(company_name__icontains=search_text) | Q(vendor_name__icontains=search_text)
                                       | Q(contact_person_name__icontains=search_text)
                                       | Q(phone_number__icontains=search_text))
        return queryset

    @check_pos_shop
    def list(self, request, *args, **kwargs):
        self.shop = kwargs['shop']
        queryset = self.pagination_class().paginate_queryset(self.get_queryset(), self.request)
        serializer = self.get_serializer(queryset, many=True)
        return api_response('', serializer.data, status.HTTP_200_OK, True)


class POView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = POSerializer

    def get_serializer_context(self):
        context = super(POView, self).get_serializer_context()
        search_text = self.request.GET.get('search_text', None)
        context.update({"search_text": search_text, "request": self.request})
        return context

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        cart = PosCart.objects.filter(retailer_shop=kwargs['shop'], id=kwargs['pk']).prefetch_related(
            'po_products').last()
        if cart:
            return api_response('', POGetSerializer(
                cart, context=self.get_serializer_context()).data, status.HTTP_200_OK, True)
        else:
            return api_response("Purchase Order not found")

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'user': self.request.user, 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.save()
            return api_response('Purchase Order created successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    @pos_check_permission_delivery_person
    def put(self, request, *args, **kwargs):
        data = request.data
        data['id'] = kwargs['pk']
        serializer = self.serializer_class(data=data,
                                           context={'user': self.request.user, 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.update(kwargs['pk'], serializer.data)
            return api_response('Purchase Order updated successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))


class POProductInfoView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = POProductInfoSerializer

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        product = RetailerProduct.objects.filter(shop=kwargs['shop'], id=kwargs['pk']).last()
        if product:
            return api_response('', self.serializer_class(product).data, status.HTTP_200_OK, True)
        else:
            return api_response("Product not found")


class POListView(ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = OffsetPaginationDefault50
    serializer_class = POListSerializer
    shop = None

    def get_queryset(self):
        queryset = PosCart.objects.filter(retailer_shop=self.shop).order_by('-modified_at').prefetch_related(
            'po_products')

        search_text = self.request.GET.get('search_text', None)
        if search_text:
            queryset = queryset.filter(Q(vendor__company_name__icontains=search_text)
                                       | Q(vendor__vendor_name__icontains=search_text)
                                       | Q(vendor__contact_person_name__icontains=search_text)
                                       | Q(vendor__phone_number__icontains=search_text)
                                       | Q(po_no__icontains=search_text))
        return queryset

    @check_pos_shop
    def list(self, request, *args, **kwargs):
        self.shop = kwargs['shop']
        queryset = self.pagination_class().paginate_queryset(self.get_queryset(), self.request)
        serializer = self.get_serializer(queryset, many=True)
        return api_response('', serializer.data, status.HTTP_200_OK, True)


class GrnOrderView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        grn_order = PosGRNOrder.objects.filter(order__ordered_cart__retailer_shop=kwargs['shop'],
                                               id=kwargs['pk']).prefetch_related('po_grn_products').last()
        if grn_order:
            return api_response('', GrnOrderGetSerializer(grn_order).data, status.HTTP_200_OK, True)
        else:
            return api_response("GRN Order not found")

    @check_pos_shop
    @pos_check_permission_delivery_person
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(self.request.data["data"])
        except:
            return api_response("Invalid Data Format")
        data['invoice'] = request.FILES.get('invoice')
        serializer = PosGrnOrderCreateSerializer(data=data,
                                                 context={'user': self.request.user, 'shop': kwargs['shop']})
        if serializer.is_valid():
            s_data = serializer.data
            s_data['invoice'] = data['invoice']
            serializer.create(s_data)
            return api_response('GRN created successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    @pos_check_permission_delivery_person
    def put(self, request, *args, **kwargs):
        try:
            data = json.loads(self.request.data["data"])
        except:
            return api_response("Invalid Data Format")
        data['invoice'] = request.FILES.get('invoice')
        data['grn_id'] = kwargs['pk']
        serializer = PosGrnOrderUpdateSerializer(data=data,
                                                 context={'user': self.request.user, 'shop': kwargs['shop']})
        if serializer.is_valid():
            s_data = serializer.data
            s_data['invoice'] = data['invoice']
            serializer.update(kwargs['pk'], s_data)
            return api_response('GRN updated successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))


class GrnOrderListView(ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination
    serializer_class = GrnListSerializer
    shop = None

    def get_queryset(self):
        queryset = PosGRNOrder.objects.filter(order__ordered_cart__retailer_shop=self.shop).order_by('-modified_at')
        return queryset

    @check_pos_shop
    def list(self, request, *args, **kwargs):
        self.shop = kwargs['shop']
        queryset = self.pagination_class().paginate_queryset(self.get_queryset(), self.request)
        serializer = self.get_serializer(queryset, many=True)
        return api_response('', serializer.data, status.HTTP_200_OK, True)


class PaymentTypeDetailView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = PaymentType.objects.filter(app__in=['pos', 'both'])
    serializer_class = PaymentTypeSerializer

    def get(self, request):
        """ GET Payment Type List """
        payment_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(payment_type, many=True)
        msg = "" if payment_type else "No payment found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)


class EcomPaymentTypeDetailView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = PaymentType.objects.filter(app='ecom')
    serializer_class = PaymentTypeSerializer

    def get(self, request):
        """ GET Payment Type List """
        payment_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(payment_type, many=True)
        msg = "" if payment_type else "No payment found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)


class IncentiveView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        msg = "There  will  be  a  1%  incentive  for  billing  done  from  Rs 50000  to  Rs 500000  for  a  calendar  month."
        return api_response(msg, None, status.HTTP_200_OK, True)
        # Get start date and end date based on offset and limit
        # offset, limit = int(self.request.GET.get('offset', 0)), min(5, int(self.request.GET.get('limit', 5)))
        # date_today = datetime.datetime.today()
        # month, year = date_today.month, date_today.year
        # month_range = calendar.monthrange(year, month)[1]
        # end_date = date_today - datetime.timedelta(days=offset * month_range)
        # start_date = end_date - datetime.timedelta(days=(limit - 1) * month_range)
        # start_month, start_year, end_month, end_year = start_date.month, start_date.year, end_date.month, end_date.year
        #
        # # Default result set
        # result_set = self.get_default_result_set(limit, month_range, end_date)
        #
        # # SALES
        # shop = kwargs['shop']
        # qss = Order.objects.filter(seller_shop=shop).exclude(order_status='CANCELLED')
        # qss = self.filter_by_date(qss, start_month, start_year, end_month, end_year)
        # qss = qss.values('created_at__month', 'created_at__year').annotate(sale=Sum('order_amount'))
        # sales_data = qss.values('sale', 'created_at__month', 'created_at__year', effective_sale=F('sale')).order_by(
        #     '-created_at__month', '-created_at__year')
        #
        # # RETURNS
        # qsr = OrderReturn.objects.filter(order__seller_shop=shop, status='completed')
        # qsr = self.filter_by_date(qsr, start_month, start_year, end_month, end_year)
        # qsr = qsr.values('created_at__month', 'created_at__year').annotate(
        #     returns=Coalesce(Sum('refund_amount', filter=Q(refund_amount__gt=0)), 0))
        # returns_data = qsr.values('returns', 'created_at__month', 'created_at__year')
        #
        # # MERGE sales and returns
        # for sale in sales_data:
        #     result_set[str(sale['created_at__month']) + '_' + str(sale['created_at__year'])] = sale
        # for ret in returns_data:
        #     key = str(ret['created_at__month']) + '_' + str(ret['created_at__year'])
        #     if key in result_set:
        #         result_set[key].update(ret)
        #         result_set[key]['effective_sale'] = result_set[key]['effective_sale'] - ret['returns']
        #
        # # Incentive cal
        # incentive_rate = int(get_config('pos_retailer_incentive_rate', 1))
        # for key in result_set:
        #     result_set[key]['month'] = calendar.month_name[result_set[key]['created_at__month']] + ', ' + str(result_set[key]['created_at__year'])
        #     del result_set[key]['created_at__month']
        #     del result_set[key]['created_at__year']
        #     result_set[key]['incentive_rate'] = str(incentive_rate) + '%'
        #     result_set[key]['incentive'] = round((incentive_rate / 100) * result_set[key]['effective_sale'], 2)
        #
        # return api_response('Incentive for shop', result_set.values(), status.HTTP_200_OK, True)

    @staticmethod
    def get_default_result_set(limit, month_range, end_date):
        result_set = dict()
        for i in range(0, limit):
            date = end_date - datetime.timedelta(days=i * month_range)
            month, year = date.month, date.year
            result_set[str(month) + '_' + str(year)] = {"created_at__month": int(month), "created_at__year": int(year),
                                                        "sale": 0, "effective_sale": 0, "returns": 0, "incentive": 0}
        return result_set

    @staticmethod
    def filter_by_date(qs, start_month, start_year, end_month, end_year):
        if start_year != end_year:
            qs = qs.filter(Q(created_at__month__gte=start_month, created_at__year=start_year) |
                           Q(created_at__month__lte=end_month, created_at__year=end_year))
        else:
            qs = qs.filter(created_at__month__gte=start_month, created_at__month__lte=end_month,
                           created_at__year=start_year)
        return qs


class MeasurementCategoryView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = MeasurementCategory.objects.filter(measurement_category_unit__default=True)
    serializer_class = MeasurementCategorySerializer

    def get(self, request):
        measure_cat = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(measure_cat, many=True)
        return api_response('', serializer.data, status.HTTP_200_OK, True)


class GetGrnOrderListView(ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = GrnOrderGetListSerializer
    pagination_class = SmallOffsetPagination

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        grn_order = PosGRNOrder.objects.filter(order__ordered_cart__retailer_shop=kwargs['shop']). \
            order_by('-modified_at')
        if request.GET.get('id'):
            """ Get GRN Order for specific ID """
            id_validation = validate_id(grn_order, int(request.GET.get('id')))
            if 'error' in id_validation:
                return api_response(id_validation['error'])
            grn_order = id_validation['data']

        search_text = self.request.GET.get('search_text')
        # search using PO number, GRN invoice number and product name on criteria that matches
        if search_text:
            grn_order = grn_product_search(grn_order, search_text.strip())
        if grn_order:
            return api_response('', self.serializer_class(
                grn_order, many=True, context={'shop': kwargs['shop']}).data, status.HTTP_200_OK, True)
        else:
            return api_response("GRN Order not found")


class ReturnStatusListView(GenericAPIView):
    """
        Get RETURN Status List
    """
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET Choice List for RETURN Status """

        info_logger.info("RETURN Status GET api called.")
        """ GET Status Choice List """
        fields = ['status', 'return_status', ]
        data = [dict(zip(fields, d)) for d in PosReturnGRNOrder.RETURN_STATUS]
        return api_response("", data, status.HTTP_200_OK, True)


class GrnReturnOrderView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    @check_return_status
    def get(self, request, *args, **kwargs):
        """ GET Return Order List """
        grn_return = PosReturnGRNOrder.objects.filter(
            grn_ordered_id__order__ordered_cart__retailer_shop=kwargs['shop'],
            status=kwargs['status']). \
            prefetch_related('grn_ordered_id', 'grn_ordered_id__po_grn_products', 'grn_order_return', ). \
            select_related('grn_ordered_id', 'last_modified_by', ).order_by('-modified_at')

        if request.GET.get('id'):
            """ Get Return Order for specific ID """
            id_validation = validate_id(grn_return, int(request.GET.get('id')))
            if 'error' in id_validation:
                return api_response(id_validation['error'])
            grn_return = id_validation['data']

        search_text = self.request.GET.get('search_text')
        if search_text:
            grn_return = grn_return_search(grn_return, search_text)

        if grn_return:
            serializer = ReturnGrnOrderSerializer(grn_return, many=True,
                                                  context={'status': kwargs['status'], 'shop': kwargs['shop']})
            return api_response('', serializer.data, status.HTTP_200_OK, True)
        else:
            return api_response("Return GRN Order not found")

    @check_pos_shop
    @check_return_status
    def post(self, request, *args, **kwargs):
        """ Create Return Order """
        serializer = ReturnGrnOrderSerializer(data=request.data,
                                              context={'status': kwargs['status'], 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.save(last_modified_by=request.user)
            return api_response('GRN returned successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    @check_return_status
    def put(self, request, *args, **kwargs):
        """ Update Return Order """
        info_logger.info("Return Order Product PUT api called.")
        if 'id' not in request.data:
            return api_response('please provide id to update return order product', False)

        # validations for input id
        try:
            pos_return_order = PosReturnGRNOrder.objects.filter(grn_ordered_id__order__ordered_cart__retailer_shop=
                                                                kwargs['shop'])
            id_instance = pos_return_order.get(id=int(request.data['id']))
        except:
            return api_response('please provide a valid id')
        serializer = ReturnGrnOrderSerializer(instance=id_instance, data=request.data,
                                              context={'status': kwargs['status'], 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.save(last_modified_by=request.user)
            return api_response('GRN returned updated successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))


class PRNwithoutGRNView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    @check_return_status
    def get(self, request, *args, **kwargs):
        """ GET PRN List for without GRN Products"""
        return_products = PosReturnGRNOrder.objects.filter(
            vendor_id__retailer_shop=kwargs['shop'],
            status=kwargs['status']).prefetch_related('grn_ordered_id', 'vendor_id', 'grn_order_return', ). \
            select_related('last_modified_by', ).order_by('-modified_at')

        if request.GET.get('id'):
            """ Get PRN for specific ID """
            id_validation = validate_id(return_products, int(request.GET.get('id')))
            if 'error' in id_validation:
                return api_response(id_validation['error'])
            return_products = id_validation['data']

        search_text = self.request.GET.get('search_text')
        if search_text:
            return_products = non_grn_return_search(return_products, search_text)

        if return_products:
            serializer = PRNOrderSerializer(return_products, many=True,
                                            context={'status': kwargs['status'], 'shop': kwargs['shop']})
            return api_response('', serializer.data, status.HTTP_200_OK, True)
        else:
            return api_response("PRN not found")

    @check_pos_shop
    @check_return_status
    def post(self, request, *args, **kwargs):
        """ Create PRN for non GRN Products """
        serializer = PRNOrderSerializer(data=request.data,
                                        context={'status': kwargs['status'], 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.save(last_modified_by=request.user)
            return api_response('PRN created successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    @check_return_status
    def put(self, request, *args, **kwargs):
        """ Update PRN for non GRN Products """
        info_logger.info("Return PRN PUT api called.")
        if 'id' not in request.data:
            return api_response('please provide id to update return product', False)

        # validations for input id
        try:
            pos_return_order = PosReturnGRNOrder.objects.filter(vendor_id__retailer_shop=kwargs['shop'])
            id_instance = pos_return_order.get(id=int(request.data['id']))
        except:
            return api_response('please provide a valid id')
        serializer = PRNOrderSerializer(instance=id_instance, data=request.data,
                                        context={'status': kwargs['status'], 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.save(last_modified_by=request.user)
            return api_response('PRN updated successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))


class ShopSpecificationView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        shop = kwargs['shop']
        return api_response("", {"enable_online_inventory": shop.online_inventory_enabled}, status.HTTP_200_OK, True)

    @check_pos_shop
    def post(self, request, *args, **kwargs):
        # Enable inventory for online orders
        enable_online_inventory = self.request.data.get('enable_online_inventory', None)
        if enable_online_inventory not in [True, False]:
            return api_response("Invalid request")

        Shop.objects.filter(id=kwargs['shop'].id).update(online_inventory_enabled=enable_online_inventory)
        msg = "Enabled Online Inventory Check" if enable_online_inventory else "Disabled Online Inventory Check"
        return api_response(msg, None, status.HTTP_200_OK, True)


class StockUpdateReasonListView(GenericAPIView):
    """
        Get Stock Update Reason List
    """
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET Choice List for Stock update reason """

        fields = ['key', 'value', ]
        data = [dict(zip(fields, d)) for d in PosInventoryChange.REMARKS_CHOICES]
        return api_response("", data, status.HTTP_200_OK, True)


class CreateBulkProductView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = BulkRetailerProduct.objects.all()
    serializer_class = BulkProductUploadSerializers

    @check_pos_shop
    def post(self, request, *args, **kwargs):
        """ POST API for Create/update Bulk Product """
        shop = kwargs['shop']
        info_logger.info("BulkSlabProductPriceView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            success, data = serializer.save(uploaded_by=request.user, seller_shop_id=shop.pk)
            if success:
                data = "Product Uploaded Successfully"
                info_logger.info("CreateBulkProductView upload successfully")
                return api_response(data, success=success, status_code=status.HTTP_200_OK)
            else:
                return api_response(data, success=success)
        return api_response(serializer_error(serializer), False)


class UpdateInventoryStockView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    @check_pos_shop
    def post(self, request, *args, **kwargs):
        """ POST API for Create/update Bulk Product """
        shop = kwargs['shop']
        info_logger.info("UpdateInventoryStockView POST api called.")
        updated_request = request.POST.copy()
        updated_request.update({'shop': shop.id})
        form = RetailerProductsStockUpdateForm(updated_request, request.FILES, shop_id=str(shop.id))
        if form.is_valid():
            reader = csv.reader(codecs.iterdecode(request.FILES.get('file'), 'utf-8', errors='ignore'))
            header = next(reader, None)
            uploaded_data_list = []
            csv_dict = {}
            count = 0
            for id, row in enumerate(reader):
                for ele in row:
                    csv_dict[header[count]] = ele
                    count += 1
                uploaded_data_list.append(csv_dict)
                csv_dict = {}
                count = 0
            stock_update(request, uploaded_data_list)
            info_logger.info("Stock updated successfully")
            return api_response("Stock updated successfully", None, status.HTTP_200_OK, True)
        return api_response(serializer_error(form), False)


class Contect_Us(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request, format=None):
        phone_no = "989-989-9551"
        obj = GlobalConfig.objects.filter(key='contect_us_pos_phone').last()
        if obj:
            phone_no = obj.value
        email = "partners@peppertap.in"
        obj = GlobalConfig.objects.filter(key='contect_us_pos_email').last()
        if obj:
            email = obj.value

        data = {'phone_number': phone_no,'email' : email}
        serializer = ContectUs(data=data)
        if serializer.is_valid():
            return api_response('contct us details', serializer.data, status.HTTP_200_OK, True)


class PaymentStatusList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get payment status list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in Payment.PAYMENT_STATUS]
        return api_response('', data, status.HTTP_200_OK, True)


class PaymentModeChoicesList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        '''
        API to get payment mode choices list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in Payment.MODE_CHOICES]
        return api_response('', data, status.HTTP_200_OK, True)


class RefundPayment(GenericAPIView):
    """Refund payment api"""
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    @check_pos_shop
    def post(self, request, *args, **kwargs):
        """Create refund ..............."""
        data = request.data
        trxn_id = data.get('trxn_id')
        if not trxn_id:
            return api_response('transaction id must be', '', status.HTTP_200_OK, False)
        payment_datails = Payment.objects.filter(transaction_id=trxn_id,
                                                          payment_status__in=["payment_approved", 'double_payment']).first()

        if not payment_datails:
            return api_response('Transaction not Found', '', status.HTTP_200_OK, False)

        if payment_datails.is_refund and (payment_datails.refund_status != 'failure'):
            return api_response(f'Refund is already initiated for the selected order', '', status.HTTP_200_OK, False)

        refund_amount = None
        if data.get('amount', None):
            if data.get('amount') > payment_datails.amount:
                return api_response('amount should be less then or equal to transaction amount', '', status.HTTP_200_OK,
                                    True)
            refund_amount = data.get('amount')
        else:
            refund_amount = payment_datails.amount
        payment_id = payment_datails.payment_id

        response = send_request_refund(payment_id, refund_amount)

        if not response.get('status'):
            return api_response('refund request failed', response, status.HTTP_200_OK, False)

        request_id = response.get('request_id')
        payment_datails.is_refund = True
        payment_datails.refund_status = 'queued'
        payment_datails.request_id= request_id
        payment_datails.refund_amount = refund_amount
        payment_datails.save()

        return api_response('refund request successful .....', response, status.HTTP_200_OK, True)


class RetailerProductListViewSet(mixins.ListModelMixin,
                                 mixins.UpdateModelMixin,
                                 viewsets.GenericViewSet):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = RetailerProductListSerializer
    queryset = RetailerProduct.objects.filter(~Q(sku_type=4)).order_by('-created_at')
    pagination_class = SmallOffsetPagination
    
    def list(self, request, *args, **kwargs):
        name_search = request.query_params.get('name_search')
        ean_code = request.query_params.get('ean_code')
        shop_id = request.query_params.get('shop_id')
        if request.user.is_superuser:
            qs = self.queryset.all()
        else:
            qs = self.queryset.filter(shop__pos_shop__user=request.user, 
                                      shop__pos_shop__status=True)
        if name_search:
            qs = qs.filter(name__icontains=name_search)
        
        if ean_code:
            qs = qs.filter(product_ean_code__iexact=ean_code)
        
        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        
        retailer_products = self.pagination_class().paginate_queryset(qs, request)
        
        serializer = self.serializer_class(retailer_products, many=True)
        msg = "success"
        return get_response(msg, serializer.data, True)
    
    def retrieve(self, request, pk):
        if request.user.is_superuser:
            qs = self.queryset.all()
        else:
            qs = self.queryset.filter(shop__pos_shop__user=request.user, 
                                      shop__pos_shop__status=True)
        try:
            qs = qs.get(id=pk)
            serializer = self.serializer_class(qs)
            msg = 'success'
            return get_response(msg, serializer.data, True)
        except RetailerProduct.DoesNotExist:
            error = 'Retailer Product not found.'
            return api_response(error)


class DownloadRetailerProductCsvShopWiseView(GenericAPIView):
    
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DownloadRetailerProductsCsvShopWiseSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            shop_id = request.data.get('shop')
            filename = f"{shop_id}_retailer_products_{datetime.datetime.now()}.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            writer.writerow(
            ['product_id', 'shop_id', 'shop_name', 'product_sku', 'product_name', 'product_image', 'mrp', 'selling_price',
            'linked_product_sku', 'linked_product_image', 'product_ean_code', 'description', 'sku_type',
            'parent_product_id', 'b2b_category', 'b2b_sub_category', 'b2c_category', 'b2c_sub_category', 'brand',
            'sub_brand', 'status', 'quantity', 'discounted_sku', 'discounted_stock', 'discounted_price',
            'product_pack_type', 'measurement_category', 'purchase_pack_size', 'available_for_online_orders',
            'online_order_price', 'is_visible', 'offer_price', 'offer_start_date', 'offer_end_date',
            'initial_purchase_value'])

            product_qs = RetailerProduct.objects.filter(~Q(sku_type=4), shop_id=int(shop_id), is_deleted=False)
            if product_qs.exists():
                retailer_products = product_qs \
                    .prefetch_related('linked_product') \
                    .prefetch_related('linked_product__parent_product__product_type') \
                    .prefetch_related('linked_product__parent_product__parent_brand') \
                    .prefetch_related('linked_product__parent_product__parent_brand__brand_parent') \
                    .prefetch_related('linked_product__parent_product__parent_product_pro_category__category') \
                    .prefetch_related('linked_product__parent_product__parent_product_pro_category__category__category_parent') \
                    .prefetch_related('linked_product__parent_product__parent_product_pro_b2c_category__category') \
                    .prefetch_related('linked_product__parent_product__parent_product_pro_b2c_category__category__category_parent') \
                    .select_related('measurement_category')\
                    .values('id', 'shop', 'shop__shop_name', 'sku', 'name', 'mrp', 'selling_price', 'product_pack_type',
                            'retailer_product_image__image',
                            'purchase_pack_size',
                            'measurement_category__category',
                            'linked_product__product_sku',
                            'product_ean_code', 'description', 'sku_type',
                            'linked_product__parent_product__parent_product_pro_category__category__category_name',
                            'linked_product__parent_product__parent_product_pro_b2c_category__category__category_name',
                            'linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name',
                            'linked_product__parent_product__parent_product_pro_b2c_category__category__category_parent__category_name',
                            'linked_product__parent_product__product_type',
                            'linked_product__parent_product__parent_id',
                            'linked_product__parent_product__parent_brand__brand_name',
                            'linked_product__parent_product__parent_brand__brand_parent__brand_name',
                            'status', 'discounted_product', 'discounted_product__sku', 'online_enabled', 'online_price',
                            'is_deleted', 'offer_price', 'offer_start_date', 'offer_end_date', 'initial_purchase_value')
                product_dict = {}
                discounted_product_ids = []
                for product in retailer_products:
                    product_dict[product['id']] = product
                    if product['discounted_product'] is not None:
                        discounted_product_ids.append(product['discounted_product'])
                product_ids = list(product_dict.keys())
                product_ids.extend(discounted_product_ids)
                inventory = PosInventory.objects.filter(product_id__in=product_ids,
                                                        inventory_state__inventory_state=PosInventoryState.AVAILABLE)
                inventory_data = {i.product_id: i.quantity for i in inventory}
                is_visible = 'False'
                for product_id, product in product_dict.items():
                    retailer_images = RetailerProductImage.objects.filter(product=product['id'])
                    category = product[
                        'linked_product__parent_product__parent_product_pro_category__category__category_parent__category_name']
                    sub_category = product[
                        'linked_product__parent_product__parent_product_pro_category__category__category_name']
                    if not category:
                        category = sub_category
                        sub_category = None

                    b2c_category = product[
                        'linked_product__parent_product__parent_product_pro_b2c_category__category__category_parent__category_name']
                    b2c_sub_category = product[
                        'linked_product__parent_product__parent_product_pro_b2c_category__category__category_name']
                    if not b2c_category:
                        b2c_category = b2c_sub_category
                        b2c_sub_category = None

                    brand = product[
                        'linked_product__parent_product__parent_brand__brand_parent__brand_name']
                    sub_brand = product[
                        'linked_product__parent_product__parent_brand__brand_name']
                    if not brand:
                        brand = sub_brand
                        sub_brand = None
                    discounted_stock = None
                    discounted_price = None
                    if product['discounted_product']:
                        discounted_stock = inventory_data.get(product['discounted_product'], 0)
                        discounted_price = RetailerProduct.objects.filter(id=product['discounted_product']).last().selling_price
                    measurement_category = product['measurement_category__category']
                    if product['online_enabled']:
                        online_enabled = 'Yes'
                    else:
                        online_enabled = 'No'

                    if not product['is_deleted']:
                        is_visible = 'Yes'

                    if PosCartProductMapping.objects.filter(product__id=product['id'], is_grn_done=True,
                                                            cart__retailer_shop__id=product['shop']).exists():
                        po_grn_initial_value = PosCartProductMapping.objects.filter(
                            product__id=product['id'], is_grn_done=True).last()
                        initial_purchase_value = po_grn_initial_value.price * po_grn_initial_value.pack_size
                    else:
                        initial_purchase_value = product['initial_purchase_value'] \
                            if product['initial_purchase_value'] else 0

                    product_image = None
                    linked_product_image = None
                    if retailer_images:
                        product_image = ", ".join([x.image.url for x in retailer_images.all()])

                    if product['linked_product__product_sku']:
                        product_obj = Product.objects.get(product_sku=product['linked_product__product_sku'])
                        linked_product_images = products_image(product_obj)
                        if linked_product_images is not None:
                            linked_product_image = str(linked_product_images)

                        # product_image = str(AWS_MEDIA_URL) + str(product['retailer_product_image__image'])
                    writer.writerow(
                        [product['id'], product['shop'], product['shop__shop_name'], product['sku'], product['name'],
                        product_image,
                        product['mrp'], product['selling_price'], product['linked_product__product_sku'],
                        linked_product_image,
                        product['product_ean_code'], product['description'],
                        RetailerProductCls.get_sku_type(product['sku_type']),
                        product['linked_product__parent_product__parent_id'],
                        category, sub_category, b2c_category, b2c_sub_category, brand, sub_brand, product['status'],
                        inventory_data.get(product_id, 0),
                        product['discounted_product__sku'], discounted_stock, discounted_price, product['product_pack_type'],
                        measurement_category, product['purchase_pack_size'], online_enabled,
                        product['online_price'], is_visible, product['offer_price'], product['offer_start_date'],
                        product['offer_end_date'], initial_purchase_value])
            else:
                writer.writerow(["Products for selected shop doesn't exists"])
            return response
        else:
            errors = [f"{error} :: {serializer.errors[error][0]}" for error in serializer.errors]
            errors = "\n".join(errors)
            return api_response(errors)


class DownloadUploadRetailerProductsCsvSampleFileView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = DownloadUploadRetailerProductsCsvSampleFileSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            shop_id = request.data.get('shop')
            filename = "upload_retailer_products_sample.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            writer.writerow(
            ['product_id', 'shop_id', 'shop_name', 'product_sku', 'product_name', 'mrp', 'selling_price',
            'linked_product_sku', 'product_ean_code', 'description', 'sku_type', 'b2b_category', 'b2b_sub_category',
            'b2c_category', 'b2c_sub_category', 'brand', 'sub_brand', 'status', 'quantity', 'discounted_sku',
            'discounted_stock', 'discounted_price', 'product_pack_type', 'measurement_category', 'purchase_pack_size', 'available_for_online_orders',
            'online_order_price', 'is_visible', 'offer_price', 'offer_start_date', 'offer_end_date',
            'initial_purchase_value'])
            writer.writerow(["", shop_id, "", "", 'Loose Noodles', 12, 10, 'PROPROTOY00000019', 'EAEASDF', 'XYZ', "",
                     "", "", "", "", "", "", 'active', 2, "", "", "", 'loose', 'weight', 1, 'Yes', 11, 'Yes', 9, "2021-11-21",
                     "2021-11-23", 8])
            writer.writerow(["", shop_id, "", "", 'Packed Noodles', 12, 10, 'PROPROTOY00000019', 'EAEASDF', 'XYZ', "",
                            "", "", "", "", 'active', 2, "", "", "", 'packet', '', 1, 'Yes', 11, 'Yes', 9, "2021-11-21",
                            "2021-11-23", 9.5])
            return response
        else:
            errors = [f"{error} :: {serializer.errors[error][0]}" for error in serializer.errors]
            errors = "\n".join(errors)
            return api_response(errors)


class BulkCreateUpdateRetailerProductsView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = BulkCreateUpdateRetailerProductsSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data_file = csv.DictReader(codecs.iterdecode(request.data['file'], 'utf-8', errors='ignore'))
            shop_id = request.data['shop']
            product_serializers = []
            rw = 0
            user = request.user
            for product_data in data_file:
                rw += 1
                if product_data.get('product_id'):
                    product_serializer = UpdateRetailerProductCsvSerializer(product_data.get('product_id'), 
                                                                            data=product_data, context={'user': user, 
                                                                                                        'shop': shop_id})
                else:
                    product_serializer = CreateRetailerProductCsvSerializer(data=product_data, context={'user': user, 
                                                                                                        'shop': shop_id})
                if product_serializer.is_valid():
                    product_serializers.append(product_serializer)
                else:
                    errors = [f"Row {rw+1} :: {error} :: {product_serializer.errors[error][0]}" for error in product_serializer.errors]
                    errors = "\n".join(errors)
                    return api_response(errors)
            for product in product_serializers:
                product.save()
            return get_response("success", '', True)
        else:
            errors = [f"{error} :: {serializer.errors[error][0]}" for error in serializer.errors]
            errors = "\n".join(errors)
            return api_response(errors)


class LinkRetailerProductsBulkUploadCsvSampleView(GenericAPIView): # upload limit 300
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    
    def get(self, request, *args, **kwargs):
        filename = 'link_retailer_products_sample.csv'
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(
            ['shop_id', 'retailer_product_sku', 'retailer_product_name', 'linked_product_sku', 'linked_product_name']
        )
        writer.writerow(
            ['35323', '35323284D5FAB99A6', 'Fruit', 'AFGARFTOY00000001', 'Mango']
        )
        return response


class LinkRetailerProductBulkUploadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = LinkRetailerProductsBulkUploadSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = request.user
            data_file = csv.DictReader(codecs.iterdecode(request.data['file'], 'utf-8', errors='ignore'))
            product_serializers = []
            rw = 0
            for product_data in data_file:
                product_serializer = LinkRetailerProductCsvSerializer(product_data.get('retailer_product_sku'),
                                                                      data=product_data, 
                                                                      context={'user': user})
                if product_serializer.is_valid():
                    product_serializers.append(product_serializer)
                else:
                    errors = [f"Row {rw+1} :: {error} :: {product_serializer.errors[error][0]}" for error in product_serializer.errors]
                    errors = "\n".join(errors)
                    return api_response(errors)
            for product in product_serializers:
                product.save()
            msg = "success"
            return get_response(msg,'', True)
        else:
            errors = [f"{error} :: {serializer.errors[error][0]}" for error in serializer.errors]
            errors = "\n".join(errors)
            return api_response(errors)


class RetailerProductImageBulkUploadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = RetailerProductImageBulkUploadSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            rs_dict = {}
            rs = []
            sc = 0
            fa = 0
            images = request.data.getlist('images')
            rs_dict['total'] = len(images)
            for image in images:
                file_name = image.name.split('.')[0]
                product_sku = file_name.split("_")[0]
                try:
                    product = RetailerProduct.objects.get(sku=product_sku)
                    image_serializer = RetailerProductImageSerializer(
                        data={
                            'product': product.id,
                            'image_name': file_name,
                            'image': image
                        }
                    )
                    if image_serializer.is_valid():
                        image_serializer.save()
                    update_es([product], product.shop_id)
                    sc += 1
                    msg = {
                        'is_valid': True,
                        'name': image_serializer.data.get('image_name'),
                        'url': image_serializer.data.get('image'),
                        'product_sku': product.sku,
                        'product_name': product.name
                    }
                except:
                    fa += 1
                    msg = {
                        'is_valid': False,
                        'name': file_name,
                        'url': '###',
                        'product_sku': 'Wrong SKU {}'.format(product_sku),
                        'product_name': 'No RetailerProduct found with SKU ID <b>{}</b>'.format(product_sku),
                    }
                rs.append(msg)
            msg = "success"
            rs_dict['success'] = sc
            rs_dict['aborted'] = fa
            rs_dict['results'] = rs
            return get_response(msg, rs_dict, True)
        else:
            error = 'Please provide valid images.'
            return api_response(error)


class PosShopListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = PosShopListSerializer
    pagination_class = SmallOffsetPagination
    
    def get(self, request, *args, **kawrgs):
        search = self.request.query_params.get('search_text')
        qs = Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2, 
                                 pos_enabled=True, pos_shop__status=True).distinct('id')
        if search:
            qs = qs.filter(Q(shop_name__icontains=search) | Q(shop_owner__phone_number__icontains=search))
        qs = self.pagination_class().paginate_queryset(qs, request)
        serializer = self.serializer_class(qs, many=True)
        msg = 'success'
        return get_response(msg, serializer.data, True)


class OnlineDisabledChoices(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        '''
        API to get list of ONLINE DISABLED CHOICES list
        '''
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in RetailerProduct.ONLINE_DISABLED_CHOICES]
        msg = [""]
        return get_response(msg, data, True)