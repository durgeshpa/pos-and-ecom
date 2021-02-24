from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist

from sp_to_gram.tasks import es_search
from audit.views import BlockUnblockProduct
from retailer_to_sp.api.v1.serializers import CartSerializer, GramMappedCartSerializer
from retailer_backend.common_function import getShopMapping
from retailer_backend.messages import ERROR_MESSAGES
from wms.common_functions import get_stock

from wms.models import InventoryType
from products.models import Product
from categories import models as categorymodel
from retailer_to_sp.models import Cart, CartProductMapping, Order, check_date_range
from retailer_to_gram.models import (Cart as GramMappedCart, CartProductMapping as GramMappedCartProductMapping)
from shops.models import Shop
from brand.models import Brand
from pos.models import RetailerProduct

from .serializers import ProductDetailSerializer


class ProductDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, *args, **kwargs):
        """
            API to get information of existing GramFactory product
        """
        pk = self.kwargs.get('pk')
        msg = {'is_success': False, 'message': '', 'response_data': None}
        try:
            product = Product.objects.get(id=pk)
        except ObjectDoesNotExist:
            msg['message'] = 'Invalid Product ID'
            return Response(msg, status=status.HTTP_200_OK)

        product_detail_serializer = ProductDetailSerializer(product)
        return Response(
            {"message": 'Product Found', "response_data": product_detail_serializer.data, "is_success": True})


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

    def get_response(self, data, msg):
        if data:
            ret = {"message": msg, "response_data": data, "is_success": True}
        else:
            ret = {"message": msg, "response_data": None, "is_success": False}
        return Response(ret, status=200)

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
            return self.get_response([], 'Shop Not Found/Active')
        query = self.search_query(request)
        body = {"from": 0, "size": 5, "query": query, "_source": {"includes": ["name", "selling_price", "mrp",
                                                                               "images"]}}
        products_list = es_search(index="rp-{}".format(shop_id), body=body)
        p_list = self.process_results(products_list)
        return self.get_response(p_list, 'Products Found For Shop' if p_list else 'No Products Found')


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
            return self.get_response(p_list, 'Products Found' if p_list else 'No Products Found')
        else:
            return self.get_response([], 'Provide Ean Code')

    def process_results(self, products_list):
        p_list = []
        for p in products_list['hits']['hits']:
            p_list.append(p["_source"])
        return p_list

    def get_response(self, data, msg):
        if data:
            ret = {"message": msg, "response_data": data, "is_success": True}
        else:
            ret = {"message": msg, "response_data": None, "is_success": False}
        return Response(ret, status=200)


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
        return self.get_response(p_list, 'Products Found' if p_list else 'No Products Found')

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

    def get_response(self, data, msg):
        if data:
            ret = {"message": msg, "response_data": data, "is_success": True}
        else:
            ret = {"message": msg, "response_data": None, "is_success": False}
        return Response(ret, status=200)


