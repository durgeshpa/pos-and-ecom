import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Q

from django.db import transaction
from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist

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
from categories import models as categorymodel
from retailer_to_sp.models import Cart, CartProductMapping, Order, check_date_range, capping_check, OrderedProduct, \
    OrderedProductMapping, OrderedProductBatch
from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping,
                                     Order as GramMappedOrder)
from shops.models import Shop
from brand.models import Brand
from gram_to_brand.models import (OrderedProductReserved as GramOrderedProductReserved, PickList)
from sp_to_gram.models import OrderedProductReserved
from addresses.models import Address
from pos.models import RetailerProduct, UserMappedShop, Payment, PAYMENT_MODE
from pos.common_functions import get_response, delete_cart_mapping, order_search
from .serializers import ProductDetailSerializer, BasicCartSerializer, BasicOrderSerializer, CheckoutSerializer, \
    BasicOrderListSerializer, OrderedDashBoardSerializer, BasicCartListSerializer
from pos.offers import BasicCartOffers
from pos.common_functions import create_user_shop_mapping, get_shop_id_from_token


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
        else:
            return get_response("Provide a valid index for search")

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
            return self.rp_exact_search(shop_id)
        # Normal Search
        elif search_type == '2':
            return self.rp_normal_search(shop_id)
        else:
            return get_response("Provide a valid search type")

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

    def process_rp(self, output_type, body, shop_id):
        """
            Modify Es results for response based on output_type - Raw OR Processed
        """
        body["from"] = int(self.request.GET.get('offset', 0))
        body["size"] = int(self.request.GET.get('count', 10))
        p_list = []
        # Raw Output
        if output_type == '1':
            body["_source"] = {"includes": ["id", "name", "selling_price", "mrp", "margin", "ean"]}
            try:
                products_list = es_search(index='rp-{}'.format(shop_id), body=body)
                for p in products_list['hits']['hits']:
                    p_list.append(p["_source"])
            except:
                pass
        # Processed Output
        else:
            body["_source"] = {"includes": ["id", "name", "selling_price", "mrp", "margin", "images", "ean"]}
            try:
                products_list = es_search(index='rp-{}'.format(shop_id), body=body)
                for p in products_list['hits']['hits']:
                    # Combo Offers On Products
                    p["_source"]['coupons'] = BasicCartOffers.get_basic_combo_coupons([p["_source"]["id"]], shop_id, 10,
                                                                                      ["coupon_code", "coupon_type"])
                    p_list.append(p["_source"])
            except:
                pass
        return get_response('Products Found' if p_list else 'No Products Found', p_list)

    # TODO
    def gf_search(self):
        search_type = self.request.GET.get('search_type', '1')
        # Exact Search
        if search_type == '1':
            return self.gf_exact_search()
        # Normal Search
        elif search_type == '2':
            return self.gf_normal_search()
        else:
            return get_response("Provide a valid search type")

    # TODO
    def gf_exact_search(self):
        ean_code = self.request.GET.get('ean_code')
        output_type = self.request.GET.get('output_type', '1')
        body = dict()
        if ean_code and ean_code != '':
            body["query"] = {"bool": {"filter": [{"term": {"ean": ean_code}}]}}
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
            except:
                pass
        # Processed Output
        else:
            body["_source"] = {"includes": ["id", "name", "product_images", "mrp", "ptr", "ean"]}
            try:
                products_list = es_search(index='all_products', body=body)
                for p in products_list['hits']['hits']:
                    p_list.append(p["_source"])
            except:
                pass
        return get_response('Products Found' if p_list else 'No Products Found', p_list)

    # TODO
    def gf_normal_search(self):
        pass

    # TODO
    def gf_shop_search(self):
        pass


class ProductDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        """
            API to get information of existing GramFactory product
        """
        pk = self.kwargs.get('pk')
        try:
            product = Product.objects.get(id=pk)
        except ObjectDoesNotExist:
            return get_response('Invalid Product ID')

        product_detail_serializer = ProductDetailSerializer(product)
        return get_response('Product Found', product_detail_serializer.data)


class GramProductsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        API to search for GramFactory products
        Inputs:
        product_name
        product_ids
        brands
        categories
        """
        query = self.search_query(request)
        body = {
            "from": int(request.GET.get('offset', 0)),
            "size": int(request.GET.get('pro_count', 50)),
            "query": query,
            "_source": {
                "includes": ["id", "name", "product_images"]}
        }
        products_list = es_search(index="all_products", body=body)
        p_list = self.process_results(products_list)
        return get_response('Products Found' if p_list else 'No Products Found', p_list)

    def search_query(self, request):
        """
            Es Search query to search for products based on name, brand, category
        """
        filter_list = [
            {"term": {"status": True}},
        ]
        query = {"bool": {"filter": filter_list}}

        product_ids = request.GET.get('product_ids')
        if product_ids:
            filter_list.append({"ids": {"type": "product", "values": product_ids}})
            return query

        brands = request.GET.get('brands')
        categories = request.GET.get('categories')
        keyword = request.GET.get('product_name')

        if not (categories or brands or keyword):
            return query

        if brands:
            brand_name = "{} -> {}".format(Brand.objects.filter(id__in=list(brands)).last(), keyword)
            filter_list.append({"match": {"brand": {"query": brand_name, "fuzziness": "AUTO", "operator": "and"}}})
        elif keyword:
            q = {"multi_match": {"query": keyword, "fields": ["name^5", "category", "brand"], "type": "cross_fields"}}
            query["bool"]["must"] = [q]
        if categories:
            category_filter = str(categorymodel.Category.objects.filter(id__in=categories, status=True).last())
            filter_list.append({"match": {"category": {"query": category_filter, "operator": "and"}}})

        return query

    def process_results(self, products_list):
        p_list = []
        for p in products_list['hits']['hits']:
            p_list.append(p["_source"])
        return p_list


class CartCheckout(APIView):
    """
        Checkout after items added
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
            Checkout
            Apply Any Available Cart Offer
            Inputs
            cart_id
            coupon_id
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
        return get_response("Offers", self.serialize(cart, offers['total_offers']))

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
            cart = Cart.objects.get(pk=cart_id, seller_shop_id=shop_id)
        except ObjectDoesNotExist:
            return get_response("Cart Does Not Exist")
        cart_products = cart.rt_cart_list.all()
        cart_value = 0
        for product_map in cart_products:
            cart_value += product_map.selling_price * product_map.qty
        offers_list = BasicCartOffers.update_cart_offer(cart.offers, cart_value)
        Cart.objects.filter(pk=cart.id).update(offers=offers_list)
        return get_response("Deleted Successfully", [], True)

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
            cart = Cart.objects.get(pk=cart_id, seller_shop_id=shop_id)
        except ObjectDoesNotExist:
            return {'error': "Cart Does Not Exist"}
        if not self.request.data.get('coupon_id') and not self.request.data.get('spot_discount'):
            return {'error': "Provide Coupon Id/Spot Discount"}
        if self.request.data.get('coupon_id') and self.request.data.get('spot_discount'):
            return {'error': "Provide either of coupon_id or spot_discount"}
        if self.request.data.get('spot_discount') and self.request.data.get('is_percentage') not in [0, 1]:
            return {'error': "Provide a valid spot discount type"}
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
            cart = Cart.objects.get(pk=cart_id, seller_shop_id=shop_id)
        except ObjectDoesNotExist:
            return {'error': "Cart Does Not Exist"}
        return {'cart': cart}

    def serialize(self, cart, offers=None):
        """
            Checkout serializer
            Payment Info plus Offers
        """
        serializer = CheckoutSerializer(Cart.objects.get(pk=cart.id))
        response = serializer.data
        if offers:
            response['available_offers'] = offers
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
            cart = Cart.objects.get(id=pk, last_modified_by=self.request.user, cart_status__in=['active', 'pending'],
                                    cart_type='BASIC', seller_shop_id=shop_id)
        except:
            return get_response("Cart Not Found")
        return self.add_customer_to_cart(cart, shop_id)

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

    def add_customer_to_cart(self, cart, shop_id):
        """
            Update customer details in basic cart
        """
        ph_no = self.request.data.get('phone_number')
        name = self.request.data.get('name')
        email = self.request.data.get('email')
        if not ph_no:
            return get_response("Please provide customer phone number")
        # Check Customer - Update Or Create
        try:
            customer = User.objects.get(phone_number=ph_no)
        except ObjectDoesNotExist:
            customer = User.objects.create_user(phone_number=ph_no)
            if email:
                customer.email = email
            if name:
                customer.first_name = name
            customer.is_active = False
            customer.save()
            create_user_shop_mapping(user=customer, shop_id=shop_id)
        # Update customer as buyer in cart
        cart.buyer = customer
        cart.save()
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
        carts = Cart.objects.filter(seller_shop_id=shop_id, cart_status__in=['active', 'pending']). \
            order_by('-created_at')
        if search_text:
            carts = carts.filter(Q(order_id__icontains=search_text) |
                                 Q(buyer__phone_number__icontains=search_text) |
                                 Q(id__icontains=search_text))

        open_orders = BasicCartListSerializer(carts, many=True)
        """
           Pagination on Cart List
        """
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
            cart = Cart.objects.get(last_modified_by=self.request.user, seller_shop=shop, cart_type='BASIC',
                                    id=self.request.GET.get('cart_id'), cart_status__in=['active', 'pending'])
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
            orders = orders.filter(order_status=order_status)
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
                                                          ).values('retailer_product', 'qty', 'product_type')
        for product_map in cart_products:
            # Order Item
            ordered_product_mapping = OrderedProductMapping.objects.create(ordered_product=shipment,
                                                                           retailer_product_id=product_map[
                                                                               'retailer_product'],
                                                                           product_type=product_map[
                                                                               'product_type'],
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
        # TODO with returns
        shipment.shipment_status = 'FULLY_DELIVERED_AND_VERIFIED'
        shipment.save()


class OrderedItemCentralDashBoard(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
            Get Order, Product & User Counts(Overview)
            Inputs
            cart_type
            shop_id for retail(Buyer shop id)
        """
        cart_type = request.GET.get('cart_type')
        if cart_type == '1':
            return self.get_retail_order_overview()
        elif cart_type == '2':
            return self.get_basic_order_overview()
        else:
            return get_response('Provide a valid cart_type')

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
        return get_response('Order', self.get_serialize_process(order))

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
            # get total orders for given shop_id & order_status
            orders = orders.filter(order_status=order_status)

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
