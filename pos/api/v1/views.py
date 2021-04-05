import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from django.db import transaction
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.core import validators
from django.db.models import Q
from rest_framework.parsers import JSONParser
from rest_framework import status, authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .pagination import pagination
from sp_to_gram.tasks import es_search
from audit.views import BlockUnblockProduct
from retailer_to_sp.api.v1.serializers import CartSerializer, GramMappedCartSerializer, ParentProductImageSerializer, \
    GramMappedOrderSerializer, OrderSerializer, OrderDetailSerializer, OrderListSerializer
from retailer_backend.common_function import getShopMapping
from retailer_backend.messages import ERROR_MESSAGES
from wms.common_functions import get_stock, OrderManagement
from accounts.models import User
from wms.models import InventoryType, OrderReserveRelease
from products.models import Product

from retailer_to_sp.models import Cart, CartProductMapping, Order, check_date_range, capping_check, OrderedProduct, \
    OrderedProductMapping, OrderedProductBatch, OrderReturn, ReturnItems
from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping,
                                     Order as GramMappedOrder)
from shops.models import Shop
from gram_to_brand.models import (OrderedProductReserved as GramOrderedProductReserved, PickList)
from sp_to_gram.models import OrderedProductReserved
from addresses.models import Address

from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon
from pos.models import RetailerProduct, Payment, PAYMENT_MODE, UserMappedShop, RetailerProductImage

from pos.common_functions import RetailerProductCls, OffersCls, get_shop_id_from_token, serializer_error, \
    get_response, delete_cart_mapping, order_search, get_response, get_invoice_and_link, delete_cart_mapping, \
    order_search, create_user_shop_mapping, get_shop_id_from_token
from .serializers import BasicCartSerializer, BasicOrderSerializer, CheckoutSerializer, \
    BasicOrderListSerializer, OrderedDashBoardSerializer, BasicCartListSerializer, OrderReturnCheckoutSerializer,\
    RetailerProductCreateSerializer, RetailerProductUpdateSerializer, \
    RetailerProductResponseSerializer, CouponCodeSerializer, FreeProductOfferSerializer, ComboDealsSerializer,\
    CouponCodeUpdateSerializer, ComboDealsUpdateSerializer, CouponRuleSetSerializers, CouponListSerializers,\
    RetailerProductImageDeleteSerializers, FreeProductUpdateSerializer

from pos.utils import MultipartJsonParser
from pos.offers import BasicCartOffers


# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')

POS_SERIALIZERS_MAP = {
    0: RetailerProductCreateSerializer,
    1: RetailerProductUpdateSerializer,
    2: RetailerProductImageDeleteSerializers
}

ORDER_STATUS_MAP = {
    1: Order.ORDERED,
    2: Order.CANCELLED,
    3: Order.PARTIALLY_REFUNDED,
    4: Order.FULLY_REFUNDED
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
                                                          selling_price=selling_price).exists():
                            msg = {"is_success": False,
                                   "message": "Product {} with mrp {} & selling_price {} already exist."
                                       .format(product.name, mrp, selling_price),
                                   "response_data": None}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif mrp:
                        # if only mrp is there in edit product request
                        # checking if product already exist, through error
                        if RetailerProduct.objects.filter(shop_id=shop_id_or_error_message, name=product.name, mrp=mrp,
                                                          selling_price=product.selling_price).exists():
                            msg = {"is_success": False,
                                   "message": "Product {} with mrp {} & selling_price {} already exist."
                                       .format(product.name, mrp, product.selling_price),
                                   "response_data": None}
                            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif selling_price:
                        # if only selling_price is there in edit product request
                        # checking if product already exist, through error
                        if RetailerProduct.objects.filter(shop_id=shop_id_or_error_message, name=product.name, mrp=product.mrp,
                                                          selling_price=selling_price).exists():
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


