from decimal import Decimal
import logging
import json
import sys
import requests
from io import BytesIO

from django.db import transaction
from django.http import QueryDict
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator

from rest_framework import status, authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from retailer_backend.utils import SmallOffsetPagination
from products.models import Product
from shops.models import Shop
from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon

from pos.models import RetailerProduct
from pos.common_functions import (RetailerProductCls, OffersCls, serializer_error, api_response, get_shop_id_from_token,
                                  validate_data_format)

from .serializers import (RetailerProductCreateSerializer, RetailerProductUpdateSerializer,
                          RetailerProductResponseSerializer, CouponOfferSerializer, FreeProductOfferSerializer,
                          ComboOfferSerializer, CouponOfferUpdateSerializer, ComboOfferUpdateSerializer,
                          CouponListSerializer, FreeProductOfferUpdateSerializer, OfferCreateSerializer,
                          OfferUpdateSerializer, CouponGetSerializer, OfferGetSerializer, ImageFileSerializer)

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
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        """
            Create Product
        """
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            modified_data = self.validate_create(shop_id)
            if 'error' in modified_data:
                return api_response(modified_data['error'])
            serializer = RetailerProductCreateSerializer(data=modified_data)
            if serializer.is_valid():
                data = serializer.data
                name, ean, mrp, sp, linked_pid, description = data['product_name'], data['product_ean_code'], data[
                    'mrp'], data['selling_price'], data['linked_product_id'], data['description']
                with transaction.atomic():
                    # Decide sku_type 3 = using GF product changed mrp, 2 = using GF product same mrp, 1 = new product
                    sku_type = self.get_sku_type(mrp, name, ean, linked_pid)
                    # Create product
                    product = RetailerProductCls.create_retailer_product(shop_id, name, mrp, sp, linked_pid, sku_type,
                                                                         description, ean)
                    # Upload images
                    RetailerProductCls.create_images(product, modified_data.getlist('images'))
                    serializer = RetailerProductResponseSerializer(product)
                    return api_response('Product created successfully!', serializer.data, status.HTTP_200_OK, True)
            else:
                return api_response(serializer_error(serializer))
        else:
            return api_response("Shop Doesn't Exist")

    def put(self, request, *args, **kwargs):
        """
            Update product
        """
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            modified_data = self.validate_update(shop_id)
            if 'error' in modified_data:
                return api_response(modified_data['error'])
            serializer = RetailerProductUpdateSerializer(data=modified_data)
            if serializer.is_valid():
                data = serializer.data
                product = RetailerProduct.objects.get(id=data['product_id'], shop_id=shop_id)
                name, ean, mrp, sp, description = data['product_name'], data['product_ean_code'], data[
                    'mrp'], data['selling_price'], data['description']

                with transaction.atomic():
                    # Update product
                    product.product_ean_code = ean if ean else product.product_ean_code
                    product.mrp = mrp if mrp else product.mrp
                    product.name = name if name else product.name
                    product.sku_type = self.get_sku_type(product.mrp, product.name, product.product_ean_code,
                                                         product.linked_product.id if product.linked_product else None)
                    product.selling_price = sp if sp else product.selling_price
                    product.status = data['status'] if data['status'] else product.status
                    product.description = description if description else product.description
                    product.save()
                    if 'images' in request.data:
                        # Update images
                        RetailerProductCls.update_images(product, modified_data.getlist('images'), modified_data.getlist('image_ids'))
                    serializer = RetailerProductResponseSerializer(product)
                    return api_response('Product updated successfully!', serializer.data, status.HTTP_200_OK, True)
            else:
                return api_response(serializer_error(serializer))
        else:
            return api_response("Shop Doesn't Exist")

    def validate_create(self, shop_id):
        # Validate product data
        try:
            data = json.loads(self.request.data["data"])
            p_data = QueryDict('', mutable=True)
            p_data.update(data)
        except (KeyError, ValueError):
            return {'error': "Invalid Data Format"}
        # Image urls
        try:
            validate = URLValidator()
            for image_url in self.request.data.getlist('image_urls'):
                validate(image_url)
        except ValidationError:
            return {"error": "Invalid Image Url / Urls"}
        # Update product data with shop id and images
        p_data['shop_id'] = shop_id
        image_files = self.request.FILES.getlist('images')
        image_urls = self.request.data.getlist('image_urls')
        for image_url in image_urls:
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
        p_data.setlist('images', image_files)
        return p_data

    def validate_update(self, shop_id):
        # Validate product data
        try:
            data = json.loads(self.request.data["data"])
            p_data = QueryDict('', mutable=True)
            p_data.update(data)
        except (KeyError, ValueError):
            return {'error': "Invalid Data Format"}
        # Image Ids
        image_ids = []
        try:
            for image_id in self.request.data.getlist('image_ids'):
                image_ids.append(int(image_id))
        except TypeError:
            return {"error": "Invalid Image Id / Ids. Ensure Digit Values"}
        # Update product data with shop id and images
        p_data['shop_id'] = shop_id
        p_data.setlist('images', self.request.FILES.getlist('images'))
        p_data.setlist('image_ids', image_ids)
        return p_data

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
    permission_classes = (AllowAny,)
    pagination_class = SmallOffsetPagination

    def get(self, request, *args, **kwargs):
        """
            Get Offer / Offers List
        """
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            coupon_id = request.GET.get('id')
            if coupon_id:
                serializer = OfferGetSerializer(data={'id': coupon_id, 'shop_id': shop_id})
                if serializer.is_valid():
                    return self.get_offer(coupon_id)
                else:
                    return api_response(serializer_error(serializer))
            else:
                return self.get_offers_list(request, shop_id)
        else:
            return api_response("Shop Doesn't Exist")

    def post(self, request, *args, **kwargs):
        """
            Create Any Offer
        """
        msg = validate_data_format(request)
        if msg:
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            serializer = OfferCreateSerializer(data=request.data)
            if serializer.is_valid():
                return self.create_offer(serializer.data, shop_id)
            else:
                return api_response(serializer_error(serializer))
        else:
            return api_response("Shop Doesn't Exist")

    def put(self, request, *args, **kwargs):
        """
           Update Any Offer
        """
        msg = validate_data_format(request)
        if msg:
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            data = request.data
            data['shop_id'] = shop_id
            serializer = OfferUpdateSerializer(data=data)
            if serializer.is_valid():
                return self.update_offer(serializer.data, shop_id)
            else:
                return api_response(serializer_error(serializer))
        else:
            return api_response("Shop Doesn't Exist")

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
                if offer_type == 1:
                    return self.update_coupon(data, shop_id)
                elif offer_type == 2:
                    return self.update_combo(data, shop_id)
                else:
                    return self.update_free_product_offer(data, shop_id)
        else:
            return api_response(serializer_error(serializer))

    @staticmethod
    def get_offer(coupon_id):
        coupon = CouponGetSerializer(Coupon.objects.get(id=coupon_id)).data
        coupon.update(coupon['details'])
        coupon.pop('details')
        msg = {"is_success": True, "message": "Offer", "response_data": coupon}
        return Response(msg, status=200)

    def get_offers_list(self, request, shop_id):
        """
          Get Offers List
       """
        coupon = Coupon.objects.filter(shop=shop_id).order_by('-created_at')
        if request.GET.get('search_text'):
            coupon = coupon.filter(coupon_name__icontains=request.GET.get('search_text'))
        objects = self.pagination_class().paginate_queryset(coupon, self.request)
        data = CouponListSerializer(objects, many=True).data
        for coupon in data:
            coupon.update(coupon['details'])
            coupon.pop('details')
        msg = {"is_success": True, "message": "Offers List", "response_data": data}
        return Response(msg, status=200)

    @staticmethod
    def create_coupon(data, shop_id):
        """
            Discount on order
        """
        shop = Shop.objects.filter(id=shop_id).last()
        start_date, expiry_date, discount_value, discount_amount = data['start_date'], data['end_date'], data[
            'discount_value'], data['order_value']
        if data['is_percentage']:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value,
                                                        max_discount=data['max_discount'], is_percentage=True)
            rule_set_name_with_shop_id = f"{shop_id}_{discount_value}% off on orders above Rs. {discount_amount}"
            if discount_obj.max_discount and float(discount_obj.max_discount) > 0:
                coupon_code = f"{discount_value}% off upto Rs. {discount_obj.max_discount} on orders above Rs. {discount_amount}"
            else:
                coupon_code = f"{discount_value}% off on orders above Rs. {discount_amount}"
        else:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value, is_percentage=False)
            rule_set_name_with_shop_id = f"{shop_id}_Rs. {discount_value} off on orders above Rs. {discount_amount}"
            coupon_code = f"Rs. {discount_value} off on orders above Rs. {discount_amount}"

        coupon_obj = OffersCls.rule_set_creation(rule_set_name_with_shop_id, start_date, expiry_date, discount_amount,
                                                 discount_obj)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)
        else:
            coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', data['coupon_name'], coupon_code, shop,
                                                     start_date, expiry_date)
            data['id'] = coupon.id
            return api_response("Coupon Offer created successfully!", data, status.HTTP_200_OK, True)

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
        combo_rule_name = f"{shop_id}_{combo_code}"
        coupon_obj = OffersCls.rule_set_creation(combo_rule_name, start_date, expiry_date)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)

        OffersCls.rule_set_product_mapping(coupon_obj.id, retailer_primary_product_obj, purchased_product_qty,
                                           retailer_free_product_obj, free_product_qty, combo_offer_name, start_date,
                                           expiry_date)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'catalog', combo_offer_name, combo_code, shop,
                                                 start_date, expiry_date)
        data['id'] = coupon.id
        return api_response("Combo Offer created successfully!", data, status.HTTP_200_OK, True)

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
            return api_response("Offer already exists for same quantity of free product. Please check.")

        rule_name = f"{shop_id}_{retailer_free_product_obj.name}_{free_product_qty}_{discount_amount}"
        coupon_code = f"{free_product_qty} {retailer_free_product_obj.name} free on orders above Rs. {discount_amount}"
        coupon_obj = OffersCls.rule_set_creation(rule_name, start_date, expiry_date, discount_amount, None,
                                                 retailer_free_product_obj, free_product_qty)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', coupon_name, coupon_code, shop, start_date,
                                                 expiry_date)
        data['id'] = coupon.id
        return api_response("Free Product Offer Created Successfully!", data, status.HTTP_200_OK, True)

    @staticmethod
    def update_coupon(data, shop_id):
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
        return api_response("Coupon Offer Updated Successfully!", None, status.HTTP_200_OK, True)

    @staticmethod
    def update_combo(data, shop_id):
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
        return api_response("Combo Offer Updated Successfully!", None, status.HTTP_200_OK, True)

    @staticmethod
    def update_free_product_offer(data, shop_id):
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
        return api_response("Free Product Offer Updated Successfully!", None, status.HTTP_200_OK, True)
