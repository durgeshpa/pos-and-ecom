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
from pos.models import RetailerProduct, UserMappedShop, Payment, PAYMENT_MODE
from pos.common_functions import get_response, delete_cart_mapping, order_search
from .serializers import BasicCartSerializer, BasicOrderSerializer, CheckoutSerializer, \
    BasicOrderListSerializer, OrderedDashBoardSerializer, BasicCartListSerializer, OrderReturnCheckoutSerializer
from pos.offers import BasicCartOffers
from pos.common_functions import create_user_shop_mapping, get_shop_id_from_token
from common.common_utils import whatsapp_opt_in, whatsapp_invoice_send
from retailer_to_sp.api.v1.views import pdf_generation_retailer
# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')

ORDER_STATUS_MAP = {
    1: Order.ORDERED,
    2: Order.CANCELLED,
    3: Order.PARTIALLY_REFUNDED,
    4: Order.FULLY_REFUNDED
}

class SearchView(APIView):
    """
        Search Catalogue ElasticSearch
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
            Search and get catalogue products from ElasticSearch
            Inputs
            ---------
            index ('string')
                values
                    '1' : Complete GramFactory Catalogue
                    '2' : GramFactory Shop Catalogue
                    '3' : Retailer Shop Catalogue
                    '4' : Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
            shop_id ('string')
                description
                    To get products from index '2'
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
        index_type = request.GET.get('index_type')
        # Complete GramFactory Catalogue
        if index_type == '1':
            return self.gf_search()
        # GramFactory Shop Catalogue
        elif index_type == '2':
            return self.gf_shop_search()
        # Retailer Shop Catalogue
        elif index_type == '3':
            return self.rp_search()
        # Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
        elif index_type == '4':
            return self.rp_gf_search()
        else:
            return get_response("Please Provide A Valid Index Type")

    def rp_search(self):
        """
            Search Retailer Shop Catalogue
        """
        # Validate shop from token
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return get_response("Shop Doesn't Exist!")

        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        if search_type == '1':
            results = self.rp_exact_search(shop_id)
        # Normal Search
        elif search_type == '2':
            results = self.rp_normal_search(shop_id)
        else:
            return get_response("Please Provide A Valid Search Type")
        return get_response('Products Found' if results else 'No Products Found', results)

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

    def rp_gf_search(self):
        """
            Search Retailer Shop Catalogue - Followed by GramFactory Catalogue If Products not found
        """
        # Validate shop from token
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return get_response("Shop Doesn't Exist!")

        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        if search_type == '1':
            results = self.rp_gf_exact_search(shop_id)
        else:
            return get_response("Provide a valid search type")
        return get_response('Products Found' if results else 'No Products Found', results)

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

    def process_rp(self, output_type, body, shop_id):
        """
            Modify Es results for response based on output_type - Raw OR Processed
        """
        body["from"] = int(self.request.GET.get('offset', 0))
        body["size"] = int(self.request.GET.get('count', 10))
        p_list = []
        # Raw Output
        if output_type == '1':
            body["_source"] = {"includes": ["id", "name", "selling_price", "mrp", "margin", "ean", "status", "images"]}
            try:
                products_list = es_search(index='rp-{}'.format(shop_id), body=body)
                for p in products_list['hits']['hits']:
                    p_list.append(p["_source"])
            except Exception as e:
                error_logger.error(e)
        # Processed Output
        else:
            body["_source"] = {"includes": ["id", "name", "selling_price", "mrp", "margin", "images", "ean", "status"]}
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

    # TODO
    def gf_search(self):
        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        if search_type == '1':
            results = self.gf_exact_search()
        # Normal Search
        elif search_type == '2':
            results = self.gf_normal_search()
        else:
            return get_response("Please Provide A Valid Search Type")
        return get_response('Products Found' if results else 'No Products Found', results)

    # TODO
    def gf_exact_search(self):
        ean_code = self.request.GET.get('ean_code')
        output_type = self.request.GET.get('output_type', '1')
        body = dict()
        if ean_code and ean_code != '':
            body["query"] = {"bool": {"filter": [{"term": {"ean": ean_code}}]}}
        return self.process_gf(output_type, body)

    # TODO
    def gf_normal_search(self):
        keyword = self.request.GET.get('keyword')
        output_type = self.request.GET.get('output_type', '1')
        body = dict()
        query = {"bool": {"filter": [{"term": {"status": True}}]}}
        if keyword:
            q = {"multi_match": {"query": keyword, "fields": ["name^5", "category", "brand"], "type": "cross_fields"}}
            query["bool"]["must"] = [q]
        body['query'] = query
        return self.process_gf(output_type, body)

    # TODO
    def process_gf(self, output_type, body):
        body["from"] = int(self.request.GET.get('offset', 0))
        body["size"] = int(self.request.GET.get('count', 10))
        p_list = []
        # Raw Output
        if output_type == '1':
            body["_source"] = {"includes": ["id", "name", "product_images", "mrp", "ptr", "ean"]}
            try:
                products_list = es_search(index='all_products', body=body)
                for p in products_list['hits']['hits']:
                    p_list.append(p["_source"])
            except Exception as e:
                error_logger.error(e)
        # Processed Output
        else:
            body["_source"] = {"includes": ["id", "name", "product_images", "mrp", "ptr", "ean"]}
            try:
                products_list = es_search(index='all_products', body=body)
                for p in products_list['hits']['hits']:
                    p_list.append(p["_source"])
            except Exception as e:
                error_logger.error(e)
        return p_list

    # TODO
    def gf_shop_search(self):
        pass


class CartCheckout(APIView):
    """
        Checkout after items added
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
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
        initial_validation = self.post_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        cart = initial_validation['cart']
        # Check spot discount
        spot_discount = self.request.data.get('spot_discount')
        if spot_discount:
            offers = BasicCartOffers.apply_spot_discount(cart, spot_discount, self.request.data.get('is_percentage'))
        else:
            # Get offers available now and apply coupon if applicable
            offers = BasicCartOffers.refresh_offers(cart, False, self.request.data.get('coupon_id'))
        if 'error' in offers:
            return get_response(offers['error'])
        return get_response("Applied Successfully" if offers['applied'] else "Not Applicable", self.serialize(cart))

    def get(self, request):
        """
            Get Checkout Amount Info, Offers Applied-Applicable
        """
        # Input validation
        initial_validation = self.get_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        cart = initial_validation['cart']
        # Auto apply highest applicable discount
        auto_apply = self.request.GET.get('auto_apply')
        # Get Offers Applicable, Verify applied offers, Apply highest discount on cart if auto apply
        offers = BasicCartOffers.refresh_offers(cart, auto_apply)
        if 'error' in offers:
            return get_response(offers['error'])
        return get_response("Cart Checkout", self.serialize(cart, offers['total_offers'], offers['spot_discount']))

    def delete(self, request):
        """
            Checkout
            Delete any applied cart offers
        """
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return get_response("Shop Doesn't Exist!")

        cart_id = self.request.GET.get('cart_id')
        try:
            cart = Cart.objects.get(pk=cart_id, seller_shop_id=shop_id, cart_status__in=['active', 'pending'])
        except ObjectDoesNotExist:
            return get_response("Cart Does Not Exist / Already Closed")
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        for product_map in cart_products:
            cart_value += product_map.selling_price * product_map.qty
        offers_list = BasicCartOffers.update_cart_offer(cart.offers, cart_value)
        Cart.objects.filter(pk=cart.id).update(offers=offers_list)
        return get_response("Removed Offer From Cart Successfully", [], True)

    def post_validate(self):
        """
            Add cart offer in checkout
            Input validation
        """
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {"error": "Shop Doesn't Exist!"}
        cart_id = self.request.data.get('cart_id')
        try:
            cart = Cart.objects.get(pk=cart_id, seller_shop_id=shop_id, cart_status__in=['active', 'pending'])
        except ObjectDoesNotExist:
            return {'error': "Cart Does Not Exist / Already Closed"}
        if not self.request.data.get('coupon_id') and not self.request.data.get('spot_discount'):
            return {'error': "Please Provide Coupon Id/Spot Discount"}
        if self.request.data.get('coupon_id') and self.request.data.get('spot_discount'):
            return {'error': "Please Provide Only One Of Coupon Id, Spot Discount"}
        if self.request.data.get('spot_discount') and self.request.data.get('is_percentage') not in [0, 1]:
            return {'error': "Please Provide A Valid Spot Discount Type"}
        return {'cart': cart}

    def get_validate(self):
        """
            Get Checkout
            Input validation
        """
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        cart_id = self.request.GET.get('cart_id')
        try:
            cart = Cart.objects.get(pk=cart_id, seller_shop_id=shop_id, cart_status__in=['active', 'pending'])
        except ObjectDoesNotExist:
            return {'error': "Cart Does Not Exist / Already Closed"}
        return {'cart': cart}

    def serialize(self, cart, offers=None, spot_discount=None):
        """
            Checkout serializer
            Payment Info plus Offers
        """
        serializer = CheckoutSerializer(Cart.objects.get(pk=cart.id))
        response = serializer.data
        if offers:
            response['available_offers'] = offers
        if spot_discount:
            response['spot_discount'] = spot_discount
        return response