class OrderListCentral(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
            Get Order List
            Inputs
            cart_type
            shop_id
        """
        cart_type = request.GET.get('cart_type')
        if cart_type == '1':
            return self.get_retail_order_list()
        elif cart_type == '2':
            return self.get_basic_order_list()
        else:
            return get_response('Provide a valid cart_type')

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
        order = self.get_retail_order(shop_type, parent_mapping)
        return {'parent_mapping': parent_mapping, 'shop_type': shop_type, 'order': order}

    def get_retail_order(self, shop_type, parent_mapping):
        """
           Get Retail Orders
        """
        search_text = self.request.GET.get('search_text')
        order_status = self.request.GET.get('order_status')
        if shop_type == 'sp':
            orders = Order.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
            if order_status:
                orders = orders.filter(order_status=order_status)
            if search_text:
                order = order_search(orders, search_text)
            else:
                order = orders
        elif shop_type == 'gf':
            orders = GramMappedOrder.objects.filter(buyer_shop=parent_mapping.retailer).order_by('-created_at')
            if order_status:
                orders = orders.filter(order_status=order_status)
            if search_text:
                order = order_search(orders, search_text)
            else:
                order = orders
        return order

    def get_retail_order_list(self):
        """
            Get Order
            For retail cart
        """
        # basic validations for inputs
        initial_validation = self.get_retail_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        parent_mapping = initial_validation['parent_mapping']
        shop_type = initial_validation['shop_type']
        order = initial_validation['order']
        if shop_type == 'sp':
            return get_response('Order', self.get_serialize_process_sp(order, parent_mapping))
        elif shop_type == 'gf':
            return get_response('Order', self.get_serialize_process_gf(order, parent_mapping))
        else:
            return get_response('Sorry shop is not associated with any GramFactory or any SP')

    def get_basic_order_list(self):
        """
            Get Order
            For Basic Cart
        """
        # basic validation for inputs
        initial_validation = self.get_basic_list_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        return get_response('Order', self.get_serialize_process_basic(order))

    def get_basic_list_validate(self):
        """
           Get Order
           Input validation for cart type 'basic'
        """
        # Check if seller shop exist
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # get order list
        order = self.get_basic_order(shop_id)
        return {'order': order}

    def get_basic_order(self, shop_id):
        """
          Get Basic Orders
        """
        search_text = self.request.GET.get('search_text')
        order_status = self.request.GET.get('order_status')
        orders = Order.objects.filter(seller_shop_id=shop_id)
        if order_status:
            order_status_actual = ORDER_STATUS_MAP.get(int(order_status), None)
            orders = orders.filter(order_status=order_status_actual) if order_status_actual else orders
        if search_text:
            order = order_search(orders, search_text)
        else:
            order = orders
        return order

    def get_serialize_process_sp(self, order, parent_mapping):
        """
           Get Order
           Cart type retail - sp
        """
        serializer = OrderListSerializer(order, many=True,
                                         context={'parent_mapping_id': parent_mapping.parent.id,
                                                  'current_url': self.request.get_host(),
                                                  'buyer_shop_id': parent_mapping.retailer.id})
        """
            Pagination on Order List
        """
        return pagination(self.request, serializer)

    def get_serialize_process_gf(self, order, parent_mapping):
        """
           Get Order
           Cart type retail - gf
        """
        serializer = GramMappedOrderSerializer(order, many=True,
                                               context={'parent_mapping_id': parent_mapping.parent.id,
                                                        'current_url': self.request.get_host(),
                                                        'buyer_shop_id': parent_mapping.retailer.id})
        """
            Pagination on Order List
        """
        return pagination(self.request, serializer)

    def get_serialize_process_basic(self, order):
        """
           Get Order
           Cart type basic
        """
        serializer = BasicOrderListSerializer(order, many=True)
        """
            Pagination on Order List
        """
        return pagination(self.request, serializer)


class OrderedItemCentralDashBoard(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
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
            return self.get_basic_order_overview()
        else:
            return get_response('Provide a valid app_type')

    def get_basic_order_overview(self):
        """
            Get Shop Name, Order, Product, & User Counts
            For Basic Cart
        """
        # basic validation for inputs
        initial_validation = self.get_basic_list_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        return get_response('Order Details', self.get_serialize_process(order))

    def get_basic_list_validate(self):
        """
           Input validation for cart type 'basic'
        """
        # Check if seller shop exist
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        # get a order_overview
        order = self.get_basic_orders_count(shop_id)
        return {'order': order}

    def get_basic_orders_count(self, shop_id):
        """
          Get Basic Order Overview based on filters
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

        # get total orders for shop_id
        orders = Order.objects.filter(seller_shop=shop_id)
        # get total products for shop_id
        products = RetailerProduct.objects.filter(shop=shop_id)
        # get total users registered with shop_id
        users = UserMappedShop.objects.filter(shop_id=shop_id)

        if order_status:
            order_status_actual = ORDER_STATUS_MAP.get(int(order_status), None)
            # get total orders for given shop_id & order_status
            orders = orders.filter(order_status=order_status_actual) if order_status_actual else orders

        # filter order, product & user by get modified date
        if filters == 1:  # today
            # filter order, product & user on modified date today
            orders = orders.filter(modified_at__date=today)
            products = products.filter(modified_at__date=today)
            users = users.filter(modified_at__date=today)

        elif filters == 2:  # yesterday
            # filter order, product & user on modified date yesterday
            yesterday = today - timedelta(days=1)
            orders = orders.filter(modified_at__date=yesterday)
            products = products.filter(modified_at__date=yesterday)
            users = users.filter(modified_at__date=yesterday)

        elif filters == 3:  # lastweek
            # filter order, product & user on modified date lastweek
            lastweek = today - timedelta(weeks=1)
            orders = orders.filter(modified_at__week=lastweek.isocalendar()[1])
            products = products.filter(modified_at__week=lastweek.isocalendar()[1])
            users = users.filter(modified_at__week=lastweek.isocalendar()[1])

        elif filters == 4:  # lastmonth
            # filter order, product & user on modified date lastmonth
            lastmonth = today - timedelta(days=30)
            orders = orders.filter(modified_at__month=lastmonth.month)
            products = products.filter(modified_at__month=lastmonth.month)
            users = users.filter(modified_at__month=lastmonth.month)

        elif filters == 5:  # lastyear
            # filter order, product & user on modified date lastyear
            lastyear = today - timedelta(days=365)
            orders = orders.filter(modified_at__year=lastyear.year)
            products = products.filter(modified_at__year=lastyear.year)
            users = users.filter(modified_at__year=lastyear.year)

        total_final_amount = 0
        for order in orders:
            # total final amount calculation
            total_final_amount += order.total_final_amount

        # counts of order for shop_id with total_final_amount, users, & products
        order_count = orders.count()
        users_count = users.count()
        products_count = products.count()
        shop = Shop.objects.get(id=shop_id)
        overview = [{"shop_name": shop.shop_name, "orders": order_count,
                     "registered_users": users_count, "products": products_count,
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
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        return get_response('Order Details', self.get_serialize_process(order))

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
            total_final_amount += order.total_final_amount

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

    def post(self, request):
        """
            Returns for any order
            Inputs
            order_id
            return_items - dict - product_id, qty
            refund_amount
        """
        # Input validation
        initial_validation = self.post_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        return_items = initial_validation['return_items']
        return_reason = initial_validation['return_reason']
        with transaction.atomic():
            # map all products to combo offers in cart
            product_combo_map = self.get_combo_offers(order)
            # initiate / update return for order
            order_return = self.update_return(order, return_reason)
            # To map free products to their return quantity
            free_returns = {}
            free_qty_product_map = []
            new_cart_value = 0
            ordered_product = OrderedProduct.objects.get(order=order)
            all_products = ordered_product.rt_order_product_order_product_mapping.filter(product_type=1).values_list('retailer_product_id', flat=True)
            given_products = []
            # for each purchased product add/remove returns according to quantity provided
            for return_product in return_items:
                product_validate = self.validate_product(ordered_product, return_product)
                if 'error' in product_validate:
                    return get_response(product_validate['error'])
                product_id = product_validate['product_id']
                ordered_product_map = product_validate['ordered_product_map']
                return_qty = product_validate['return_qty']
                given_products += [product_id]
                # if return quantity of product is greater than zero
                if return_qty > 0:
                    self.return_item(order_return, ordered_product_map, return_qty)
                    if product_id in product_combo_map:
                        new_prod_qty = ordered_product_map.shipped_qty - return_qty
                        for offer in product_combo_map[product_id]:
                            purchased_product_multiple = int(int(new_prod_qty) / int(offer['item_qty']))
                            new_free_item_qty = int(purchased_product_multiple * int(offer['free_item_qty']))
                            return_free_qty = offer['free_item_qty_added'] - new_free_item_qty
                            free_qty_product_map.append(
                                self.get_free_item_map(product_id, offer['free_item_id'], return_free_qty))
                            free_returns = self.get_updated_free_returns(free_returns, offer['free_item_id'],
                                                                         return_free_qty)
                else:
                    ReturnItems.objects.filter(return_id=order_return, ordered_product=ordered_product_map).delete()
                    if product_id in product_combo_map:
                        for offer in product_combo_map[product_id]:
                            free_returns = self.get_updated_free_returns(free_returns, offer['free_item_id'], 0)
                new_cart_value += (ordered_product_map.shipped_qty - return_qty) * ordered_product_map.selling_price
            for id in all_products:
                if id not in given_products:
                    return get_response("Please provide product {}".format(id) + " in return items")
            # check and update refund amount
            self.update_refund_amount(order, new_cart_value, order_return)
            self.process_free_products(ordered_product, order_return, free_returns)
            order_return.free_qty_map = free_qty_product_map
            order_return.save()
        return get_response("Order Return", BasicOrderSerializer(order, context={'current_url': self.request.get_host(),
                                                                                 'invoice': 1}).data)

    def post_validate(self):
        """
            Validate order return creation
        """
        # check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {"error": "Shop Doesn't Exist!"}
        return_items = self.request.data.get('return_items')
        if not return_items:
            return {'error': "Provide return item details"}
        # check if order exists
        order_id = self.request.data.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, seller_shop_id=shop_id, order_status='ordered')
        except ObjectDoesNotExist:
            return {'error': "Order Does Not Exist"}
        # check return reason is valid
        return_reason = self.request.data.get('return_reason', '')
        if return_reason and return_reason not in dict(OrderReturn.RETURN_REASON):
            return {'error': 'Provide a valid return reason'}
        return {'order': order, 'return_reason': return_reason, 'return_items': return_items}

    def update_refund_amount(self, order, new_cart_value, order_return):
        """
            Calculate refund amount
            Check offers applied on order
            Remove coupon if new cart value does not qualify for offer
            Remove spot discount if discount exceeds new cart value
        """
        # previous offer on order
        order_offer = {}
        applied_offers = order.ordered_cart.offers
        if applied_offers:
            for offer in applied_offers:
                if offer['coupon_type'] == 'cart' and offer['applied']:
                    order_offer = self.modify_applied_cart_offer(offer, new_cart_value)
        discount = order_offer['discount_value'] if order_offer else 0
        refund_amount = round(float(order.total_final_amount) - float(new_cart_value) + discount, 2)
        refund_amount_provided = self.request.data.get('refund_amount')
        if refund_amount_provided and refund_amount_provided <= refund_amount:
            refund_amount = refund_amount_provided
        order_return.refund_amount = refund_amount
        order_return.offers = [order_offer] if order_offer else []
        order_return.save()

    def modify_applied_cart_offer(self, offer, new_cart_value):
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

    def get_combo_offers(self, order):
        """
            Get combo offers mapping with product purchased
        """
        offers = order.ordered_cart.offers
        product_combo_map = {}
        if offers:
            for offer in offers:
                if offer['type'] == 'combo':
                    product_combo_map[offer['item_id']] = product_combo_map[offer['item_id']] + [offer] \
                        if offer['item_id'] in product_combo_map else [offer]
        return product_combo_map

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
        order_return, _ = OrderReturn.objects.get_or_create(order=order)
        order_return.processed_by = self.request.user
        order_return.return_reason = return_reason
        order_return.save()
        return order_return

    def validate_product(self, ordered_product, return_product):
        """
            Validate return detail - product_id, qty, amt (refund amount) - provided for a product
        """
        # product id
        if 'product_id' not in return_product:
            return {'error': "Provide product ids"}
        product_id = return_product['product_id']
        # return qty
        if 'qty' not in return_product or return_product['qty'] < 0:
            return {'error': "Return qty not provided / invalid for product {}".format(product_id)}
        return_qty = return_product['qty']
        # ordered product
        try:
            ordered_product_map = OrderedProductMapping.objects.get(ordered_product=ordered_product, product_type=1,
                                                                    retailer_product_id=product_id)
        except:
            return {'error': "{} is not a purchased product in this order".format(product_id)}
        # check return qty
        if return_qty > ordered_product_map.shipped_qty:
            return {'error': "Product {} - return qty cannot be greater than sold quantity".format(product_id)}
        return {'ordered_product_map': ordered_product_map, 'return_qty': return_qty, 'product_id': product_id}

    def process_free_products(self, ordered_product, order_return, free_returns):
        """
            Process return for free products
            ordered_product
            order_return - return created on order
            free_returns - dict containing return free item qty
        """
        for free_product in free_returns:
            ordered_product_map_free = OrderedProductMapping.objects.get(
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

    def post(self, request):
        """
            Apply Any Available Applicable Offer - Either coupon or spot discount
            Inputs
            cart_id
            coupon_id
            spot_discount
            is_percentage (spot discount type)
        """
        initial_validation = self.post_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        order_return = initial_validation['order_return']
        # initial order amount
        received_amount = order.total_final_amount
        # refund amount according to any previous offer applied
        refund_amount = order_return.refund_amount
        applied_offers = order_return.offers
        discount_given = 0
        if applied_offers:
            for offer in applied_offers:
                if offer['coupon_type'] == 'cart' and offer['applied']:
                    discount_given += offer['discount_value']
        # refund amount without any offer
        refund_amount_raw = refund_amount - discount_given
        # new order amount when no discount is applied
        current_amount = received_amount - refund_amount_raw
        # Check spot discount or cart offer
        spot_discount = self.request.data.get('spot_discount')
        offers_list = dict()
        offers_list['applied'] = False
        if spot_discount:
            offers = BasicCartOffers.apply_spot_discount_returns(spot_discount, self.request.data.get('is_percentage'),
                                                                 current_amount, order_return, refund_amount_raw)
        else:
            offers = BasicCartOffers.refresh_returns_offers(order, current_amount, order_return, refund_amount_raw,
                                                            self.request.data.get('coupon_id'))
        if 'error' in offers:
            return get_response(offers['error'])
        return get_response("Applied Successfully" if offers['applied'] else "Not Applicable", self.serialize(order))

    def post_validate(self):
        """
            Validate returns checkout offers apply
        """
        # check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {"error": "Shop Doesn't Exist!"}
        # check order
        order_id = self.request.data.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, seller_shop_id=shop_id)
        except ObjectDoesNotExist:
            return {'error': "Order Does Not Exist"}
        # check if return created
        try:
            order_return = OrderReturn.objects.get(order=order, status='created')
        except ObjectDoesNotExist:
            return {'error': "Order Return Created Does Not Exist"}
        if not self.request.data.get('coupon_id') and not self.request.data.get('spot_discount'):
            return {'error': "Provide Coupon Id/Spot Discount"}
        if self.request.data.get('coupon_id') and self.request.data.get('spot_discount'):
            return {'error': "Provide either of coupon_id or spot_discount"}
        if self.request.data.get('spot_discount') and self.request.data.get('is_percentage') not in [0, 1]:
            return {'error': "Provide a valid spot discount type"}
        return {'order': order, 'order_return': order_return}

    def get(self, request):
        """
            Get Return Checkout Amount Info, Offers Applied-Applicable
        """
        # Input validation
        initial_validation = self.get_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        order_return = initial_validation['order_return']
        # get available offers
        # Get coupons available on cart from es
        # initial order amount
        received_amount = order.total_final_amount
        # refund amount according to any previous offer applied
        refund_amount = order_return.refund_amount
        applied_offers = order_return.offers
        discount_given = 0
        if applied_offers:
            for offer in applied_offers:
                if offer['coupon_type'] == 'cart' and offer['applied']:
                    discount_given += offer['discount_value']
        # refund amount without any offer
        refund_amount_raw = refund_amount - discount_given
        # new order amount when no discount is applied
        current_amount = received_amount - refund_amount_raw
        offers = BasicCartOffers.refresh_returns_offers(order, current_amount, order_return, refund_amount_raw)
        if 'error' in offers:
            return get_response(offers['error'])
        return get_response("Return Checkout", self.serialize(order, offers['total_offers'], offers['spot_discount']))

    def get_validate(self):
        """
            Get Return Checkout
            Input validation
        """
        # check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {"error": "Shop Doesn't Exist!"}
        # check order
        order_id = self.request.GET.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, seller_shop_id=shop_id, order_status='ordered')
        except ObjectDoesNotExist:
            return {'error': "Order Does Not Exist / Still Open / Already Returned"}
        # check if return created
        try:
            order_return = OrderReturn.objects.get(order=order, status='created')
        except ObjectDoesNotExist:
            return {'error': "Order Return Created Does Not Exist / Already Closed"}
        return {'order': order, 'order_return': order_return}

    def delete(self, request):
        """
            Order return checkout
            Delete any applied offers
        """
        # Check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return get_response("Shop Doesn't Exist!")
        # check order
        order_id = self.request.GET.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, seller_shop_id=shop_id)
        except ObjectDoesNotExist:
            return get_response("Order Does Not Exist")
        # check if return created
        try:
            order_return = OrderReturn.objects.get(order=order)
        except ObjectDoesNotExist:
            return {'error': "Order Return Does Not Exist"}
        refund_amount = order_return.refund_amount
        applied_offers = order_return.offers
        discount_given = 0
        if applied_offers:
            for offer in applied_offers:
                if offer['coupon_type'] == 'cart' and offer['applied']:
                    discount_given += offer['discount_value']
        refund_amount = refund_amount - discount_given
        order_return.offers = []
        order_return.refund_amount = refund_amount
        order_return.save()
        return get_response("Deleted Successfully", [], True)

    def serialize(self, order, offers=None, spot_discount=None):
        """
            Checkout serializer
        """
        serializer = OrderReturnCheckoutSerializer(order)
        response = serializer.data
        if offers:
            response['available_offers'] = offers
        if spot_discount:
            response['spot_discount'] = spot_discount
        return response


