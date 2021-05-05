from decimal import Decimal
import logging
import json

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
from pos.common_functions import RetailerProductCls, OffersCls, serializer_error, get_response, get_shop_id_from_token

from .serializers import RetailerProductCreateSerializer, RetailerProductUpdateSerializer, \
    RetailerProductResponseSerializer, RetailerProductImageDeleteSerializer, CouponCodeSerializer, \
    FreeProductOfferSerializer, ComboDealsSerializer, CouponCodeUpdateSerializer, ComboDealsUpdateSerializer, \
    CouponRuleSetSerializer, CouponListSerializer, FreeProductUpdateSerializer
from pos.data_validation import validate_data_format
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
                message = {"is_success": True, "message": "Product has been successfully created!",
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
            GET API for CouponOfferEdit.
            Using CouponCodeSerializer for Coupon Coupon LIST and ComboDealsSerializer for Combo Offer LIST.
        """
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            combo_coupon_id = request.GET.get('id')
            if combo_coupon_id:
                coupon_offers = self.get_coupons_combo_offers_by_id(shop_id, combo_coupon_id)
            else:
                coupon_offers = self.get_coupons_combo_offers_list(request, shop_id)
            msg = {"is_success": True, "message": "Coupon/Offers Retrieved Successfully",
                   "response_data": coupon_offers}
            return Response(msg, status=200)
        else:
            msg = {'is_success': False, 'error_message': f"There is no shop available with (shop id : {shop_id}) ",
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def post(self, request, *args, **kwargs):
        """
        POST API for CouponOfferCreation.
        Using CouponCodeSerializer for Coupon Creation and ComboDealsSerializer for Combo Offer Creation.
        """
        msg = validate_data_format(request)
        if msg:
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            rule_type = request.data.get('rule_type')
            if int(rule_type) == 1:
                serializer = CouponCodeSerializer(data=request.data)
                if serializer.is_valid():
                    """
                       rule_type is Coupon Code Creating Coupon
                    """
                    try:
                        with transaction.atomic():
                            msg, status_code = self.create_coupon(request, serializer, shop_id)
                            return Response(msg, status=status_code.get("status_code"))
                    except Exception as e:
                        error_logger.error(e)
                        msg = {"is_success": False, "message": "something went wrong ",
                               "response_data": serializer.data}
                        return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    msg = serializer_error(serializer)
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

            elif int(rule_type) == 2:
                serializer = ComboDealsSerializer(data=request.data)
                if serializer.is_valid():
                    """
                       rule_type is Combo Deals Creating Combo Offer
                    """
                    try:
                        with transaction.atomic():
                            msg, status_code = self.create_combo_offer(request, serializer, shop_id)
                            return Response(msg, status=status_code.get("status_code"))
                    except Exception as e:
                        error_logger.error(e)
                        msg = {"is_success": False, "message": "something went wrong ",
                               "response_data": serializer.data}
                        return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    msg = serializer_error(serializer)
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

            elif int(rule_type) == 3:
                serializer = FreeProductOfferSerializer(data=request.data)
                if serializer.is_valid():
                    """
                       rule_type is Free Product Offer Creating FreeProductOffer
                    """
                    try:
                        with transaction.atomic():
                            msg, status_code = self.create_free_product_offer(serializer, shop_id)
                            return Response(msg, status=status_code.get("status_code"))
                    except Exception as e:
                        error_logger.error(e)
                        msg = {"is_success": False, "message": "something went wrong ",
                               "response_data": serializer.data}
                        return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    msg = serializer_error(serializer)
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        else:
            msg = {'is_success': False, 'error_message': f"There is no shop available with (shop id : {shop_id}) ",
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def put(self, request, *args, **kwargs):
        """
           PUT API for CouponOfferUpdation.
           Using CouponCodeSerializer for Coupon Updation and ComboDealsSerializer for Combo Offer Updation.
        """
        msg = validate_data_format(request)
        if msg:
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        shop_id = get_shop_id_from_token(request)
        if type(shop_id) == int:
            rule_type = request.data.get('rule_type')
            if int(rule_type) == 1:
                """
                  rule_type is Coupon Code updating Coupon
                """
                serializer = CouponCodeUpdateSerializer(data=request.data)
                if serializer.is_valid():
                    coupon_id = request.data.get('id')
                    if Coupon.objects.filter(id=coupon_id, shop=shop_id).exists():
                        try:
                            with transaction.atomic():
                                msg, status_code = self.update_coupon(request, coupon_id, serializer, shop_id)
                                return Response(msg, status=status_code.get("status_code"))
                        except Exception as e:
                            error_logger.error(e)
                            msg = {"is_success": False, "message": "something went wrong ",
                                   "response_data": serializer.data}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    else:
                        msg = {'is_success': False,
                               'error_message': f"There is no coupon available with (coupon id : {coupon_id}) "
                                                f"for the shop_id : {shop_id}",
                               'response_data': None}
                        return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    msg = serializer_error(serializer)
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

            if int(rule_type) == 2:
                """
                    rule_type is Combo Deals updating Combo Deals Offers
                """
                serializer = ComboDealsUpdateSerializer(data=request.data)
                if serializer.is_valid():
                    combo_offer_id = request.data.get('id')
                    if Coupon.objects.filter(id=combo_offer_id, shop=shop_id).exists():
                        try:
                            with transaction.atomic():
                                msg, status_code = self.update_combo(request, combo_offer_id, serializer, shop_id)
                                return Response(msg, status=status_code.get("status_code"))
                        except Exception as e:
                            error_logger.error(e)
                            msg = {"is_success": False, "message": "something went wrong ",
                                   "response_data": serializer.data}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    else:
                        msg = {'is_success': False,
                               'error_message': f"There is no combo offer available with (coupon id : {combo_offer_id}) "
                                                f"for the shop_id : {shop_id}",
                               'response_data': None}
                        return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    msg = serializer_error(serializer)
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

            if int(rule_type) == 3:
                """
                    rule_type is Combo Deals updating Combo Deals Offers
                """
                serializer = FreeProductUpdateSerializer(data=request.data)
                if serializer.is_valid():
                    coupon_id = request.data.get('id')
                    if Coupon.objects.filter(id=coupon_id, shop=shop_id).exists():
                        try:
                            with transaction.atomic():
                                msg, status_code = self.update_free_product_offer(coupon_id, serializer, shop_id)
                                return Response(msg, status=status_code.get("status_code"))
                        except Exception as e:
                            error_logger.error(e)
                            msg = {"is_success": False, "message": "something went wrong",
                                   "response_data": serializer.data}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    else:
                        msg = {'is_success': False,
                               'error_message': f"There is no combo offer available with (coupon id : {coupon_id}) "
                                                f"for the shop_id : {shop_id}",
                               'response_data': None}
                        return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    msg = serializer_error(serializer)
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

        else:
            msg = {'is_success': False, 'error_message': f"There is no shop available with (shop id : {shop_id})",
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def get_coupons_combo_offers_by_id(self, shop_id, combo_coupon_id):
        """
          Get Offers/Coupons
          Serialize Offers/Coupons
       """
        coupon_offers = CouponRuleSet.objects.filter(coupon_ruleset__shop=shop_id,
                                                     coupon_ruleset__id=combo_coupon_id)
        serializer = CouponRuleSetSerializer(coupon_offers, many=True)
        return serializer.data

    def get_coupons_combo_offers_list(self, request, shop_id):
        """
          Get Offers/Coupons
          Serialize Offers/Coupons
       """
        coupon = Coupon.objects.filter(shop=shop_id)
        if request.GET.get('search_text'):
            """
                 Get Offers/Coupons when search_text is given in params
            """
            coupon = coupon.filter(coupon_code__icontains=request.GET.get('search_text'))
        objects = self.pagination_class().paginate_queryset(coupon, self.request)
        serializer = CouponListSerializer(objects, many=True)
        """
            Pagination on Offers/Coupons
        """
        return serializer.data

    def create_coupon(self, request, serializer, shop_id):
        """
            Creating Discount, Ruleset & Coupon
        """
        shop = Shop.objects.filter(id=shop_id).last()
        coupon_name = request.data.get('coupon_name')
        start_date = request.data.get('start_date')
        expiry_date = request.data.get('expiry_date')
        discount_value = request.data.get('discount_value')
        discount_amount = request.data.get('discount_qty_amount')
        # creating Discount
        if request.data.get('is_percentage'):
            discount_obj = DiscountValue.objects.create(discount_value=discount_value,
                                                        max_discount=request.data.get('max_discount'),
                                                        is_percentage=True)
            # creating CouponRuleSet
            rule_set_name_with_shop_id = f"{shop_id}_on Spending {discount_amount} get {discount_value} % Off"
            coupon_code = f"Get {discount_value} % OFF on Spending {discount_amount} Rs"
        else:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value, is_percentage=False)
            # creating CouponRuleSet
            rule_set_name_with_shop_id = f"{shop_id}_on Spending {discount_amount} get {discount_value} Off"
            coupon_code = f"Get {discount_value} Rs OFF on Spending {discount_amount} Rs"

        coupon_obj = OffersCls.rule_set_creation(rule_set_name_with_shop_id, start_date, expiry_date, discount_amount,
                                                 discount_obj)
        if type(coupon_obj) == str:
            msg = {"is_success": False, "message": coupon_obj,
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        # creating Coupon with coupon_type(cart)
        OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', coupon_name, coupon_code,
                                        shop, start_date, expiry_date)
        msg = {"is_success": True, "message": "Coupon has been successfully created!",
               "response_data": serializer.data}
        status_code = {"status_code": 201}
        return msg, status_code

    def create_combo_offer(self, request, serializer, shop_id):
        """
            Creating Ruleset, RuleSetProductMapping & Coupon
        """
        shop = Shop.objects.filter(id=shop_id).last()
        retailer_primary_product = request.data.get('retailer_primary_product')
        try:
            retailer_primary_product_obj = RetailerProduct.objects.get(id=retailer_primary_product, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": f"{retailer_primary_product} Not Found",
                   "response_data": serializer.data},
            status_code = {"status_code": 404}
            return msg, status_code

        retailer_free_product = request.data.get('retailer_free_product')
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=retailer_free_product, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": f"{retailer_free_product} Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        combo_offer_name = request.data.get('combo_offer_name')
        start_date = request.data.get('start_date')
        expiry_date = request.data.get('expiry_date')
        purchased_product_qty = request.data.get('purchased_product_qty')
        free_product_qty = request.data.get('free_product_qty')

        # checking if offer already exist with retailer_primary_product,
        ruleset = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                       retailer_primary_product=retailer_primary_product_obj,
                                                       rule__coupon_ruleset__is_active=True)
        if ruleset:
            msg = {"is_success": False, "message": f"Offer already exist for SKU {retailer_primary_product_obj.sku} ",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        # checking if reverse offer exist,
        reverse_ruleset = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                               retailer_primary_product=retailer_free_product_obj,
                                                               retailer_free_product=retailer_primary_product_obj,
                                                               rule__coupon_ruleset__is_active=True)
        if reverse_ruleset:
            msg = {"is_success": False,
                   "message": f"reverse offer cannot be created {reverse_ruleset[0].rule.rulename} already exist)",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        # coupon_code creation for combo offers using retailer_primary_product, purchased_product_qty
        # retailer_free_product, free_product_qty
        combo_code = f"Buy {purchased_product_qty} {retailer_primary_product_obj.name}" \
                     f" + Get {free_product_qty} {retailer_free_product_obj.name} Free"
        # ruleset_name will be uniq.
        combo_ruleset_name = f"{shop_id}_{combo_code}"
        # creating CouponRuleSet
        coupon_obj = OffersCls.rule_set_creation(combo_ruleset_name, start_date, expiry_date)
        if type(coupon_obj) == str:
            msg = {"is_success": False, "message": coupon_obj,
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        # creating Combo Offer with primary & free products
        OffersCls.rule_set_product_mapping(coupon_obj.id, retailer_primary_product_obj, purchased_product_qty,
                                           retailer_free_product_obj, free_product_qty,
                                           combo_offer_name, start_date, expiry_date)
        # creating Coupon with coupon_type(catalog)
        OffersCls.rule_set_cart_mapping(coupon_obj.id, 'catalog', combo_offer_name, combo_code,
                                        shop, start_date, expiry_date)
        msg = {"is_success": True, "message": "Combo Offer has been successfully created!",
               "response_data": serializer.data}
        status_code = {"status_code": 201}
        return msg, status_code

    def create_free_product_offer(self, serializer, shop_id):
        """
            Creating Ruleset & Coupon
        """
        shop = Shop.objects.filter(id=shop_id).last()
        free_product = self.request.data.get('free_product')
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=free_product, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": f"retailer_free_product {free_product} Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        rulename = self.request.data.get('rulename')
        discount_amount = self.request.data.get('cart_qualifying_min_sku_value')
        start_date = self.request.data.get('start_date')
        expiry_date = self.request.data.get('expiry_date')
        free_product_qty = self.request.data.get('free_product_qty')
        # checking if offer already exist with retailer_free_product, discount_amount & free_product_qty
        coupon_ruleset_discount_amount = Coupon.objects.filter(rule__cart_qualifying_min_sku_value=discount_amount,
                                                               shop=shop_id, rule__coupon_ruleset__is_active=True)
        if coupon_ruleset_discount_amount:
            msg = {"is_success": False, "message": f"Offer already exist  for discount amount {discount_amount}",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        coupon_ruleset_product_qty = Coupon.objects.filter(rule__free_product=retailer_free_product_obj,
                                                           rule__free_product_qty=free_product_qty,
                                                           shop=shop_id, rule__coupon_ruleset__is_active=True)

        if coupon_ruleset_product_qty:
            msg = {"is_success": False, "message": f"Offer already exist for SKU {retailer_free_product_obj.sku} ",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        ruleset_name = f"{shop_id}_{retailer_free_product_obj.name}_{free_product_qty}"
        coupon_code = f"Get {free_product_qty} {retailer_free_product_obj.name} " \
                      f"Free on Spending {discount_amount} Rs"
        # creating CouponRuleSet
        coupon_obj = OffersCls.rule_set_creation(ruleset_name, start_date, expiry_date, discount_amount, None,
                                                 retailer_free_product_obj, free_product_qty)
        if type(coupon_obj) == str:
            msg = {"is_success": False, "message": coupon_obj,
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        # creating Coupon with coupon_type(cart)
        OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', rulename, coupon_code,
                                        shop, start_date, expiry_date)
        msg = {"is_success": True, "message": "Free Product Offer has been successfully created!",
               "response_data": serializer.data}
        status_code = {"status_code": 201}
        return msg, status_code

    def update_coupon(self, request, coupon_id, serializer, shop_id):
        """
            Updating Discount, Ruleset & Coupon
        """
        try:
            coupon = Coupon.objects.get(id=coupon_id, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "coupon Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code
        try:
            coupon_ruleset = CouponRuleSet.objects.get(id=coupon.rule.id)
        except:
            msg = {"is_success": False, "error": "coupon rulest not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code
        try:
            discount = DiscountValue.objects.get(id=coupon_ruleset.discount.id)
        except:
            msg = {"is_success": False, "error": "discount value not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        expected_input_data_list = ['id', 'coupon_name', 'discount_qty_amount', 'discount_value', 'start_date',
                                    'expiry_date', 'is_active', 'is_percentage', 'max_discount']
        actual_input_data_list = []
        for key in expected_input_data_list:
            if key in request.data.keys():
                actual_input_data_list.append(key)

        if 'coupon_name' in actual_input_data_list:
            # If coupon_name in actual_input_data_list
            coupon_name = request.data.get('coupon_name')
            coupon.coupon_name = coupon_name

        if 'discount_qty_amount' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount_amount = request.data.get('discount_qty_amount')
            coupon_ruleset.cart_qualifying_min_sku_value = discount_amount

        if 'discount_value' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount_value = request.data.get('discount_value')
            discount.discount_value = discount_value

        if 'is_percentage' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount.is_percentage = request.data.get('is_percentage')
        if 'max_discount' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount.max_discount = request.data.get('max_discount')

        if 'discount_qty_amount' or 'discount_value' in actual_input_data_list:
            # If discount_qty_amount or discount_value in actual_input_data_list
            if discount.is_percentage:
                rulename = f"{shop_id}_on Spending {coupon_ruleset.cart_qualifying_min_sku_value} get {discount.discount_value} % Off"
                coupon.coupon_code = f"Get {discount.discount_value} % OFF on Spending {coupon_ruleset.cart_qualifying_min_sku_value} Rs"
            else:
                rulename = f"{shop_id}_on Spending {coupon_ruleset.cart_qualifying_min_sku_value} get {discount.discount_value} Off"
                coupon.coupon_code = f"Get {discount.discount_value} Rs OFF on Spending {coupon_ruleset.cart_qualifying_min_sku_value} Rs"

            coupon_ruleset_name = CouponRuleSet.objects.filter(rulename=rulename). \
                exclude(id=coupon_ruleset.id)

            if coupon_ruleset_name:
                msg = {"is_success": False,
                       "message": f"Offer already exist for ruleset_name {rulename} ",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            coupon_ruleset.rulename = rulename

        if 'start_date' in actual_input_data_list:
            # If start_date in actual_input_data_list
            coupon_ruleset.start_date = request.data.get('start_date')
            coupon.start_date = request.data.get('start_date')
        if 'expiry_date' in actual_input_data_list:
            # If expiry_date in actual_input_data_list
            coupon_ruleset.expiry_date = request.data.get('expiry_date')
            coupon.expiry_date = request.data.get('expiry_date')
        if 'is_active' in actual_input_data_list:
            # If is_active in actual_input_data_list
            coupon_ruleset.is_active = request.data.get('is_active')
            coupon.is_active = request.data.get('is_active')

        coupon_ruleset.save()
        discount.save()
        coupon.save()
        msg = {"is_success": True, "message": f"Coupon has been successfully UPDATED!",
               "response_data": serializer.data}
        status_code = {"status_code": 201}
        return msg, status_code

    def update_combo(self, request, combo_id, serializer, shop_id):
        """
            Updating Ruleset, RuleSetProductMapping & Coupon
        """
        try:
            coupon = Coupon.objects.get(id=combo_id, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "Offer Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code
        try:
            coupon_ruleset = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "Offer Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code
        try:
            rule_set_product_mapping = RuleSetProductMapping.objects.get(rule=coupon.rule)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "Offer Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code
        expected_input_data_list = ['id', 'combo_offer_name', 'expiry_date', 'start_date',
                                    'retailer_primary_product', 'retailer_free_product', 'purchased_product_qty',
                                    'free_product_qty']
        actual_input_data_list = []
        for key in expected_input_data_list:
            if key in request.data.keys():
                actual_input_data_list.append(key)

        if 'combo_offer_name' in actual_input_data_list:
            # If coupon_name in actual_input_data_list
            combo_offer_name = request.data.get('combo_offer_name')
            coupon.coupon_name = combo_offer_name
        if 'start_date' in actual_input_data_list:
            # If start_date in actual_input_data_list
            coupon_ruleset.start_date = request.data.get('start_date')
            rule_set_product_mapping.start_date = request.data.get('start_date')
            coupon.start_date = request.data.get('start_date')
        if 'expiry_date' in actual_input_data_list:
            # If expiry_date in actual_input_data_list
            coupon_ruleset.expiry_date = request.data.get('expiry_date')
            rule_set_product_mapping.expiry_date = request.data.get('expiry_date')
            coupon.expiry_date = request.data.get('expiry_date')
        if 'retailer_primary_product' in actual_input_data_list:
            # If retailer_primary_product in actual_input_data_list
            retailer_primary_product = request.data.get('retailer_primary_product')
            try:
                retailer_primary_product_obj = RetailerProduct.objects.get(id=retailer_primary_product, shop=shop_id)
            except ObjectDoesNotExist:
                msg = {"is_success": False, "error": "retailer_primary_product Not Found",
                       "response_data": serializer.data,
                       },
                status_code = {"status_code": 404}
                return msg, status_code

            ruleset = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                           retailer_primary_product=retailer_primary_product_obj,
                                                           rule__coupon_ruleset__is_active=True).\
                exclude(id=rule_set_product_mapping.id)
            if ruleset:
                msg = {"is_success": False, "message": f"Offer already exist for  {retailer_primary_product_obj.sku}",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            # checking if reverse offer exist,
            reverse_ruleset = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                                   retailer_primary_product=rule_set_product_mapping.
                                                                   retailer_free_product.id,
                                                                   retailer_free_product=retailer_primary_product_obj,
                                                                   rule__coupon_ruleset__is_active=True)
            if reverse_ruleset:
                msg = {"is_success": False,
                       "message": f"reverse offer cannot be updated {reverse_ruleset[0].rule.rulename} already exist)",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            rule_set_product_mapping.retailer_primary_product = retailer_primary_product_obj
            # update ruleset_name & combo_code with existing ruleset_name , retailer_free_product name,
            # purchased_product_qty & free_product_qty
            combo_code = f"Buy {rule_set_product_mapping.purchased_product_qty} {retailer_primary_product_obj.name}" \
                         f" + Get {rule_set_product_mapping.free_product_qty} {rule_set_product_mapping.retailer_free_product.name} Free"

            coupon.coupon_code = combo_code
            coupon_ruleset.rulename = f"{shop_id}_{combo_code}"

        if 'retailer_free_product' in actual_input_data_list:
            # If retailer_free_product in actual_input_data_list
            retailer_free_product = request.data.get('retailer_free_product')
            try:
                retailer_free_product_obj = RetailerProduct.objects.get(id=retailer_free_product, shop=shop_id)
            except ObjectDoesNotExist:
                msg = {"is_success": False, "error": "retailer_free_product Not Found",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            # checking if reverse offer exist,
            reverse_ruleset = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                                   retailer_primary_product=retailer_free_product_obj,
                                                                   retailer_free_product=rule_set_product_mapping.
                                                                   retailer_primary_product.id,
                                                                   rule__coupon_ruleset__is_active=True)
            if reverse_ruleset:
                msg = {"is_success": False,
                       "message": f"reverse offer cannot be updated {reverse_ruleset[0].rule.rulename} already exist)",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            rule_set_product_mapping.retailer_free_product = retailer_free_product_obj
            # update ruleset_name & combo_code with existing ruleset_name , retailer_primary_product name,
            # purchased_product_qty & free_product_qty
            combo_code = f"Buy {rule_set_product_mapping.purchased_product_qty} {rule_set_product_mapping.retailer_primary_product.name}" \
                         f" + Get {rule_set_product_mapping.free_product_qty} {retailer_free_product_obj.name} Free"

            coupon.coupon_code = combo_code
            coupon_ruleset.rulename = f"{shop_id}_{combo_code}"

        if 'purchased_product_qty' in actual_input_data_list:
            # If purchased_product_qty in actual_input_data_list
            rule_set_product_mapping.purchased_product_qty = request.data.get('purchased_product_qty')
            # update combo_code with existing ruleset_name , retailer_primary_product, retailer_free_product name,
            #  & free_product_qty
            combo_code = f"Buy {request.data.get('purchased_product_qty')} {rule_set_product_mapping.retailer_primary_product.name}" \
                         f" + Get {rule_set_product_mapping.free_product_qty} {rule_set_product_mapping.retailer_free_product.name} Free"

            coupon.coupon_code = combo_code
            coupon_ruleset.rulename = f"{shop_id}_{combo_code}"

        if 'free_product_qty' in actual_input_data_list:
            # If free_product_qty in actual_input_data_list
            rule_set_product_mapping.free_product_qty = request.data.get('free_product_qty')
            # update combo_code with existing ruleset_name , retailer_primary_product, retailer_free_product name,
            #  & purchased_product_qty
            combo_code = f"Buy {rule_set_product_mapping.purchased_product_qty} {rule_set_product_mapping.retailer_primary_product.name}" \
                         f" + Get {request.data.get('free_product_qty')} {rule_set_product_mapping.retailer_free_product.name} Free"

            coupon.coupon_code = combo_code
            coupon_ruleset.rulename = f"{shop_id}_{combo_code}"

        if 'is_active' in actual_input_data_list:
            # If is_active in actual_input_data_list
            rule_set_product_mapping.is_active = request.data.get('is_active')
            coupon_ruleset.is_active = request.data.get('is_active')
            coupon.is_active = request.data.get('is_active')

        coupon_ruleset.save()
        rule_set_product_mapping.save()
        coupon.save()

        msg = {"is_success": True, "message": f"Combo Offer has been successfully UPDATED!",
               "response_data": serializer.data}
        status_code = {"status_code": 201}
        return msg, status_code

    def update_free_product_offer(self, coupon_id, serializer, shop_id):
        """
            Updating Discount, Ruleset & Coupon
        """
        try:
            coupon = Coupon.objects.get(id=coupon_id, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "coupon Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code
        coupon_ruleset = CouponRuleSet.objects.get(id=coupon.rule.id)

        expected_input_data_list = ['id', 'rulename', 'start_date', 'expiry_date', 'free_product',
                                    'cart_qualifying_min_sku_value', 'free_product_qty', 'is_active']
        actual_input_data_list = []
        for key in expected_input_data_list:
            if key in self.request.data.keys():
                actual_input_data_list.append(key)

        if 'rulename' in actual_input_data_list:
            # If coupon_name in actual_input_data_list
            coupon.coupon_name = self.request.data.get('rulename')
        if 'cart_qualifying_min_sku_value' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount_amount = self.request.data.get('cart_qualifying_min_sku_value')
            # checking if offer already exist with retailer_free_product, discount_qty_amount
            coupon_ruleset_qty = Coupon.objects.filter(rule__cart_qualifying_min_sku_value=discount_amount,
                                                       shop=shop_id, rule__coupon_ruleset__is_active=True).\
                exclude(id=coupon.id)
            if coupon_ruleset_qty:
                msg = {"is_success": False, "message": f"Offer already exist for discount amount {discount_amount} ",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            coupon_ruleset.cart_qualifying_min_sku_value = discount_amount
            coupon_code = f"Get {coupon_ruleset.free_product_qty} {coupon_ruleset.free_product.name} " \
                          f"Free on Spending {discount_amount} Rs"
            coupon.coupon_code = coupon_code
        if 'free_product' in actual_input_data_list:
            # If retailer_free_product in actual_input_data_list
            retailer_free_product = self.request.data.get('free_product')
            try:
                retailer_free_product_obj = RetailerProduct.objects.get(id=retailer_free_product, shop=shop_id)
            except ObjectDoesNotExist:
                msg = {"is_success": False, "error": f" {retailer_free_product} Not Found",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code
            if not 'free_product_qty' in actual_input_data_list:
                coupon_ruleset_product = Coupon.objects.filter(rule__free_product=retailer_free_product_obj,
                                                               rule__free_product_qty=coupon_ruleset.free_product_qty,
                                                               shop=shop_id, rule__coupon_ruleset__is_active=True).\
                    exclude(id=coupon.id)

                if coupon_ruleset_product:
                    msg = {"is_success": False,
                           "message": f"Offer already exist for SKU {coupon_ruleset.free_product.sku} with "
                                      f"free_product_qty {coupon_ruleset.free_product_qty}",
                           "response_data": serializer.data}
                    status_code = {"status_code": 404}
                    return msg, status_code

            coupon_ruleset.free_product = retailer_free_product_obj
            ruleset_name = f"{shop_id}_{retailer_free_product_obj.name}_{coupon_ruleset.free_product_qty}"
            coupon_code = f"Get {coupon_ruleset.free_product_qty} {retailer_free_product_obj.name} " \
                          f"Free on Spending {coupon_ruleset.cart_qualifying_min_sku_value} Rs"

            if CouponRuleSet.objects.filter(rulename=ruleset_name).exclude(id=coupon_ruleset.id):
                msg = {"is_success": False,
                       "message": f"cannot create a Offer with {ruleset_name}, already exists",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            coupon_ruleset.rulename = ruleset_name
            coupon.coupon_code = coupon_code

        if 'free_product_qty' in actual_input_data_list:
            # If free_product_qty in actual_input_data_list
            free_product_qty = self.request.data.get('free_product_qty')
            coupon_ruleset_qty = Coupon.objects.filter(rule__free_product=coupon_ruleset.free_product,
                                                       rule__free_product_qty=free_product_qty,
                                                       shop=shop_id, rule__coupon_ruleset__is_active=True).\
                exclude(id=coupon.id)
            if coupon_ruleset_qty:
                msg = {"is_success": False,
                       "message": f"Offer already exist for SKU {coupon_ruleset.free_product.sku} with "
                                  f"free_product_qty {free_product_qty} ",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            coupon_ruleset.free_product_qty = free_product_qty
            ruleset_name = f"{shop_id}_{coupon_ruleset.free_product.name}_{free_product_qty}"
            coupon_code = f"Get {free_product_qty} {coupon_ruleset.free_product.name} " \
                          f"Free on Spending {coupon_ruleset.cart_qualifying_min_sku_value} Rs"

            if CouponRuleSet.objects.filter(rulename=ruleset_name).exclude(id=coupon_ruleset.id):
                msg = {"is_success": False,
                       "message": f"cannot create a Offer with {ruleset_name}, already exists",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            coupon_ruleset.rulename = ruleset_name
            coupon.coupon_code = coupon_code

        if 'start_date' in actual_input_data_list:
            # If start_date in actual_input_data_list
            coupon_ruleset.start_date = self.request.data.get('start_date')
            coupon.start_date = self.request.data.get('start_date')
        if 'expiry_date' in actual_input_data_list:
            # If expiry_date in actual_input_data_list
            coupon_ruleset.expiry_date = self.request.data.get('expiry_date')
            coupon.expiry_date = self.request.data.get('expiry_date')
        if 'is_active' in actual_input_data_list:
            # If is_active in actual_input_data_list
            coupon_ruleset.is_active = self.request.data.get('is_active')
            coupon.is_active = self.request.data.get('is_active')

        coupon_ruleset.save()
        coupon.save()
        msg = {"is_success": True, "message": f"FreeProduct Offer has been successfully UPDATED!",
               "response_data": serializer.data}
        status_code = {"status_code": 201}
        return msg, status_code