class CartCentral(APIView):
    """
        Get Cart
        Add To Cart
        Search Cart
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
            Get Cart
            Inputs:
                shop_id
                cart_type (retail-1 or basic-2)
        """
        cart_type = self.request.GET.get('cart_type')
        if cart_type == '1':
            return self.get_retail_cart()
        elif cart_type == '2':
            if self.request.GET.get('cart_id'):
                return self.get_basic_cart()
            else:
                return self.get_basic_cart_list()
        else:
            return get_response('Please provide a valid cart_type')

    def post(self, request):
        """
            Add To Cart
            Inputs
                cart_type (retail-1 or basic-2)
                cart_product (Product for 'retail', RetailerProduct for 'basic'
                shop_id (Buyer shop id for 'retail', Shop id for selling shop in case of 'basic')
                cart_id (For Basic Cart)
                qty (Quantity of product to be added)
        """
        cart_type = self.request.data.get('cart_type')
        if cart_type == '1':
            return self.retail_add_to_cart()
        elif cart_type == '2':
            return self.basic_add_to_cart()
        else:
            return get_response('Please provide a valid cart_type')

    def put(self, request, pk):
        """
            Update Customer Details For Basic Cart
            Inputs
            cart_id
            phone_number - Customer phone number
        """
        # Check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return get_response("Shop Doesn't Exist!")
        # Check If Cart Exists
        try:
            cart = Cart.objects.get(id=pk, cart_status__in=['active', 'pending'], seller_shop_id=shop_id)
        except:
            return get_response("Cart Not Found")
        # check phone_number
        phone_no = self.request.data.get('phone_number')
        if not phone_no:
            return get_response("Please enter phone number")
        if not re.match(r'^[6-9]\d{9}$', phone_no):
            return get_response("Please enter a valid phone number")
        return self.add_customer_to_cart(cart, shop_id, phone_no)

    def delete(self, request, pk):
        """
            Update Cart Status To deleted For Basic Cart
        """
        # Check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return get_response("Shop Doesn't Exist!")
        # Check If Cart Exists
        try:
            cart = Cart.objects.get(id=pk, last_modified_by=self.request.user, cart_status__in=['active', 'pending'],
                                    cart_type='BASIC', seller_shop_id=shop_id)
        except:
            return get_response("Cart Not Found")
        Cart.objects.filter(id=cart.id).update(cart_status=Cart.DELETED)
        return get_response('Deleted Cart', self.post_serialize_process_basic(cart))

    def add_customer_to_cart(self, cart, shop_id, ph_no):
        """
            Update customer details in basic cart
        """
        name = self.request.data.get('name')
        email = self.request.data.get('email')
        is_whatsapp = self.request.data.get('is_whatsapp')
        if email:
            try:
                validators.validate_email(email)
            except:
                return get_response("Please enter a valid email")

        # Check Customer - Update Or Create
        customer, created = User.objects.get_or_create(phone_number=ph_no)
        customer.email = email if email else customer.email
        customer.first_name = name if name else customer.first_name
        customer.is_whatsapp = True if is_whatsapp else False
        customer.save()
        if created:
            create_user_shop_mapping(user=customer, shop_id=shop_id)
        # Update customer as buyer in cart
        cart.buyer = customer
        cart.save()
        if customer.is_whatsapp is True:
            whatsapp_opt_in.delay(ph_no)
        serializer = BasicCartSerializer(cart)
        return get_response("Cart Updated Successfully!", serializer.data)

    def get_retail_cart(self):
        """
            Get Cart
            For cart_type "retail"
        """
        # basic validations for inputs
        initial_validation = self.get_retail_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
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
                    return get_response('Sorry no product added to this cart yet')
                # Delete products without MRP
                self.delete_products_without_mrp(cart)
                # Process response - Product images, MRP check, Serialize - Search and Pagination
                return get_response('Cart', self.get_serialize_process_sp(cart, seller_shop, buyer_shop))
            else:
                return get_response('Sorry no product added to this cart yet')
        # If Seller Shop is gf type
        elif shop_type == 'gf':
            # Check if cart exists
            if GramMappedCart.objects.filter(last_modified_by=user, cart_status__in=['active', 'pending']).exists():
                cart = GramMappedCart.objects.filter(last_modified_by=user,
                                                     cart_status__in=['active', 'pending']).last()
                # Check if products are present in cart
                if cart.rt_cart_list.count() <= 0:
                    return get_response('Sorry no product added to this cart yet')
                else:
                    # Process response - Serialize
                    return get_response('Cart', self.get_serialize_process_gf(cart, seller_shop))
            else:
                return get_response('Sorry no product added to this cart yet')
        else:
            return get_response('Sorry shop is not associated with any GramFactory or any SP')

    def get_basic_cart(self):
        """
            Get Cart
            For cart_type "basic"
        """
        # basic validations for inputs
        initial_validation = self.get_basic_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        cart = initial_validation['cart']
        # Refresh - add/remove/update combo and cart level offers
        offers = BasicCartOffers.refresh_offers(cart)
        if 'error' in offers:
            return get_response(offers['error'])
        return get_response('Cart', self.get_serialize_process_basic(cart))

    def get_basic_cart_list(self):
        """
            List active carts for seller shop
        """
        # Check Shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        search_text = self.request.GET.get('search_text')
        carts = Cart.objects.filter(seller_shop_id=shop_id, cart_status__in=['active', 'pending']).order_by('-modified_at')
        if search_text:
            carts = carts.filter(Q(buyer__phone_number__icontains=search_text) |
                                 Q(id__icontains=search_text))
        open_orders = BasicCartListSerializer(carts, many=True)
        return get_response("Open Orders", pagination(self.request, open_orders))

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

    def get_basic_validate(self):
        """
            Get Cart
            Input validation for cart type 'basic'
        """
        # check if shop exists
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            return {'error': "Shop Doesn't Exist!"}
        try:
            cart = Cart.objects.get(seller_shop=shop, cart_type='BASIC',
                                    id=self.request.GET.get('cart_id'), )
        except ObjectDoesNotExist:
            return {'error': "Cart Not Found!"}
        return {'shop': shop, 'cart': cart}

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
    def delivery_message():
        """
            Get Cart
            Delivery message
        """
        date_time_now = datetime.now()
        day = date_time_now.strftime("%A")
        time = date_time_now.strftime("%H")

        if int(time) < 17 and not (day == 'Saturday'):
            return str('Order now and get delivery by {}'.format(
                (date_time_now + timedelta(days=1)).strftime('%A')))
        elif (day == 'Friday'):
            return str('Order now and get delivery by {}'.format(
                (date_time_now + timedelta(days=3)).strftime('%A')))
        else:
            return str('Order now and get delivery by {}'.format(
                (date_time_now + timedelta(days=2)).strftime('%A')))

    @staticmethod
    def delete_products_without_mrp(cart):
        """
            Delete products without MRP in cart
        """
        for i in Cart.objects.get(id=cart.id).rt_cart_list.all():
            if not i.cart_product.getMRP(cart.seller_shop.id, cart.buyer_shop.id):
                CartProductMapping.objects.filter(cart__id=cart.id, cart_product__id=i.cart_product.id).delete()

    def get_serialize_process_sp(self, cart, seller_shop='', buyer_shop=''):
        """
           Get Cart
           Cart type retail - sp
           Serialize and Modify Cart - Parent Product Image Check, MRP Check
        """
        serializer = CartSerializer(Cart.objects.get(id=cart.id),
                                    context={'parent_mapping_id': seller_shop.id, 'buyer_shop_id': buyer_shop.id,
                                             'search_text': self.request.GET.get('search_text', ''),
                                             'page_number': self.request.GET.get('page_number', 1),
                                             'records_per_page': self.request.GET.get('records_per_page', 10),
                                             'delivery_message': self.delivery_message()})
        for i in serializer.data['rt_cart_list']:
            # check if product has to use it's parent product image
            if not i['cart_product']['product_pro_image']:
                product = Product.objects.get(id=i['cart_product']['id'])
                if product.use_parent_image:
                    for im in product.parent_product.parent_product_pro_image.all():
                        parent_image_serializer = ParentProductImageSerializer(im)
                        i['cart_product']['product_pro_image'].append(parent_image_serializer.data)
            # remove products without mrp
            if not i['cart_product']['product_mrp']:
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

    def get_serialize_process_basic(self, cart):
        """
           Get Cart
           Cart type basic
           Serialize
        """
        serializer = BasicCartSerializer(Cart.objects.get(id=cart.id),
                                         context={'search_text': self.request.GET.get('search_text', ''),
                                                  'page_number': self.request.GET.get('page_number', 1),
                                                  'records_per_page': self.request.GET.get('records_per_page', 10)})
        return serializer.data

    def retail_add_to_cart(self):
        """
            Add To Cart
            For cart type 'retail'
        """
        # basic validations for inputs
        initial_validation = self.post_retail_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
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
                return get_response(proceed['message'], proceed['data'])
            elif proceed['quantity_check']:
                # check for product available quantity and add to cart
                cart_map = self.retail_quantity_check(seller_shop, product, cart, qty)
            # Check if products are present in cart
            if cart.rt_cart_list.count() <= 0:
                return get_response('Sorry no product added to this cart yet')
            # process and return response
            return get_response('Added To Cart', self.post_serialize_process_sp(cart, seller_shop, buyer_shop, product))
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
                return get_response('Sorry no product added to this cart yet')
            # process and return response
            return get_response('Added To Cart', self.post_serialize_process_gf(cart, seller_shop))
        else:
            return get_response('Sorry shop is not associated with any Gramfactory or any SP')

    def basic_add_to_cart(self):
        """
            Add To Cart
            For cart type 'basic'
        """
        # basic validations for inputs
        initial_validation = self.post_basic_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        product = initial_validation['product']
        shop = initial_validation['shop']
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
        if cart.rt_cart_list.count() <= 0:
            return get_response('No product added to this cart yet')
        # serialize and return response
        return get_response('Added To Cart', self.post_serialize_process_basic(cart))

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
        return {'product': product, 'buyer_shop': parent_mapping.retailer, 'seller_shop': parent_mapping.parent,
                'quantity': qty, 'shop_type': parent_mapping.parent.shop_type.shop_type}

    def post_basic_validate(self):
        """
            Add To Cart
            Input validation for add to cart for cart type 'basic'
        """
        # Check shop token
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        qty = self.request.data.get('qty')
        # Added Quantity check
        if qty is None or qty == '':
            return {'error': "Qty Not Found!"}
        # Check if shop exists
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            return {'error': "Shop Doesn't Exist!"}
        # Check if product exists for that shop
        try:
            product = RetailerProduct.objects.get(id=self.request.data.get('cart_product'), shop=shop)
        except ObjectDoesNotExist:
            return {'error': "Product Not Found!"}
        # Check if existing or new cart
        cart = None
        cart_id = self.request.data.get('cart_id')
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id, last_modified_by=self.request.user, seller_shop=shop,
                                        cart_type='BASIC', cart_status__in=['active', 'pending'])
            except ObjectDoesNotExist:
                return {'error': "Cart Not Found!"}
        # Check if selling price is less than equal to mrp if price change
        price_change = self.request.data.get('price_change')
        if price_change in ['1', '2']:
            selling_price = self.request.data.get('selling_price')
            if not selling_price:
                return {'error': "Please provide selling price to change price"}
            if Decimal(selling_price) > product.mrp:
                return {'error': "Selling Price cannot be greater than MRP"}
        # activate product in cart
        if product.status != 'active':
            product.status = 'active'
            product.save()
        return {'product': product, 'shop': shop, 'quantity': qty, 'cart': cart}

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
            cart = Cart(last_modified_by=user, cart_status='active')
            cart.cart_type = 'RETAIL'
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
            cart.cart_type = 'BASIC'
            cart.approval_status = False
            cart.cart_status = 'active'
            cart.seller_shop = seller_shop
            cart.save()
        else:
            cart = Cart(last_modified_by=user, cart_status='active')
            cart.cart_type = 'BASIC'
            cart.approval_status = False
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
                return self.retail_capping_remaining(capping.capping_qty, ordered_qty)
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
        if price_change in ['1', '2']:
            selling_price = self.request.data.get('selling_price')
            if price_change == '1' and selling_price:
                RetailerProduct.objects.filter(id=product.id).update(selling_price=selling_price)

        return selling_price if selling_price else product.selling_price

    def post_serialize_process_sp(self, cart, seller_shop='', buyer_shop='', product=''):
        """
            Add To Cart
            Serialize and Modify Cart - MRP Check - retail sp cart
        """
        serializer = CartSerializer(Cart.objects.get(id=cart.id), context={'parent_mapping_id': seller_shop.id,
                                                                           'buyer_shop_id': buyer_shop.id})
        for i in serializer.data['rt_cart_list']:
            if not i['cart_product']['product_mrp']:
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
        serializer = BasicCartSerializer(Cart.objects.get(id=cart.id))
        return serializer.data


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
            return self.get_basic_order_list(request)
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

    def get_basic_order_list(self, request):
        """
            Get Order
            For Basic Cart
        """
        # basic validation for inputs
        initial_validation = self.get_basic_list_validate(request)
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        return get_response('Order', self.get_serialize_process_basic(order))

    def get_basic_list_validate(self, request):
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
        order = self.get_basic_order(request, shop_id)
        return {'order': order}

    def get_basic_order(self, request, shop_id):
        """
          Get Basic Orders
        """
        search_text = request.GET.get('search_text')
        order_status = request.GET.get('order_status')
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


