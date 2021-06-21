import datetime
from decimal import Decimal
import logging
import json
import sys
import requests
from io import BytesIO

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator
from django.db.models import Q, Sum, F
from django.db.models.functions import Coalesce

from rest_framework import status, authentication, permissions
from rest_framework.generics import GenericAPIView

from retailer_backend.utils import SmallOffsetPagination
from products.models import Product
from shops.models import Shop
from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon
from wms.models import PosInventoryChange, PosInventoryState, PosInventory
from retailer_to_sp.models import OrderedProduct, Order

from pos.models import RetailerProduct, RetailerProductImage
from pos.common_functions import (RetailerProductCls, OffersCls, serializer_error, api_response, PosInventoryCls,
                                  check_pos_shop)

from .serializers import (RetailerProductCreateSerializer, RetailerProductUpdateSerializer,
                          RetailerProductResponseSerializer, CouponOfferSerializer, FreeProductOfferSerializer,
                          ComboOfferSerializer, CouponOfferUpdateSerializer, ComboOfferUpdateSerializer,
                          CouponListSerializer, FreeProductOfferUpdateSerializer, OfferCreateSerializer,
                          OfferUpdateSerializer, CouponGetSerializer, OfferGetSerializer, ImageFileSerializer,
                          InventoryReportSerializer, InventoryLogReportSerializer, SalesReportResponseSerializer,
                          SalesReportSerializer)

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
        modified_data = self.validate_create(shop.id)
        if 'error' in modified_data:
            return api_response(modified_data['error'])
        serializer = RetailerProductCreateSerializer(data=modified_data)
        if serializer.is_valid():
            data = serializer.data
            name, ean, mrp, sp, linked_pid, description, stock_qty = data['product_name'], data[
                'product_ean_code'], data['mrp'], data['selling_price'], data['linked_product_id'], data[
                                                                         'description'], data['stock_qty']
            with transaction.atomic():
                # Decide sku_type 2 = using GF product, 1 = new product
                sku_type = 2 if linked_pid else 1
                # sku_type = self.get_sku_type(mrp, name, ean, linked_pid)
                # Create product
                product = RetailerProductCls.create_retailer_product(shop.id, name, mrp, sp, linked_pid, sku_type,
                                                                     description, ean)
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
        serializer = RetailerProductUpdateSerializer(data=modified_data)
        if serializer.is_valid():
            data = serializer.data
            product = RetailerProduct.objects.get(id=data['product_id'], shop_id=shop.id)
            name, ean, mrp, sp, description, stock_qty = data['product_name'], data['product_ean_code'], data[
                'mrp'], data['selling_price'], data['description'], data['stock_qty']

            with transaction.atomic():
                # Update product
                product.product_ean_code = ean if ean else product.product_ean_code
                product.mrp = mrp if mrp else product.mrp
                product.name = name if name else product.name
                product.selling_price = sp if sp else product.selling_price
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
                serializer = RetailerProductResponseSerializer(product)
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
            retailer_primary_product_obj = RetailerProduct.objects.get(id=retailer_primary_product, shop=shop_id)
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
        inv_available = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        inv = PosInventory.objects.filter(product__shop=shop, inventory_state=inv_available)

        # Search by product name
        if request.GET.get('search_text'):
            inv = inv.filter(product__name__icontains=request.GET.get('search_text'))

        inv = inv.order_by('-modified_at')
        objects = self.pagination_class().paginate_queryset(inv, self.request)
        data = InventoryReportSerializer(objects, many=True).data
        msg = "Inventory Report Fetched Successfully!" if data else "No Product Inventory Found For This Shop!"
        return api_response(msg, data, status.HTTP_200_OK, True)


class InventoryLogReport(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
            Get inventory logs for a product
        """
        shop = kwargs['shop']
        # Validate product id w.r.t. shop
        if 'pk' not in kwargs:
            return api_response("Please provide a Product Id to fetch inventory log for")
        pk = kwargs['pk']
        try:
            product = RetailerProduct.objects.get(pk=kwargs['pk'], shop=shop)
        except ObjectDoesNotExist:
            return api_response("Product Id Invalid")

        # Inventory
        inv_available = PosInventoryState.objects.get(inventory_state=PosInventoryState.AVAILABLE)
        inv = PosInventory.objects.filter(product=product, inventory_state=inv_available).last()
        inv_data = InventoryReportSerializer(inv).data

        # Inventory Logs
        logs = PosInventoryChange.objects.filter(product_id=pk)
        search_text = request.GET.get('search_text')
        if search_text:
            logs = logs.filter(Q(transaction_type__icontains=search_text) | Q(transaction_id__icontains=search_text))
        logs = logs.order_by('-modified_at')
        objects = self.pagination_class().paginate_queryset(logs, self.request)
        logs_data = InventoryLogReportSerializer(objects, many=True).data

        # Merge data
        data = dict()
        data['product_inventory'] = inv_data
        data['logs'] = logs_data
        return api_response("Inventory Report Fetched Successfully!", data, status.HTTP_200_OK, True)


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
        elif report_type == 'monthly':
            return self.monthly_report(shop, report_type, request_data)
        else:
            return self.invoice_report(shop, report_type, request_data)

    def invoice_report(self, shop, report_type, request_data):
        # Shop Filter
        qs = OrderedProduct.objects.select_related('order', 'invoice').prefetch_related(
            'order__rt_return_order').filter(order__seller_shop=shop)

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
        qs = qs.annotate(returns=Coalesce(Sum('order__rt_return_order__refund_amount'), 0))
        qs = qs.annotate(effective_sale=F('sale') - F('returns'), invoice_no=F('invoice__invoice_no'))
        data = qs.values('sale', 'returns', 'effective_sale', 'created_at__date', 'invoice_no')

        return self.get_response(report_type, data, request_data['sort_by'], request_data['sort_order'])

    def daily_report(self, shop, report_type, request_data):
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
        qs = qs.annotate(returns=Coalesce(Sum('rt_return_order__refund_amount'), 0))
        qs = qs.annotate(effective_sale=F('sale') - F('returns')).order_by('created_at__date')
        data = qs.values('sale', 'returns', 'effective_sale', 'created_at__date')

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
        qs = qs.annotate(returns=Coalesce(Sum('rt_return_order__refund_amount'), 0))
        qs = qs.annotate(effective_sale=F('sale') - F('returns')).order_by('created_at__month')
        data = qs.values('sale', 'returns', 'effective_sale', 'created_at__month', 'created_at__year')

        return self.get_response(report_type, data, request_data['sort_by'], request_data['sort_order'])

    @staticmethod
    def filter_by_date_filter(date_filter, invoices):
        date_today = datetime.datetime.today()
        if date_filter == 'today':
            invoices = invoices.filter(created_at__date=date_today)
        elif date_filter == 'yesterday':
            date_yesterday = date_today - datetime.timedelta(days=1)
            invoices = invoices.filter(created_at__date=date_yesterday)
        elif date_filter == 'this_week':
            invoices = invoices.filter(created_at__week=date_today.isocalendar()[1])
        elif date_filter == 'last_week':
            last_week = date_today - datetime.timedelta(weeks=1)
            invoices = invoices.filter(created_at__week=last_week.isocalendar()[1])
        elif date_filter == 'this_month':
            invoices = invoices.filter(created_at__month=date_today.month)
        elif date_filter == 'last_month':
            last_month = date_today - datetime.timedelta(days=30)
            invoices = invoices.filter(created_at__month=last_month.month)
        elif date_filter == 'this_year':
            invoices = invoices.filter(created_at__year=date_today.year)
        return invoices

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
