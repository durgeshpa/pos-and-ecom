import datetime
from decimal import Decimal
import logging
import json
import sys
import requests
from io import BytesIO
from copy import deepcopy

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator
from django.db.models import Q, Sum, F, Count, Subquery, OuterRef, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce

from rest_framework import status, authentication, permissions
from rest_framework.generics import GenericAPIView, ListAPIView

from retailer_backend.utils import SmallOffsetPagination
from products.models import Product
from shops.models import Shop
from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon
from wms.models import PosInventoryChange, PosInventoryState, PosInventory
from retailer_to_sp.models import OrderedProduct, Order, OrderReturn

from pos.models import RetailerProduct, RetailerProductImage, ShopCustomerMap, Vendor, PosCart, PosGRNOrder, PaymentType
from pos.common_functions import (RetailerProductCls, OffersCls, serializer_error, api_response, PosInventoryCls,
                                  check_pos_shop, ProductChangeLogs)
from pos.common_validators import compareList, validate_user_type_for_pos_shop

from .serializers import (PaymentTypeSerializer, RetailerProductCreateSerializer, RetailerProductUpdateSerializer,
                          RetailerProductResponseSerializer, CouponOfferSerializer, FreeProductOfferSerializer,
                          ComboOfferSerializer, CouponOfferUpdateSerializer, ComboOfferUpdateSerializer,
                          CouponListSerializer, FreeProductOfferUpdateSerializer, OfferCreateSerializer,
                          OfferUpdateSerializer, CouponGetSerializer, OfferGetSerializer, ImageFileSerializer,
                          InventoryReportSerializer, InventoryLogReportSerializer, SalesReportResponseSerializer,
                          SalesReportSerializer, CustomerReportSerializer, CustomerReportResponseSerializer,
                          CustomerReportDetailResponseSerializer, VendorSerializer, VendorListSerializer,
                          POSerializer, POGetSerializer, POProductInfoSerializer, POListSerializer,
                          PosGrnOrderCreateSerializer, PosGrnOrderUpdateSerializer, GrnListSerializer,
                          GrnOrderGetSerializer)

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
    def post(self, request, *args, **kwargs):
        """
            Create Product
        """
        shop = kwargs['shop']
        pos_shop_user_obj = validate_user_type_for_pos_shop(shop, request.user)
        if 'error' in pos_shop_user_obj:
            return api_response(pos_shop_user_obj['error'])
        modified_data = self.validate_create(shop.id)
        if 'error' in modified_data:
            return api_response(modified_data['error'])
        serializer = RetailerProductCreateSerializer(data=modified_data)
        if serializer.is_valid():
            data = serializer.data
            name, ean, mrp, sp, offer_price, offer_sd, offer_ed, linked_pid, description, stock_qty = data[
                'product_name'], data['product_ean_code'], data['mrp'], data['selling_price'], data[
                    'offer_price'], data['offer_start_date'], data['offer_end_date'], data[
                        'linked_product_id'], data['description'], data['stock_qty']
            with transaction.atomic():
                # Decide sku_type 2 = using GF product, 1 = new product
                sku_type = 2 if linked_pid else 1
                # sku_type = self.get_sku_type(mrp, name, ean, linked_pid)
                # Create product
                product = RetailerProductCls.create_retailer_product(shop.id, name, mrp, sp, linked_pid, sku_type,
                                                                     description, ean, self.request.user, 'product',
                                                                     None, 'active', offer_price, offer_sd, offer_ed)
                # Upload images
                if 'images' in modified_data:
                    RetailerProductCls.create_images(product, modified_data['images'])
                product.save()
                # Add Inventory
                PosInventoryCls.stock_inventory(product.id, PosInventoryState.NEW, PosInventoryState.AVAILABLE,
                                                stock_qty, self.request.user, product.sku,
                                                PosInventoryChange.STOCK_ADD)
                serializer = RetailerProductResponseSerializer(product)
                return api_response('Product has been created successfully!', serializer.data, status.HTTP_200_OK,
                                    True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
    def put(self, request, *args, **kwargs):
        """
            Update product
        """
        shop = kwargs['shop']
        modified_data, success_msg = self.validate_update(shop.id)
        if 'error' in modified_data:
            return api_response(modified_data['error'])
        if not compareList(list(modified_data.keys()), ['product_id', 'stock_qty', 'shop_id']):
            pos_shop_user_obj = validate_user_type_for_pos_shop(shop, request.user)
            if 'error' in pos_shop_user_obj:
                return api_response(pos_shop_user_obj['error'])
        serializer = RetailerProductUpdateSerializer(data=modified_data)
        if serializer.is_valid():
            data = serializer.data
            product = RetailerProduct.objects.get(id=data['product_id'], shop_id=shop.id)
            name, ean, mrp, sp, description, stock_qty = data['product_name'], data['product_ean_code'], data[
                'mrp'], data['selling_price'], data['description'], data['stock_qty']
            offer_price, offer_sd, offer_ed = data['offer_price'], data['offer_start_date'], data['offer_end_date']
            add_offer_price = data['add_offer_price']

            with transaction.atomic():
                old_product = deepcopy(product)
                # Update product
                product.product_ean_code = ean if ean else product.product_ean_code
                product.mrp = mrp if mrp else product.mrp
                product.name = name if name else product.name
                product.selling_price = sp if sp else product.selling_price
                if add_offer_price is not None:
                    product.offer_price = offer_price
                    product.offer_start_date = offer_sd
                    product.offer_end_date = offer_ed
                product.status = data['status'] if data['status'] else product.status
                product.description = description if description else product.description
                # Update images
                if 'image_ids' in modified_data:
                    RetailerProductImage.objects.filter(product=product).exclude(
                        id__in=modified_data['image_ids']).delete()
                if 'images' in modified_data:
                    RetailerProductCls.update_images(product, modified_data['images'])
                product.save()
                if 'stock_qty' in modified_data:
                    # Update Inventory
                    PosInventoryCls.stock_inventory(product.id, PosInventoryState.AVAILABLE,
                                                    PosInventoryState.AVAILABLE, stock_qty, self.request.user,
                                                    product.sku, PosInventoryChange.STOCK_UPDATE)
                # Change logs
                ProductChangeLogs.product_update(product, old_product, self.request.user, 'product', product.sku)
                serializer = RetailerProductResponseSerializer(product)
                if data['is_discounted']:
                    discounted_price = data['discounted_price']
                    discounted_stock = data['discounted_stock']
                    product_status = 'active' if discounted_stock > 0 else 'deactivated'

                    initial_state = PosInventoryState.AVAILABLE
                    tr_type = PosInventoryChange.STOCK_UPDATE

                    discounted_product = RetailerProduct.objects.filter(product_ref=product).last()
                    if not discounted_product:

                        initial_state = PosInventoryState.NEW
                        tr_type = PosInventoryChange.STOCK_ADD

                        discounted_product = RetailerProductCls.create_retailer_product(product.shop.id, product.name, product.mrp,
                                                                 discounted_price, product.linked_product_id, 4,
                                                                 product.description, product.product_ean_code,
                                                                 self.request.user, 'product', None, product_status,
                                                                 None, None, None, product)
                    else:
                        RetailerProductCls.update_price(discounted_product.id, discounted_price, product_status,
                                                        self.request.user, 'product', discounted_product.sku)

                    PosInventoryCls.stock_inventory(discounted_product.id, initial_state,
                                                    PosInventoryState.AVAILABLE, discounted_stock, self.request.user,
                                                    discounted_product.sku, tr_type)
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
        success_msg = 'Product has been updated successfully!'
        # Validate product data
        try:
            p_data = json.loads(self.request.data["data"])
        except (KeyError, ValueError):
            return {'error': "Invalid Data Format"}
        if 'product_name' not in p_data:
            if 'selling_price' in p_data:
                success_msg = 'Price has been updated successfully!'
            elif 'status' in p_data:
                if p_data['status'] == 'active':
                    success_msg = 'Product has been activated successfully!'
                else:
                    success_msg = 'Product has been deactivated successfully.'
            elif 'stock_qty' in p_data:
                success_msg = 'Quantity has been updated successfully!'
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
        coupon = CouponGetSerializer(Coupon.objects.get(id=coupon_id)).data
        coupon.update(coupon['details'])
        coupon.pop('details')
        return api_response("Offers", coupon, status.HTTP_200_OK, True)

    def get_offers_list(self, request, shop_id):
        """
          Get Offers List
       """
        coupon = Coupon.objects.select_related('rule').filter(shop=shop_id)
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
                                                     start_date, expiry_date)
            data['id'] = coupon.id
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
                                                 start_date, expiry_date)
        data['id'] = coupon.id
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
                                                 expiry_date)
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
        if search_text:
            logs = logs.filter(Q(transaction_type__icontains=search_text) | Q(transaction_id__icontains=search_text))
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
        qss = Order.objects.filter(seller_shop=shop)
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
        result_set = dict()
        for sale in sales_data:
            key = str(sale['created_at__date'])
            sale['date'] = sale['created_at__date'].strftime("%b %d, %Y")
            del sale['created_at__date']
            result_set[key] = sale
            result_set[key]['returns'] = 0
        for ret in returns_data:
            key = str(ret['created_at__date'])
            ret['date'] = ret['created_at__date'].strftime("%b %d, %Y")
            del ret['created_at__date']
            if key in result_set:
                result_set[key].update(ret)
                result_set[key]['effective_sale'] = result_set[key]['effective_sale'] - ret['returns']
            else:
                result_set[key] = dict()
                result_set[key] = ret
                result_set[key]['sale'] = 0
                result_set[key]['order_count'] = 0
                result_set[key]['effective_sale'] = 0
        for i in range(0, limit):
            date = end_date - datetime.timedelta(days=i)
            date = date.date()
            if str(date) not in result_set:
                result_set[str(date)] = {'sale': 0, 'order_count': 0, 'effective_sale': 0, 'returns': 0,
                                         'date': date.strftime("%b %d, %Y")}

        result_set = dict(reversed(sorted(result_set.items()))).values()
        report_type = report_type.capitalize()
        msg = report_type + ' Sales Report Fetched Successfully!'
        return api_response(msg, result_set, status.HTTP_200_OK, True)

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
        if vendor_status in [True, False]:
            queryset = queryset.filter(status=vendor_status)

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

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        cart = PosCart.objects.filter(retailer_shop=kwargs['shop'], id=kwargs['pk']).prefetch_related(
            'po_products').last()
        if cart:
            return api_response('', POGetSerializer(cart).data, status.HTTP_200_OK, True)
        else:
            return api_response("Purchase Order not found")

    @check_pos_shop
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'user': self.request.user, 'shop': kwargs['shop']})
        if serializer.is_valid():
            serializer.save()
            return api_response('Purchase Order created successfully!', None, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @check_pos_shop
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
    pagination_class = SmallOffsetPagination
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
    queryset = PaymentType.objects.all()
    serializer_class = PaymentTypeSerializer

    def get(self, request):
        """ GET Payment Type List """
        payment_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(payment_type, many=True)
        msg = "" if payment_type else "No payment found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)