class OrderCentral(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
            Get Order Details
            Inputs
            cart_type
            order_id
        """
        cart_type = request.GET.get('cart_type')
        if cart_type == '1':
            return self.get_retail_order()
        elif cart_type == '2':
            return self.get_basic_order()
        else:
            return get_response('Provide a valid cart_type')

    def put(self, request, pk):
        """
            allowed updates to order status
        """
        # Check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return get_response("Shop Doesn't Exist!")
        # Check if order exists
        try:
            order = Order.objects.get(pk=pk, seller_shop_id=shop_id, order_status='ordered')
        except ObjectDoesNotExist:
            return get_response('Order Not Found To Cancel!')
        # check input status validity
        allowed_updates = [Order.CANCELLED]
        status = self.request.data.get('status')
        if status not in allowed_updates:
            return get_response("Please Provide A Valid Status To Update Order")
        # cancel order
        order.order_status = status
        order.last_modified_by = self.request.user
        order.save()
        # cancel shipment
        OrderedProduct.objects.filter(order=order).update(shipment_status='CANCELLED', last_modified_by=self.request.user)
        return get_response("Order cancelled successfully!", [], True)

    def post(self, request):
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
        cart_type = self.request.data.get('cart_type')
        if cart_type == '1':
            return self.post_retail_order()
        elif cart_type == '2':
            return self.post_basic_order()
        else:
            return get_response('Provide a valid cart_type')

    def get_retail_order(self):
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

    def get_basic_order(self):
        """
            Get Order
            For Basic Cart
        """
        # basic validation for inputs
        initial_validation = self.get_basic_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        return get_response('Order', self.get_serialize_process_basic(order))

    def post_retail_order(self):
        """
            Place Order
            For retail cart
        """
        # basic validations for inputs
        initial_validation = self.post_retail_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
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
                        return get_response(cart_resp['message'])
                    # Check capping
                    order_capping_check = self.retail_capping_check(cart, parent_mapping)
                    if not order_capping_check['is_success']:
                        return get_response(order_capping_check['message'])
                    # Get Order Reserved data and process order
                    order_reserve_obj = self.get_reserve_retail_sp(cart, parent_mapping)
                    if order_reserve_obj:
                        # Create Order
                        order = self.create_retail_order_sp(cart, parent_mapping, billing_address, shipping_address)
                        # Release blocking
                        if self.update_ordered_reserve_sp(cart, parent_mapping, order) is False:
                            order.delete()
                            return get_response('No item in this cart.')
                        # Serialize and return response
                        return get_response('Ordered Successfully!',
                                            self.post_serialize_process_sp(order, parent_mapping))
                    # Order reserve not found
                    else:
                        return get_response('Sorry! your session has timed out.')
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
                    return get_response('Ordered Successfully!', self.post_serialize_process_gf(order, parent_mapping))
                else:
                    return get_response('Available Quantity Is None')
        # Shop type neither sp nor gf
        else:
            return get_response('Sorry shop is not associated with any GramFactory or any SP')
        return get_response('Some error occurred')

    def post_basic_order(self):
        """
            Place Order
            For basic cart
        """
        # basic validations for inputs
        initial_validation = self.post_basic_validate()
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        shop = initial_validation['shop']
        cart = initial_validation['cart']
        payment_method = initial_validation['payment_method']

        with transaction.atomic():
            # Update Cart To Ordered
            self.update_cart_basic(cart)
            order = self.create_basic_order(cart, shop)
            self.auto_process_order(order, payment_method)
            return get_response('Ordered Successfully!', self.post_serialize_process_basic(order))

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

    def get_basic_validate(self):
        """
            Get order validate
        """
        # Check shop
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        # Check if order exists
        try:
            order = Order.objects.get(pk=self.request.GET.get('order_id'), seller_shop_id=shop_id)
        except ObjectDoesNotExist:
            return {'error': 'Order Not Found!'}
        return {'order': order}

    def post_retail_validate(self):
        """
            Place Order
            Input validation for cart type 'retail'
        """
        shop_id = self.request.data.get('shop_id')
        # Check if buyer shop exists
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
        return {'parent_mapping': parent_mapping, 'shop_type': parent_mapping.parent.shop_type.shop_type,
                'billing_add': billing_address, 'shipping_add': shipping_address}

    def post_basic_validate(self):
        """
            Place Order
            Input validation for cart type 'basic'
        """
        # Check if seller shop exists
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        try:
            shop = Shop.objects.get(id=shop_id)
        except ObjectDoesNotExist:
            return {'error': "Shop Doesn't Exist!"}
        # Check if cart exists
        cart_id = self.request.data.get('cart_id')
        try:
            cart = Cart.objects.get(id=cart_id, last_modified_by=self.request.user, seller_shop=shop,
                                    cart_status__in=['active', 'pending'])
        except ObjectDoesNotExist:
            return {'error': "Cart Doesn't Exist!"}
        if not cart.buyer:
            return {'error': "Cart customer not found!"}
        # Check if products available in cart
        cart_products = CartProductMapping.objects.select_related('retailer_product').filter(cart=cart, product_type=1)
        if cart_products.count() <= 0:
            return {'error': 'No product is available in cart'}
        # Check payment method
        payment_method = self.request.data.get('payment_method')
        if not payment_method or payment_method not in dict(PAYMENT_MODE):
            return {'error': 'Please provide a valid payment method'}
        return {'shop': shop, 'cart': cart, 'payment_method': payment_method}

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
            else:
                pass
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
        cart.cart_status = 'ordered'
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
                                                         ordered_by=user, ordered_cart=cart)

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
        order.total_tax_amount = float(self.request.data.get('total_tax_amount', 0))
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
            'transaction_id': cart.id,
            'transaction_type': 'ordered',
            'order_status': order.order_status
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
                                                  transaction_id=cart.id,
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
        serializer = BasicOrderSerializer(order, context={'current_url': self.request.get_host()})
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
        return serializer.data

    def auto_process_order(self, order, payment_method):
        """
            Auto process add payment, shipment, invoice for retailer and customer
        """
        # Add free products
        offers = order.ordered_cart.offers
        product_qty_map = {}
        if offers:
            for offer in offers:
                if offer['type'] == 'combo':
                    qty = offer['free_item_qty_added']
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
        Payment.objects.create(
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
                                                          ).values('retailer_product', 'qty', 'product_type', 'selling_price')
        for product_map in cart_products:
            # Order Item
            ordered_product_mapping = OrderedProductMapping.objects.create(ordered_product=shipment,
                                                                           retailer_product_id=product_map[
                                                                               'retailer_product'],
                                                                           product_type=product_map[
                                                                               'product_type'],
                                                                           selling_price=product_map['selling_price'],
                                                                           shipped_qty=product_map['qty'],
                                                                           picked_pieces=product_map['qty'],
                                                                           delivered_qty=product_map['qty'])
            # Order Item Batch
            OrderedProductBatch.objects.create(
                ordered_product_mapping=ordered_product_mapping,
                quantity=product_map['qty'],
                pickup_quantity=product_map['qty'],
                delivered_qty=product_map['qty'],
                ordered_pieces=product_map['qty']
            )
        # Invoice Number Generate
        shipment.shipment_status = OrderedProduct.READY_TO_SHIP
        shipment.save()
        # Complete Shipment
        shipment.shipment_status = 'FULLY_DELIVERED_AND_VERIFIED'
        shipment.save()
        pdf_generation_retailer(self.request, order.id)


class OrderedItemCentralDashBoard(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
            Get Order, Product & User Counts(Overview)
            Inputs
            app_type
            shop_id
            retail
                shop_id (Buyer shop id)
            basic
                shop_id (Seller shop id)
        """
        cart_type = request.GET.get('app_type')
        if cart_type == '1':
            return self.get_retail_order_overview()
        elif cart_type == '2':
            return self.get_basic_order_overview(request)
        else:
            return get_response('Provide a valid app_type')

    def get_basic_order_overview(self, request):
        """
            Get Order, Product, & User Counts
            For Basic Cart
        """
        # basic validation for inputs
        initial_validation = self.get_basic_list_validate(request)
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        order = initial_validation['order']
        return get_response('Order', self.get_serialize_process(order))

    def get_basic_list_validate(self, request):
        """
           Input validation for cart type 'basic'
        """
        # Check if seller shop exist
        shop_id = get_shop_id_from_token(self.request)
        if not type(shop_id) == int:
            return {'error': "Shop Doesn't Exist!"}
        # get a order_overview
        order = self.get_basic_orders_count(request, shop_id)
        return {'order': order}

    def get_basic_orders_count(self, request, shop_id):
        """
          Get Basic Order Overview based on filters
        """
        filters = request.GET.get('filters')
        if filters is not '':
            # check if filter parameter is not none convert it to int
            filters = int(filters)
        order_status = request.GET.get('order_status')
        today = datetime.today()

        # get total orders for shop_id
        orders = Order.objects.filter(seller_shop=shop_id)
        # get total products for shop_id
        products = RetailerProduct.objects.filter(shop=shop_id)
        # get total users for shop_id
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

        # counts of order with total_final_amount, users, & products
        order_count = orders.count()
        users_count = users.count()
        products_count = products.count()
        overview = [{"orders": order_count, "register_users": users_count, "products": products_count,
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
        return get_response('Order', self.get_serialize_process(order))

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
        order = [{"order": orders, "total_final_amount": total_final_amount}]
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
        return get_response("Order Return", BasicOrderSerializer(order, context={'current_url': self.request.get_host()}).data)

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