from decimal import Decimal
import logging

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.parsers import JSONParser
from rest_framework import status, authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from products.models import Product
from shops.models import Shop
from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon

from pos.models import RetailerProduct, RetailerProductImage
from pos.utils import MultipartJsonParser
from pos.common_functions import RetailerProductCls, OffersCls, serializer_error, get_response, get_shop_id_from_token,\
    validate_data_format

from .serializers import RetailerProductCreateSerializer, RetailerProductUpdateSerializer, \
    RetailerProductResponseSerializer, RetailerProductImageDeleteSerializer, CouponOfferSerializer, \
    FreeProductOfferSerializer, ComboOfferSerializer, CouponOfferUpdateSerializer, ComboOfferUpdateSerializer, \
    CouponListSerializer, FreeProductOfferUpdateSerializer, OfferCreateSerializer,\
    OfferUpdateSerializer, CouponGetSerializer, OfferGetSerializer
from retailer_backend.utils import SmallOffsetPagination
# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')

POS_SERIALIZERS_MAP = {
    0: RetailerProductCreateSerializer,
    1: RetailerProductUpdateSerializer,
    2: RetailerProductImageDeleteSerializer
}

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


class CatalogueProductCreation(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parser_classes = [MultipartJsonParser, JSONParser]

    def get_shop_id_or_error_message(self, request):
        # If Token and shop_id, check whether Token is valid for shop_id or not
        shopID = request.data.get('shop_id')
        if request.user.id and shopID:
            if Shop.objects.filter(shop_owner_id=request.user.id).exists():
                shop_id_from_token = Shop.objects.filter(shop_owner_id=request.user.id)
            else:
                if Shop.objects.filter(related_users=request.user.id).exists():
                    shop_id_from_token = Shop.objects.filter(related_users=request.user.id)
                else:
                    return "Please Provide a Valid TOKEN"
            shop_id = Shop.objects.filter(id=shopID)
            if not shop_id.values()[0].get('id') == shop_id_from_token.values()[0].get('id'):
                return "INCORRECT TOKEN for given SHOP_ID"

        if shopID:
            return int(shopID)
        else:
            shop_id = get_shop_id_from_token(request)
            return shop_id

    def get_serializer_class(self, data):
        """
        We are getting different serializer_class for post and put API's.
        0 refers to POST and 1 refers to PUT .
        """
        if data == 0:
            return POS_SERIALIZERS_MAP[0]
        if data == 1:
            return POS_SERIALIZERS_MAP[1]
        if data == 2:
            return POS_SERIALIZERS_MAP[2]

    def post(self, request, *args, **kwargs):
        """
        POST API for Product Creation.
        Using RetailerProductCreateSerializer for request and RetailerProductResponseSerializer for response.
        """
        msg = validate_data_format(request)
        if msg:
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        shop_id_or_error_message = self.get_shop_id_or_error_message(request)
        if type(shop_id_or_error_message) == int:
            serializer = self.get_serializer_class(0)(data=request.data)
            if serializer.is_valid():
                product_name = request.data.get('product_name')
                mrp = request.data.get('mrp')
                selling_price = request.data.get('selling_price')
                linked_product_id = request.data.get('linked_product_id')
                product_ean_code = request.data.get('product_ean_code')
                product_status = request.data.get('status')
                description = request.data.get('description') if request.data.get('description') else ''
                product_images = request.FILES.getlist('images')
                if len(product_images) > 3:
                    # product_images count is greater then 3 through error
                    msg = {'is_success': False,
                           'error_message': "Please upload maximum 3 images",
                           'response_data': None}
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                if RetailerProduct.objects.filter(shop=shop_id_or_error_message, name=product_name, mrp=mrp, selling_price=selling_price).exists():
                    msg = {"is_success": False, "message": "Product {} with mrp {} & selling_price {} already exist."
                            .format(product_name, mrp, selling_price),
                            "response_data": None}
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

                # if else condition for checking whether, Product we are creating is linked with existing product or not
                # with the help of 'linked_product_id'
                with transaction.atomic():
                    if request.data.get('linked_product_id'):
                        # If product is linked with existing product
                        if Product.objects.filter(id=request.data.get('linked_product_id')).exists():
                            product = Product.objects.filter(id=request.data.get('linked_product_id'))
                            if str(product.values()[0].get('product_mrp')) == format(
                                    Decimal(request.data.get('mrp')), ".2f"):
                                # If Linked_Product_MRP == Input_MRP , create a Product with [SKU TYPE : LINKED]
                                product_obj = RetailerProductCls.create_retailer_product(shop_id_or_error_message,
                                                                           product_name, mrp, selling_price,
                                                                           linked_product_id, 2, description,
                                                                           product_ean_code, product_status)
                            else:
                                # If Linked_Product_MRP != Input_MRP, Create a new Product with
                                # SKU_TYPE == "LINKED_EDITED"
                                product_obj = RetailerProductCls.create_retailer_product(shop_id_or_error_message,
                                                                           product_name, mrp, selling_price,
                                                                           linked_product_id, 3, description,
                                                                           product_ean_code, product_status)
                    else:
                        # If product is not linked with existing product, Create a new Product
                        # with SKU_TYPE == "Created"
                        product_obj = RetailerProductCls.create_retailer_product(shop_id_or_error_message, product_name, mrp,
                                                                   selling_price, None, 1, description,
                                                                   product_ean_code, product_status)

                    for file in product_images:
                        RetailerProductImage.objects.create(product_id=product_obj.id, image=file)

                product = RetailerProduct.objects.all().last()
                # Fetching the data of created product
                data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp', 'selling_price',
                                                      'description', 'sku_type', 'product_ean_code',
                                                      'linked_product__product_name', 'created_at',
                                                      'modified_at', 'status', 'retailer_product_image').filter(id=product.id)
                response_serializer = RetailerProductResponseSerializer(instance=data[0])
                message = {"is_success": True, "message": "Product created successfully!",
                           "response_data": response_serializer.data}
                return Response(message, status=status.HTTP_201_CREATED)
            else:
                msg = serializer_error(serializer)
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            msg = {'is_success': False,
                   'error_message': shop_id_or_error_message,
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def put(self, request, *args, **kwargs):
        """
        PUT API for Product Update.
        Using RetailerProductUpdateSerializer for request and RetailerProductResponseSerializer for response.
        """
        msg = validate_data_format(request)
        if msg:
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        # RetailerProductUpdateSerializer is used
        shop_id_or_error_message = self.get_shop_id_or_error_message(request)
        if type(shop_id_or_error_message) == int:
            serializer = self.get_serializer_class(1)(data=request.data)
            if serializer.is_valid():
                product_id = request.data.get('product_id')
                mrp = request.data.get('mrp')
                product_images = request.FILES.getlist('images')
                image_id = request.data.get('image_id')

                if len(product_images) > 3:
                    # product_images count is greater then 3 through error
                    msg = {'is_success': False,
                           'error_message': "Please upload maximum 3 images",
                           'response_data': None}
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                if RetailerProduct.objects.filter(id=product_id,
                                                  shop_id=shop_id_or_error_message).exists():
                    expected_input_data_list = ['product_id', 'mrp',
                                                'product_ean_code', 'selling_price',
                                                'description', 'status', 'images']
                    actual_input_data_list = []  # List of keys that user wants to update(If user wants to update product_name, this list wil only have product_name)
                    for key in expected_input_data_list:
                        if key in request.data.keys():
                            actual_input_data_list.append(key)

                    product = RetailerProduct.objects.get(id=product_id, shop_id=shop_id_or_error_message)
                    selling_price = request.data.get('selling_price')
                    if mrp and selling_price:
                        # if both mrp & selling price are there in edit product request
                        # checking if product already exist, through error
                        if RetailerProduct.objects.filter(shop_id=shop_id_or_error_message, name=product.name, mrp=mrp,
                                                          selling_price=selling_price).exclude(id=product_id).exists():
                            msg = {"is_success": False,
                                   "message": "Product {} with mrp {} & selling_price {} already exist."
                                       .format(product.name, mrp, selling_price),
                                   "response_data": None}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif mrp:
                        # if only mrp is there in edit product request
                        # checking if product already exist, through error
                        if RetailerProduct.objects.filter(shop_id=shop_id_or_error_message, name=product.name, mrp=mrp,
                                                          selling_price=product.selling_price).\
                                                          exclude(id=product_id).exists():
                            msg = {"is_success": False,
                                   "message": "Product {} with mrp {} & selling_price {} already exist."
                                       .format(product.name, mrp, product.selling_price),
                                   "response_data": None}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif selling_price:
                        # if only selling_price is there in edit product request
                        # checking if product already exist, through error
                        if RetailerProduct.objects.filter(shop_id=shop_id_or_error_message, name=product.name, mrp=product.mrp,
                                                          selling_price=selling_price).\
                                                          exclude(id=product_id).exists():
                            msg = {"is_success": False,
                                   "message": "Product {} with mrp {} & selling_price {} already exist."
                                       .format(product.name, product.mrp, selling_price),
                                   "response_data": None}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    linked_product_id = product.linked_product_id
                    if linked_product_id:
                        if 'mrp' in actual_input_data_list:
                            # If MRP in actual_input_data_list
                            linked_product = Product.objects.filter(id=linked_product_id)
                            if format(Decimal(mrp), ".2f") == str(
                                    linked_product.values()[0].get('product_mrp')):
                                # If Input_MRP == Product_MRP, Update the product with [SKU Type : Linked]
                                product.sku_type = 2
                            else:
                                # If Input_MRP != Product_MRP, Update the product with [SKU Type : Linked Edited]
                                product.sku_type = 3
                    if image_id:
                        for id in image_id:
                            try:
                                product_image_id = RetailerProductImage.objects.get(id=int(id), product=product_id)
                                # delete image from product
                                product_image_id.delete()
                            except ObjectDoesNotExist:
                                return get_response(f"Image Does Not Exist with this image id {id}")

                    if product_images:
                        # If product_image_data in request
                        if RetailerProductImage.objects.filter(product=product_id).exists():
                            # delete existing product_image
                            RetailerProductImage.objects.filter(product=product_id).delete()
                        for file in product_images:
                            # create new product_image
                            RetailerProductImage.objects.create(product_id=product_id, image=file)
                    if 'product_ean_code' in actual_input_data_list:
                        # If product_ean_code in actual_input_data_list
                        product.product_ean_code = request.data.get('product_ean_code')
                    if 'mrp' in actual_input_data_list:
                        # If MRP in actual_input_data_list
                        product.mrp = mrp
                    if 'status' in actual_input_data_list:
                        # If status in actual_input_data_list
                        product.status = request.data.get('status')
                    if 'selling_price' in actual_input_data_list:
                        # If selling price in actual_input_data_list
                        product.selling_price = request.data.get('selling_price')
                    if 'description' in actual_input_data_list:
                        # Update Description
                        product.description = request.data.get('description')
                    product.save()

                    data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp',
                                                          'selling_price', 'description', 'sku_type',
                                                          'product_ean_code', 'linked_product__product_name',
                                                          'created_at', 'modified_at', 'status').\
                        filter(id=request.data.get('product_id'))
                    response_serializer = RetailerProductResponseSerializer(instance=data[0])
                    message = {"is_success": True, "message": f"Product has been successfully UPDATED!",
                               "response_data": response_serializer.data}
                    return Response(message, status=status.HTTP_202_ACCEPTED)
                else:
                    msg = {'is_success': False,
                           'error_message': f"There is no product available with (product id : {product_id}) "
                                            f"for the shop_id provided",
                           'response_data': None}
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                msg = serializer_error(serializer)
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            msg = {'is_success': False,
                   'error_message': shop_id_or_error_message,
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def delete(self, request):
        """
            Delete Image from product
        """
        msg = validate_data_format(request)
        if msg:
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        shop_id_or_error_message = self.get_shop_id_or_error_message(request)
        if type(shop_id_or_error_message) == int:
            serializer = self.get_serializer_class(2)(data=request.data)
            if serializer.is_valid():
                product_id = request.data.get('product_id')
                image_id = request.data.get('image_id')
                try:
                    product_image_id = RetailerProductImage.objects.get(id=image_id, product=product_id)
                except ObjectDoesNotExist:
                    return get_response("Image Does Not Exist with this Product ID")
                product_image_id.delete()
                data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp',
                                                      'selling_price', 'description', 'sku_type',
                                                      'product_ean_code', 'linked_product__product_name',
                                                      'created_at', 'modified_at', 'status').\
                    filter(id=request.data.get('product_id'))
                response_serializer = RetailerProductResponseSerializer(instance=data[0])
                message = {"is_success": True, "message": f"Product Image has been Deleted successfully!",
                           "response_data": response_serializer.data}
                return Response(message, status=status.HTTP_202_ACCEPTED)
            else:
                msg = serializer_error(serializer)
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)


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
                    msg = serializer_error(serializer)
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                return self.get_offers_list(request, shop_id)
        else:
            msg = {'is_success': False, 'message': "Shop Doesn't Exist", 'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

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
                msg = serializer_error(serializer)
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            msg = {'is_success': False, 'message': "Shop Doesn't Exist!", 'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

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
                msg = serializer_error(serializer)
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            msg = {'is_success': False, 'message': "Shop Doesn't Exist", 'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def create_offer(self, data, shop_id):
        offer_type = data['offer_type']
        serializer_class = OFFER_SERIALIZERS_MAP[data['offer_type']]
        serializer = serializer_class(data=self.request.data)
        if serializer.is_valid():
            with transaction.atomic():
                data.update(serializer.data)
                if offer_type == 1:
                    msg, status_code = self.create_coupon(data, shop_id)
                elif offer_type == 2:
                    msg, status_code = self.create_combo_offer(data, shop_id)
                else:
                    msg, status_code = self.create_free_product_offer(data, shop_id)
                return Response(msg, status=status_code)
        else:
            msg = serializer_error(serializer)
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def update_offer(self, data, shop_id):
        offer_type = data['offer_type']
        serializer_class = OFFER_UPDATE_SERIALIZERS_MAP[data['offer_type']]
        serializer = serializer_class(data=self.request.data)
        if serializer.is_valid():
            with transaction.atomic():
                data.update(serializer.data)
                if offer_type == 1:
                    msg, status_code = self.update_coupon(data, shop_id)
                elif offer_type == 2:
                    msg, status_code = self.update_combo(data, shop_id)
                else:
                    msg, status_code = self.update_free_product_offer(data, shop_id)
                return Response(msg, status=status_code)
        else:
            msg = serializer_error(serializer)
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

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
            coupon = coupon.filter(coupon_code__icontains=request.GET.get('search_text'))
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
            if discount_obj.max_discount:
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
            msg, status_code = {"is_success": False, "message": coupon_obj, "response_data": None}, 406
        else:
            coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', data['coupon_name'], coupon_code, shop,
                                                     start_date, expiry_date)
            data['id'] = coupon.id
            msg, status_code = {"is_success": True, "message": "Coupon Offer created successfully!",
                                "response_data": data}, 201
        return msg, status_code

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
            return {"is_success": False, "message": "Primary Product Not Found", "response_data": None}, 406
        retailer_free_product = data['free_product_id']
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=retailer_free_product, shop=shop_id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Free Product Not Found", "response_data": None}, 406

        combo_offer_name, start_date, expiry_date, purchased_product_qty, free_product_qty = data['coupon_name'], data[
            'start_date'], data['end_date'], data['primary_product_qty'], data['free_product_qty']
        offer = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                     retailer_primary_product=retailer_primary_product_obj,
                                                     rule__coupon_ruleset__is_active=True)
        if offer:
            return {"is_success": False, "message": "Offer already exists for this Primary Product",
                    "response_data": None}, 406

        combo_code = f"Buy {purchased_product_qty} {retailer_primary_product_obj.name}" \
                     f" + Get {free_product_qty} {retailer_free_product_obj.name} Free"
        combo_rule_name = f"{shop_id}_{combo_code}"
        coupon_obj = OffersCls.rule_set_creation(combo_rule_name, start_date, expiry_date)
        if type(coupon_obj) == str:
            return {"is_success": False, "message": coupon_obj, "response_data": None}, 406

        OffersCls.rule_set_product_mapping(coupon_obj.id, retailer_primary_product_obj, purchased_product_qty,
                                           retailer_free_product_obj, free_product_qty, combo_offer_name, start_date,
                                           expiry_date)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'catalog', combo_offer_name, combo_code, shop,
                                                 start_date, expiry_date)
        data['id'] = coupon.id
        return {"is_success": True, "message": "Combo Offer created successfully!", "response_data": data}, 201

    @staticmethod
    def create_free_product_offer(data, shop_id):
        """
            Cart Free Product
        """
        shop, free_product = Shop.objects.filter(id=shop_id).last(), data['free_product_id']
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=free_product, shop=shop_id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Free product not found", "response_data": None}, 406

        coupon_name, discount_amount, start_date, expiry_date, free_product_qty = data['coupon_name'], data[
            'order_value'], data['start_date'], data['end_date'], data['free_product_qty']
        coupon_rule_discount_amount = Coupon.objects.filter(rule__cart_qualifying_min_sku_value=discount_amount,
                                                            shop=shop_id, rule__coupon_ruleset__is_active=True)
        if coupon_rule_discount_amount:
            return {"is_success": False, "message": f"Offer already exists for Order Value {discount_amount}",
                    "response_data": None}, 406

        coupon_rule_product_qty = Coupon.objects.filter(rule__free_product=retailer_free_product_obj,
                                                        rule__free_product_qty=free_product_qty,
                                                        shop=shop_id, rule__coupon_ruleset__is_active=True)
        if coupon_rule_product_qty:
            return {"is_success": False,
                    "message": "Offer already exists for same quantity of free product. Please check.",
                    "response_data": None}, 406

        rule_name = f"{shop_id}_{retailer_free_product_obj.name}_{free_product_qty}"
        coupon_code = f"{free_product_qty} {retailer_free_product_obj.name} free on orders above Rs. {discount_amount}"
        coupon_obj = OffersCls.rule_set_creation(rule_name, start_date, expiry_date, discount_amount, None,
                                                 retailer_free_product_obj, free_product_qty)
        if type(coupon_obj) == str:
            return {"is_success": False, "message": coupon_obj, "response_data": None}, 406
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', coupon_name, coupon_code, shop, start_date,
                                                 expiry_date)
        data['id'] = coupon.id
        return {"is_success": True, "message": "Free Product Offer Created Successfully!", "response_data": data}, 201

    @staticmethod
    def update_coupon(data, shop_id):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Coupon Id Invalid", "response_data": None}, 406
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Coupon RuleSet not found", "response_data": None}, 500
        try:
            discount = DiscountValue.objects.get(id=rule.discount.id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Discount Obj Not Found", "response_data": None}, 500

        coupon.coupon_name = data['coupon_name'] if 'coupon_name' in data else coupon.coupon_name
        if 'start_date' in data:
            rule.start_date = coupon.start_date = data['start_date']
        if 'end_date' in data:
            rule.expiry_date = coupon.expiry_date = data['end_date']
        if 'is_active' in data:
            rule.is_active = coupon.is_active = data['is_active']
        rule.save()
        discount.save()
        coupon.save()
        return {"is_success": True, "message": "Coupon Offer Updated Successfully!", "response_data": None}, 200

    @staticmethod
    def update_combo(data, shop_id):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Offer Not Found", "response_data": None}, 406
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Coupon RuleSet not Found", "response_data": None}, 500
        try:
            rule_set_product_mapping = RuleSetProductMapping.objects.get(rule=coupon.rule)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Product mapping Not Found with Offer", "response_data": None}, 500

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
        return {"is_success": True, "message": "Combo Offer Updated Successfully!", "response_data": None}, 200

    @staticmethod
    def update_free_product_offer(data, shop_id):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Coupon Not Found", "response_data": None}, 406
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            return {"is_success": False, "message": "Coupon RuleSet Not Found", "response_data": None}, 500

        coupon.coupon_name = data['coupon_name'] if 'coupon_name' in data else coupon.coupon_name
        if 'start_date' in data:
            rule.start_date = coupon.start_date = data['start_date']
        if 'expiry_date' in data:
            rule.expiry_date = coupon.expiry_date = data['end_date']
        if 'is_active' in data:
            rule.is_active = coupon.is_active = data['is_active']
        rule.save()
        coupon.save()
        return {"is_success": True, "message": f"Free Product Offer Updated Successfully!", "response_data": None}, 200