class OrderReturnComplete(APIView):
    """
        Complete created return on an order
    """

    def post(self, request):
        """
            Complete return on order
        """
        # check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {"error": "Shop Doesn't Exist!"}
        # check order
        order_id = self.request.data.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, seller_shop_id=shop_id, order_status='ordered')
        except ObjectDoesNotExist:
            return {'error': "Order Does Not Exist / Still Open / Already Returned"}
        # check if return created
        try:
            order_return = OrderReturn.objects.get(order=order, status='created')
        except ObjectDoesNotExist:
            return {'error': "Order Return Does Not Exist / Already Closed"}

        with transaction.atomic():
            # check partial or fully refunded order
            return_qty = order_return.rt_return_list \
            .aggregate(return_qty=Sum('return_qty'))['return_qty']

            ordered_product = OrderedProduct.objects.get(order=order)

            initial_qty = ordered_product.rt_order_product_order_product_mapping \
            .aggregate(shipped_qty=Sum('shipped_qty'))['shipped_qty']

            if initial_qty == return_qty:
                order.order_status = Order.FULLY_REFUNDED
                ordered_product.shipment_status = 'FULLY_RETURNED_AND_VERIFIED'
            else:
                order.order_status = Order.PARTIALLY_REFUNDED
                ordered_product.shipment_status = 'PARTIALLY_DELIVERED_AND_VERIFIED'
            ordered_product.last_modified_by = self.request.user
            ordered_product.save()
            order.last_modified_by = self.request.user
            order.save()
            # complete return
            order_return.status = 'completed'
            order_return.save()
        return get_response("Return Completed Successfully!", OrderReturnCheckoutSerializer(order).data)