class CartCentral(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
            Add To Cart
            Inputs
            cart_type (retail- or basic)
            cart_product (Product for 'retail', RetailerProduct for 'basic'
            shop_id (Buyer shop id for 'retail', Shop id for selling shop in case of 'basic')
            qty (Quantity of product to be added)
        """
        cart_type = request.POST.get('cart_type')
        if cart_type == 'retail':
            return self.retail_add_to_cart(request)
        elif cart_type == 'basic':
            return self.basic_add_to_cart(request)
        else:
            msg = {'is_success': False, 'message': ['Please provide a valid cart_type'], 'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)

    def retail_add_to_cart(self, request):
        """
            Add to Cart for cart type 'retail'
        """
        # basic validations for inputs
        initial_validation = self.retail_cart_validate(request)
        if not initial_validation['is_success']:
            return Response(initial_validation, status=status.HTTP_200_OK)
        product = initial_validation['data']['product']
        buyer_shop = initial_validation['data']['buyer_shop']
        seller_shop = initial_validation['data']['seller_shop']
        shop_type = initial_validation['data']['shop_type']
        qty=initial_validation['data']['quantity']

        # If Seller Shop is sp Type
        if shop_type == 'sp':
            # Update or create cart for user and shop
            cart = self.update_cart(seller_shop, 'RETAIL', buyer_shop)
            # check for product capping
            proceed = self.retail_capping_check(product, seller_shop, buyer_shop, qty, cart)
            if not proceed['is_success']:
                return Response(proceed['message'], status=status.HTTP_200_OK)
            elif proceed['quantity_check']:
                # check for product available quantity and add to cart
                self.retail_quantity_check(seller_shop, product, cart, qty)
            # process and return response
            return self.get_response(cart, seller_shop, buyer_shop, product, shop_type)
        # If Seller Shop is gf type
        elif shop_type == 'gf':
            # Update or create cart for user
            cart = self.update_cart(self, seller_shop, 'gram_mapped', buyer_shop)
            # check quantity and add to cart
            if int(qty) == 0:
                if GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                    GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
            else:
                cart_mapping, _ = GramMappedCartProductMapping.objects.get_or_create(cart=cart, cart_product=product)
                cart_mapping.qty = qty
                cart_mapping.save()
            # process and return response
            return self.get_response(cart, seller_shop, buyer_shop, product, shop_type)
        else:
            msg = {'is_success': False,
                   'message': ['Sorry shop is not associated with any Gramfactory or any SP'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_200_OK)

    def basic_add_to_cart(self, request):
        """
            Add to Cart for cart type 'basic'
        """
        # basic validations for inputs
        initial_validation = self.basic_cart_validate(request)
        if not initial_validation['is_success']:
            return Response(initial_validation, status=status.HTTP_200_OK)
        product = initial_validation['data']['product']
        shop = initial_validation['data']['shop']
        qty = initial_validation['data']['quantity']

        # doubt buyer seller cart??? single object ???
        # Update or create cart for user and shop
        cart = self.update_cart(shop, 'BASIC', '')
        # Add quantity to cart
        cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart, basic_cart_product=product)
        cart_mapping.qty = qty
        cart_mapping.no_of_pieces = int(qty)
        cart_mapping.save()
        # return response
        msg = {'is_success': True, 'message': ['Data Added To Cart'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def retail_cart_validate(self, request):
        """
            Input validation for add to cart for cart type 'retail'
        """
        result = {'is_success': False}
        qty = request.POST.get('qty')
        shop_id = request.POST.get('shop_id')
        # Added Quantity check
        if qty is None or qty == '':
            result['message'] = "Qty Not Found!"
            return result
        # Check if buyer shop exists
        if not Shop.objects.filter(id=shop_id).exists():
            result['message'] = "Shop Doesn't Exist!"
            return result
        # Check if buyer shop is mapped to parent/seller shop
        parent_mapping = getShopMapping(shop_id)
        if parent_mapping is None:
            result['message'] = "Shop Mapping Doesn't Exist!"
            return result
        # Check if product exists
        try:
            product = Product.objects.get(id=request.POST.get('cart_product'))
        except ObjectDoesNotExist:
            result['message'] = "Product Not Found!"
            return result
        # Check if the product is blocked for audit
        is_blocked_for_audit = BlockUnblockProduct.is_product_blocked_for_audit(product, parent_mapping.parent)
        if is_blocked_for_audit:
            result['message'] = ERROR_MESSAGES['4019'].format(product)
            return result
        return {'is_success': True, 'data': {'product':product, 'buyer_shop':parent_mapping.retailer,
                                                      'seller_shop':parent_mapping.parent,
                                                      'shop_type':parent_mapping.parent.shop_type.shop_type,
                                                      'quantity':qty}}

    def basic_cart_validate(self, request):
        """
            Input validation for add to cart for cart type 'basic'
        """
        result = {'is_success': False}
        qty = request.POST.get('qty')
        # Added Quantity check
        if qty is None or qty == '':
            result['message'] = "Qty Not Found!"
            return result
        # Check if shop exists
        try:
            shop = Shop.objects.get(id=request.POST.get('shop_id'))
        except ObjectDoesNotExist:
            result['message'] = "Shop Doesn't Exist!"
            return result
        # Check if product exists for that shop
        try:
            product = RetailerProduct.objects.get(id=request.POST.get('cart_product'), shop=shop)
        except ObjectDoesNotExist:
            result['message'] = "Product Not Found!"
            return result
        return {'is_success': True, 'data': {'product': product, 'shop': shop, 'quantity': qty}}

    def update_cart(self, seller_shop, cart_type, buyer_shop):
        """
            Update cart object for gram_mapped or normal cart
        """
        user = self.request.user
        if cart_type != 'gram_mapped':
            if Cart.objects.filter(last_modified_by=user, buyer_shop=buyer_shop,
                                   cart_status__in=['active', 'pending']).exists():
                cart = Cart.objects.filter(last_modified_by=user, buyer_shop=buyer_shop,
                                           cart_status__in=['active', 'pending']).last()
                cart.cart_type = cart_type
                cart.approval_status = False
                cart.cart_status = 'active'
                cart.seller_shop = seller_shop
                cart.buyer_shop = buyer_shop
                cart.save()
            else:
                cart = Cart(last_modified_by=user, cart_status='active')
                cart.cart_type = cart_type
                cart.approval_status = False
                cart.seller_shop = seller_shop
                cart.buyer_shop = buyer_shop
                cart.save()
        else:
            if GramMappedCart.objects.filter(last_modified_by=user, cart_status__in=['active', 'pending']).exists():
                cart = GramMappedCart.objects.filter(last_modified_by=user, cart_status__in=['active', 'pending']).last()
                cart.cart_status = 'active'
                cart.save()
            else:
                cart = GramMappedCart(last_modified_by=user, cart_status='active')
                cart.save()
        return cart

    def retail_ordered_quantity(self, capping, product, buyer_shop):
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

    def retail_quantity_check(self, seller_shop, product, cart, qty):
        """
            Check available quantity of product for adding to retail cart
        """
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        shop_products_dict = get_stock(seller_shop, type_normal, [product.id])
        cart_mapping, _ = CartProductMapping.objects.get_or_create(cart=cart,
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

    def retail_capping_check(self, product, seller_shop, buyer_shop, qty, cart):
        """
            check if capping is applicable to retail cart product
        """
        capping = product.get_current_shop_capping(seller_shop, buyer_shop)
        if capping:
            ordered_qty = self.retail_ordered_quantity(capping, product, buyer_shop)
            if capping.capping_qty > ordered_qty:
                if (capping.capping_qty - ordered_qty) >= int(qty):
                    if int(qty) == 0:
                        self.delete_cart_mapping(cart, product)
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
                        msg = {'is_success': True, 'message': ['The Purchase Limit of the Product is %s #%s' % (
                            capping.capping_qty - ordered_qty, product.id)], 'response_data': serializer.data}
                        return {'is_success': False, 'message': msg}
            else:
                if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                    CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
                serializer = CartSerializer(Cart.objects.get(id=cart.id), context={
                    'parent_mapping_id': seller_shop.id, 'buyer_shop_id': buyer_shop.id})
                msg = {'is_success': True, 'message': [
                    'You have already exceeded the purchase limit of this product #%s' % (
                        product.id)], 'response_data': serializer.data}
                return {'is_success': False, 'message': msg}
        else:
            if int(qty) == 0:
                self.delete_cart_mapping(cart, product)
            else:
                return {'is_success': True, 'quantity_check': True}
        return {'is_success': True, 'quantity_check': False}

    def delete_cart_mapping(self, cart, product, cart_type='retail'):
        """
            Delete Cart items
        """
        if cart_type == 'retail':
            if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
                CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()

    def get_response(self, cart, seller_shop, buyer_shop, product, shop_type):
        """
            Return response for Add to Cart
        """
        if cart.rt_cart_list.count() <= 0:
            msg = {'is_success': False, 'message': ['Sorry, no product added to this cart yet'], 'response_data': None}
        else:
            if shop_type == 'sp':
                serializer = CartSerializer(cart,
                                            context={'parent_mapping_id': seller_shop.id,
                                                     'buyer_shop_id': buyer_shop.id})
                for i in serializer.data['rt_cart_list']:
                    if i['cart_product']['product_mrp'] == False:
                        CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
            elif shop_type == 'gf':
                serializer = GramMappedCartSerializer(cart,
                                                      context={'parent_mapping_id': seller_shop.id})
            else:
                serializer = CartSerializer(cart,
                                            context={'parent_mapping_id': seller_shop.id,
                                                     'buyer_shop_id': buyer_shop.id})
            msg = {'is_success': True, 'message': ['Data added to cart'], 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)
