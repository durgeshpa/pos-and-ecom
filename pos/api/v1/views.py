from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist

from sp_to_gram.tasks import es_search
from audit.views import BlockUnblockProduct
from retailer_to_sp.api.v1.serializers import CartSerializer, GramMappedCartSerializer, ParentProductImageSerializer
from retailer_backend.common_function import getShopMapping
from retailer_backend.messages import ERROR_MESSAGES
from wms.common_functions import get_stock
from accounts.models import User
from wms.models import InventoryType
from products.models import Product
from categories import models as categorymodel
from retailer_to_sp.models import Cart, CartProductMapping, Order, check_date_range
from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping)
from shops.models import Shop
from brand.models import Brand
from pos.models import RetailerProduct
from pos.common_functions import get_response, delete_cart_mapping

from .serializers import ProductDetailSerializer


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


class RetailerProductsList(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def search_query(self, request):
        """
            Es Search query to search for retailer products based on name, brand, category
        """
        filter_list = []
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
        """
            Modify Es results for response
        """
        p_list = []
        for p in products_list['hits']['hits']:
            mrp = p["_source"]["mrp"]
            sp = p["_source"]["selling_price"]
            p["_source"]["margin"] = ((mrp - sp) / mrp) * 100
            p_list.append(p["_source"])
        return p_list

    def get(self, request):
        """
        API to search for retailer products of a particular shop
        Inputs:
        shop_id
        product_name
        product_ids
        brands
        categories
        """
        shop_id = request.GET.get('shop_id')
        if not Shop.objects.filter(id=shop_id, status=True).exists():
            return get_response('Shop Not Found/Active')
        query = self.search_query(request)
        body = {"from": 0, "size": 5, "query": query, "_source": {"includes": ["name", "selling_price", "mrp",
                                                                               "images"]}}
        products_list = es_search(index="rp-{}".format(shop_id), body=body)
        p_list = self.process_results(products_list)
        return get_response('Products Found For Shop' if p_list else 'No Products Found', p_list)


class EanSearch(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
            API to search GramFactory product catalogue based on product ean code exact match
            Inputs
            ean_code
        """
        ean_code = request.GET.get('ean_code')
        if ean_code and ean_code != '':
            body = {
                "from": int(request.GET.get('offset', 0)),
                "size": int(request.GET.get('pro_count', 50)),
                "query": {"bool": {"filter": [{"term": {"status": True}}, {"match": {"ean": {"query": ean_code}}}]}},
                "_source": {
                    "includes": ["id", "name", "product_images"]}
            }
            products_list = es_search(index="all_products", body=body)
            p_list = self.process_results(products_list)
            return get_response('Products Found' if p_list else 'No Products Found', p_list)
        else:
            return get_response('Provide Ean Code')

    def process_results(self, products_list):
        p_list = []
        for p in products_list['hits']['hits']:
            p_list.append(p["_source"])
        return p_list


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
                cart_type (retail or basic)
                phone_number (Customer phone number for 'basic' cart)
        """
        cart_type = request.GET.get('cart_type')
        if cart_type == 'retail':
            return self.get_retail_cart(request)
        elif cart_type == 'basic':
            return self.get_basic_cart(request)
        else:
            return get_response('Please provide a valid cart_type')

    def post(self, request):
        """
            Add To Cart
            Inputs
                cart_type (retail or basic)
                cart_product (Product for 'retail', RetailerProduct for 'basic'
                shop_id (Buyer shop id for 'retail', Shop id for selling shop in case of 'basic')
                qty (Quantity of product to be added)
                phone_number (Customer phone number for 'basic' cart)
        """
        cart_type = request.POST.get('cart_type')
        if cart_type == 'retail':
            return self.retail_add_to_cart(request)
        elif cart_type == 'basic':
            return self.basic_add_to_cart(request)
        else:
            return get_response('Please provide a valid cart_type')

    def get_retail_cart(self, request):
        """
            Get Cart
            For cart_type "retail"
        """
        # basic validations for inputs
        initial_validation = self.get_retail_validate(request)
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
                # Process response - Product images, MRP check, Serialize
                search_text = request.GET.get('search_text', '')
                page_number = request.GET.get('page_number', 1)
                records_per_page = request.GET.get('records_per_page', 10)
                return get_response('Cart', self.get_serialize_process(cart, seller_shop, buyer_shop, shop_type,
                                                                       search_text, page_number, records_per_page))
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
                    return get_response('Cart', self.get_serialize_process(cart, seller_shop, buyer_shop, shop_type))
            else:
                return get_response('Sorry no product added to this cart yet')
        else:
            return get_response('Sorry shop is not associated with any GramFactory or any SP')

    def get_basic_cart(self, request):
        """
            Get Cart
            For cart_type "basic"
        """
        # basic validations for inputs
        initial_validation = self.get_basic_validate(request)
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        seller_shop = initial_validation['shop']
        customer = initial_validation['customer']
        user = self.request.user

        if Cart.objects.filter(last_modified_by=user, seller_shop=seller_shop, buyer=customer,
                               cart_status__in=['active', 'pending']).exists():
            cart = Cart.objects.filter(last_modified_by=user, seller_shop=seller_shop, buyer=customer,
                                       cart_status__in=['active', 'pending']).last()
            search_text = request.GET.get('search_text', '')
            page_number = request.GET.get('page_number', 1)
            records_per_page = request.GET.get('records_per_page', 10)
            return get_response('Cart', self.get_serialize_process(cart, '', '', '', search_text, page_number,
                                                                   records_per_page))
        else:
            return get_response('Sorry no product added to this cart yet')

    def get_retail_validate(self, request):
        """
            Get Cart
            Input validation for cart type 'retail'
        """
        shop_id = request.GET.get('shop_id')
        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            return {'error': "Shop Doesn't Exist!"}
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            return {'error': "Shop Mapping Doesn't Exist!"}
        return {'buyer_shop': parent_mapping.retailer, 'seller_shop': parent_mapping.parent,
                'shop_type': parent_mapping.parent.shop_type.shop_type}

    def get_basic_validate(self, request):
        """
            Get Cart
            Input validation for cart type 'basic'
        """
        # check if shop exists
        try:
            shop = Shop.objects.get(id=request.GET.get('shop_id'))
        except ObjectDoesNotExist:
            return {'error': "Shop Doesn't Exist!"}
        # Check Customer
        try:
            customer = User.objects.get(phone_number=request.GET.get('phone_number'))
        except ObjectDoesNotExist:
            return {'error': "User/Customer Not Found"}
        return {'shop': shop, 'customer': customer}

    @staticmethod
    def filter_cart_products(cart, seller_shop):
        """
            Filter/Delete cart products that are blocked for audit etc
        """
        cart_products = CartProductMapping.objects.select_related('cart_product').filter(cart=cart)
        cart_product_to_be_deleted = []
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

    def get_serialize_process(self, cart, seller_shop='', buyer_shop='', shop_type='', search_text='', page_number=1,
                              records_per_page=10):
        """
            Get Cart
            Serialize and Modify Cart - Parent Product Image Check, MRP Check
        """
        if shop_type == 'sp':
            # Serialize Get Cart
            serializer = CartSerializer(Cart.objects.get(id=cart.id), context={'parent_mapping_id': seller_shop.id,
                                                                               'buyer_shop_id': buyer_shop.id,
                                                                               'search_text': search_text,
                                                                               'page_number': page_number,
                                                                               'records_per_page':records_per_page,
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
        elif shop_type == 'gf':
            # Serialize Get Cart
            serializer = GramMappedCartSerializer(GramMappedCart.objects.get(id=cart.id),
                                                  context={'parent_mapping_id': seller_shop.id,
                                                           'delivery_message': self.delivery_message()})
        else:
            serializer = CartSerializer(cart, context={'search_text': search_text, 'page_number': page_number,
                                                       'records_per_page':records_per_page})
        return serializer.data

    def retail_add_to_cart(self, request):
        """
            Add To Cart
            For cart type 'retail'
        """
        # basic validations for inputs
        initial_validation = self.post_retail_validate(request)
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
            return get_response('Added To Cart',
                                self.post_serialize_process(cart, seller_shop, buyer_shop, product, shop_type))
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
            return get_response('Added To Cart',
                                self.post_serialize_process(cart, seller_shop, buyer_shop, product, shop_type))
        else:
            return get_response('Sorry shop is not associated with any Gramfactory or any SP')

    def basic_add_to_cart(self, request):
        """
            Add To Cart
            For cart type 'basic'
        """
        # basic validations for inputs
        initial_validation = self.post_basic_validate(request)
        if 'error' in initial_validation:
            return get_response(initial_validation['error'])
        product = initial_validation['product']
        shop = initial_validation['shop']
        qty = initial_validation['quantity']
        customer = initial_validation['customer']

        # Update or create cart for customer and shop
        cart = self.post_update_basic_cart(shop, customer)
        # Add quantity to cart
        cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, retailer_product=product)
        cart_mapping.qty = qty
        cart_mapping.no_of_pieces = int(qty)
        cart_mapping.save()
        # serialize and return response
        return get_response('Added To Cart', self.post_serialize_process(cart))

    def post_retail_validate(self, request):
        """
            Add To Cart
            Input validation for cart type 'retail'
        """
        qty = request.POST.get('qty')
        shop_id = request.POST.get('shop_id')
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
            product = Product.objects.get(id=request.POST.get('cart_product'))
        except ObjectDoesNotExist:
            return {'error': "Product Not Found!"}
        # Check if the product is blocked for audit
        is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(product, parent_mapping.parent)
        if is_blocked_for_audit:
            return {'error': ERROR_MESSAGES['4019'].format(product)}
        return {'product': product, 'buyer_shop': parent_mapping.retailer, 'seller_shop': parent_mapping.parent,
                'quantity': qty, 'shop_type': parent_mapping.parent.shop_type.shop_type}

    def post_basic_validate(self, request):
        """
            Add To Cart
            Input validation for add to cart for cart type 'basic'
        """
        qty = request.POST.get('qty')
        # Added Quantity check
        if qty is None or qty == '':
            return {'error': "Qty Not Found!"}
        # Check if shop exists
        try:
            shop = Shop.objects.get(id=request.POST.get('shop_id'))
        except ObjectDoesNotExist:
            return {'error': "Shop Doesn't Exist!"}
        # Check if product exists for that shop
        try:
            product = RetailerProduct.objects.get(id=request.POST.get('cart_product'), shop=shop)
        except ObjectDoesNotExist:
            return {'error': "Product Not Found!"}
        # Check Customer
        try:
            customer = User.objects.get(phone_number=request.POST.get('phone_number'))
        except ObjectDoesNotExist:
            return {'error': "User/Customer Not Found"}
        return {'product': product, 'shop': shop, 'quantity': qty, 'customer': customer}

    def post_update_retail_sp_cart(self, seller_shop, buyer_shop):
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

    def post_update_basic_cart(self, seller_shop, customer):
        user = self.request.user
        if Cart.objects.filter(last_modified_by=user, seller_shop=seller_shop, buyer=customer,
                               cart_status__in=['active', 'pending']).exists():
            cart = Cart.objects.filter(last_modified_by=user, seller_shop=seller_shop, buyer=customer,
                                       cart_status__in=['active', 'pending']).last()
            cart.cart_type = 'BASIC'
            cart.approval_status = False
            cart.cart_status = 'active'
            cart.seller_shop = seller_shop
            cart.buyer = customer
            cart.save()
        else:
            cart = Cart(last_modified_by=user, cart_status='active')
            cart.cart_type = 'BASIC'
            cart.approval_status = False
            cart.seller_shop = seller_shop
            cart.buyer = customer
            cart.save()
        return cart

    @staticmethod
    def retail_ordered_quantity(capping, product, buyer_shop):
        """
            Get ordered quantity for buyer shop in case of retail cart to check capping
        """
        ordered_qty = 0
        capping_start_date, capping_end_date = check_date_range(capping)
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
        available_qty = shop_products_dict[int(product.id)] // int(
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
        return cart_mapping

    def retail_capping_check(self, product, seller_shop, buyer_shop, qty, cart):
        """
            Add To Cart
            check if capping is applicable to retail cart product
        """
        capping = product.get_current_shop_capping(seller_shop, buyer_shop)
        if capping:
            ordered_qty = self.retail_ordered_quantity(capping, product, buyer_shop)
            if capping.capping_qty > ordered_qty:
                if (capping.capping_qty - ordered_qty) >= int(qty):
                    if int(qty) == 0:
                        delete_cart_mapping(cart, product)
                    else:
                        return {'is_success': True, 'quantity_check': True}
                else:
                    serializer = CartSerializer(Cart.objects.get(id=cart.id), context={
                        'parent_mapping_id': seller_shop.id, 'buyer_shop_id': buyer_shop.id})
                    if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                        cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                        cart_mapping.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
                                capping.capping_qty - ordered_qty)]
                        cart_mapping.save()
                    else:
                        return {'is_success': False, 'message': 'The Purchase Limit of the Product is %s #%s' % (
                            capping.capping_qty - ordered_qty, product.id), 'data': serializer.data}
            else:
                delete_cart_mapping(cart, product)
                serializer = CartSerializer(Cart.objects.get(id=cart.id), context={
                    'parent_mapping_id': seller_shop.id, 'buyer_shop_id': buyer_shop.id})
                return {'is_success': False, 'message': 'You have already exceeded the purchase limit of'
                                                        ' this product #%s' % product.id, 'data': serializer.data}
        else:
            if int(qty) == 0:
                delete_cart_mapping(cart, product)
            else:
                return {'is_success': True, 'quantity_check': True}
        return {'is_success': True, 'quantity_check': False}

    def post_serialize_process(self, cart, seller_shop='', buyer_shop='', product='', shop_type=''):
        """
            Add To Cart
            Serialize and Modify Cart - MRP Check
        """
        if shop_type == 'sp':
            serializer = CartSerializer(cart, context={'parent_mapping_id': seller_shop.id,
                                                       'buyer_shop_id': buyer_shop.id})
            for i in serializer.data['rt_cart_list']:
                if not i['cart_product']['product_mrp']:
                    delete_cart_mapping(cart, product)
        elif shop_type == 'gf':
            serializer = GramMappedCartSerializer(cart,
                                                  context={'parent_mapping_id': seller_shop.id})
        else:
            serializer = CartSerializer(cart)
        return serializer.data