class CouponOfferCreation(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

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
                        msg = {"is_success": False, "message": "Something went wrong",
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
                        msg = {"is_success": False, "message": f"{e}",
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
                        msg = {"is_success": False, "message": "Something went wrong",
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
                            msg = {"is_success": False, "message": "Something went wrong",
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
                            msg = {"is_success": False, "message": "Something went wrong",
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
                        except:
                            msg = {"is_success": False, "message": "Something went wrong",
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
        serializer = CouponRuleSetSerializers(coupon_offers, many=True)
        return serializer.data

    def get_coupons_combo_offers_list(self, request, shop_id):
        """
          Get Offers/Coupons
          Serialize Offers/Coupons
       """
        if request.GET.get('search_text'):
            """
                 Get Offers/Coupons when search_text is given in params
            """
            coupon = Coupon.objects.filter(shop=shop_id, coupon_code__icontains=request.GET.get('search_text'))
            serializer = CouponListSerializers(coupon, many=True)
        else:
            """
                Get Offers/Coupons when search_text is not given in params
           """
            coupon_ruleset = Coupon.objects.filter(shop=shop_id)
            serializer = CouponListSerializers(coupon_ruleset, many=True)
        """
            Pagination on Offers/Coupons
        """
        return pagination(request, serializer)

    def create_coupon(self, request, serializer, shop_id):
        """
            Creating Discount, Ruleset & Coupon
        """
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "Shop Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

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
        else:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value)
        # creating CouponRuleSet
        coupon_name_with_shop_id = f"{shop_id}_on Spending {discount_amount} get {discount_value} Off"
        coupon_obj = OffersCls.rule_set_creation(coupon_name_with_shop_id, start_date, expiry_date, discount_amount,
                                                 discount_obj)
        if type(coupon_obj) == str:
            msg = {"is_success": False, "message": coupon_obj,
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        coupon_code = f"Get {discount_value} OFF on Spending {discount_amount} Rs"
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
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "shop Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

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
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "shop Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

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

        coupon_ruleset = CouponRuleSet.objects.get(id=coupon.rule.id)
        discount = DiscountValue.objects.get(id=coupon_ruleset.discount.id)
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
            rulename = f"{shop_id}_on Spending {discount_amount} get {discount.discount_value} Off"
            coupon_ruleset_name = CouponRuleSet.objects.filter(rulename=rulename)
            if coupon_ruleset_name:
                msg = {"is_success": False,
                       "message": f"Offer already exist for ruleset_name {rulename} ",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            coupon_ruleset.rulename = rulename
            coupon.coupon_code = f"Get {discount.discount_value} OFF on Spending {discount_amount} Rs"


        if 'discount_value' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount_value = request.data.get('discount_value')
            discount.discount_value = discount_value

            coupon.coupon_code = f"Get {discount_value} OFF on Spending {coupon_ruleset.cart_qualifying_min_sku_value} Rs"
            rulename = f"{shop_id}_on Spending {coupon_ruleset.cart_qualifying_min_sku_value} get {discount_value} Off"

            coupon_ruleset_name = CouponRuleSet.objects.filter(rulename=rulename)
            if coupon_ruleset_name:
                msg = {"is_success": False,
                       "message": f"Offer already exist for ruleset_name {rulename} ",
                       "response_data": serializer.data}
                status_code = {"status_code": 404}
                return msg, status_code

            coupon_ruleset.rulename = rulename

        if 'is_percentage' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount.is_percentage = request.data.get('is_percentage')
        if 'max_discount' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount.max_discount = request.data.get('max_discount')
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
                                                           rule__coupon_ruleset__is_active=True)
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
                                                       shop=shop_id, rule__coupon_ruleset__is_active=True)
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

            coupon_ruleset_product = Coupon.objects.filter(rule__free_product=retailer_free_product_obj,
                                                           rule__free_product_qty=coupon_ruleset.free_product_qty,
                                                           shop=shop_id, rule__coupon_ruleset__is_active=True)

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
            coupon_ruleset.rulename = ruleset_name
            coupon.coupon_code = coupon_code

        if 'free_product_qty' in actual_input_data_list:
            # If free_product_qty in actual_input_data_list
            free_product_qty = self.request.data.get('free_product_qty')
            coupon_ruleset_qty = Coupon.objects.filter(rule__free_product=coupon_ruleset.free_product,
                                                       rule__free_product_qty=free_product_qty,
                                                       shop=shop_id, rule__coupon_ruleset__is_active=True)
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
