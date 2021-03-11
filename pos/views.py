import codecs
import csv
import decimal

from dal import autocomplete
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status, authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import transaction

from pos.common_functions import RetailerProductCls, OffersCls, get_shop_id_from_token, serializer_error
from pos.serializers import RetailerProductCreateSerializer, RetailerProductUpdateSerializer, \
    RetailerProductResponseSerializer, CouponCodeSerializer, ComboDealsSerializer,\
    CouponCodeUpdateSerializer, ComboDealsUpdateSerializer, CouponCodeGetSerializer, ComboCodeGetSerializer, Combo
from pos.forms import RetailerProductsCSVDownloadForm, RetailerProductsCSVUploadForm
from pos.models import RetailerProduct, RetailerProductImage
from products.models import Product, ParentProductCategory
from shops.models import Shop
from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon
from global_config.models import GlobalConfig


POS_SERIALIZERS_MAP = {
    '0': RetailerProductCreateSerializer,
    '1': RetailerProductUpdateSerializer
}


class CatalogueProductCreation(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

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
            return POS_SERIALIZERS_MAP['0']
        if data == 1:
            return POS_SERIALIZERS_MAP['1']

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
                description = request.data.get('description') if request.data.get('description') else ''
                # if else condition for checking whether, Product we are creating is linked with existing product or not
                # with the help of 'linked_product_id'
                if request.data.get('linked_product_id'):
                    # If product is linked with existing product
                    if Product.objects.filter(id=request.data.get('linked_product_id')).exists():
                        product = Product.objects.filter(id=request.data.get('linked_product_id'))
                        if str(product.values()[0].get('product_mrp')) == format(
                                decimal.Decimal(request.data.get('mrp')), ".2f"):
                            # If Linked_Product_MRP == Input_MRP , create a Product with [SKU TYPE : LINKED]
                            RetailerProductCls.create_retailer_product(shop_id_or_error_message,
                                                                       product_name, mrp, selling_price,
                                                                       linked_product_id, 2, description)
                        else:
                            # If Linked_Product_MRP != Input_MRP, Create a new Product with SKU_TYPE == "LINKED_EDITED"
                            RetailerProductCls.create_retailer_product(shop_id_or_error_message,
                                                                       product_name, mrp, selling_price,
                                                                       linked_product_id, 3, description)
                else:
                    # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
                    RetailerProductCls.create_retailer_product(shop_id_or_error_message, product_name, mrp,
                                                               selling_price, None, 1, description)
                product = RetailerProduct.objects.all().last()
                # Fetching the data of created product
                data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp', 'selling_price',
                                                      'description', 'sku_type',
                                                      'linked_product__product_name', 'created_at',
                                                      'modified_at').filter(id=product.id)
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
                if RetailerProduct.objects.filter(id=product_id,
                                                  shop_id=shop_id_or_error_message).exists():
                    expected_input_data_list = ['product_name', 'product_id', 'mrp', 'selling_price', 'description']
                    actual_input_data_list = []  # List of keys that user wants to update(If user wants to update product_name, this list wil only have product_name)
                    for key in expected_input_data_list:
                        if key in request.data.keys():
                            actual_input_data_list.append(key)
                    product = RetailerProduct.objects.get(id=product_id)
                    linked_product_id = product.linked_product_id
                    if linked_product_id:
                        if 'mrp' in actual_input_data_list:
                            # If MRP in actual_input_data_list
                            linked_product = Product.objects.filter(id=linked_product_id)
                            if format(decimal.Decimal(mrp), ".2f") == str(
                                    linked_product.values()[0].get('product_mrp')):
                                # If Input_MRP == Product_MRP, Update the product with [SKU Type : Linked]
                                product.sku_type = 2
                            else:
                                # If Input_MRP != Product_MRP, Update the product with [SKU Type : Linked Edited]
                                product.sku_type = 3
                    if 'mrp' in actual_input_data_list:
                        # If MRP in actual_input_data_list
                        product.mrp = mrp
                    if 'selling_price' in actual_input_data_list:
                        # If selling price in actual_input_data_list
                        product.selling_price = request.data.get('selling_price')
                    if 'product_name' in actual_input_data_list:
                        # Update Product Name
                        product.name = request.data.get('product_name')
                    if 'description' in actual_input_data_list:
                        # Update Description
                        product.description = request.data.get('description')
                    product.save()

                    data = RetailerProduct.objects.values('id', 'shop__shop_name', 'name', 'sku', 'mrp',
                                                          'selling_price', 'description', 'sku_type',
                                                          'linked_product__product_name', 'created_at',
                                                          'modified_at').filter(id=request.data.get('product_id'))
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
            combo_coupon_id = request.data.get('id')
            if combo_coupon_id:
                coupon_offers = self.get_coupons_combo_offers_by_id(request, shop_id, combo_coupon_id)
            else:
                coupon_offers = self.get_serialize_process(request, shop_id)
            msg = {"is_success": True, "message": "Coupon/Offers Retrieved Successfully",
                   "response_data": coupon_offers}
            return Response(msg, status=200)
        else:
            msg = {'is_success': False, 'error_message':  f"There is no shop available with (shop id : {shop_id}) ",
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
                    except:
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

    def put(self,  request, *args, **kwargs):
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
                        except:
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
                        except:
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
        else:
            msg = {'is_success': False, 'error_message': f"There is no shop available with (shop id : {shop_id})",
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    def get_coupons_combo_offers_by_id(self, request, shop_id, combo_coupon_id):
        """
          Get Offers/Coupons
          Serialize Offers/Coupons
       """
        rule_type = request.data.get('rule_type')
        if int(rule_type) == 1:
            """
              rule_type is Coupon Code getting Coupon
            """
            offers = Coupon.objects.filter(shop=shop_id, id=combo_coupon_id).order_by('-created_at').\
                values('id', 'coupon_type', 'coupon_name', 'coupon_code', 'start_date', 'expiry_date')
        else:
            """
                 rule_type is Coupon Code getting Combo offer
            """
            offers = Coupon.objects.filter(shop=shop_id, id=combo_coupon_id).order_by('-created_at').\
                values('id', 'coupon_type', 'rule__id')
            for offer in offers:
                offers = RuleSetProductMapping.objects.filter(rule=offer['rule__id']).order_by('-created_at').\
                    values('rule__id', 'retailer_primary_product__name',
                           'retailer_free_product__name', 'start_date', 'expiry_date',)
        return offers

    def get_serialize_process(self, request, shop_id):
        """
          Get Offers/Coupons
          Serialize Offers/Coupons
       """
        coupon_offers = []
        if request.GET.get('search_text'):
            """
                 Get Offers/Coupons when search_text is given in params
            """
            for coupons in Coupon.objects.filter(shop=shop_id, coupon_name__icontains=request.GET.get('search_text')).order_by('-created_at'):
                serializer = CouponCodeGetSerializer(coupons)
                coupon_offers.append(serializer.data)
            coupon = Coupon.objects.filter(shop=shop_id, coupon_name__icontains=request.GET.get('search_text'))
            for coupons in coupon:
                for offer in RuleSetProductMapping.objects.filter(combo_offer_name=coupons['coupon_name']).order_by('-created_at'):
                    serializer = Combo(offer)
                    coupon_offers.append(serializer.data)
        else:
            """
                Get Offers/Coupons when search_text is not given in params
           """
            for coupons in Coupon.objects.filter(shop=shop_id).order_by('-created_at').values('rule'):
                serializer = Combo(coupons['rule'])
                coupon_offers.append(serializer.data)
        """
            Pagination on Offers/Coupons
        """
        per_page_coupons_offers = request.GET.get('records_per_page') if request.GET.get('records_per_page') else 10
        paginator = Paginator(coupon_offers, int(per_page_coupons_offers))
        page_number = request.GET.get('page_number')
        try:
            coupon_offers = paginator.page(page_number)
        except PageNotAnInteger:
            coupon_offers = paginator.page(1)
        except EmptyPage:
            coupon_offers = paginator.page(paginator.num_pages)
        coupon_offers_data = {
            'previous_page': coupon_offers.has_previous() and coupon_offers.previous_page_number() or None,
            'next_page': coupon_offers.has_next() and coupon_offers.next_page_number() or None,
            'data': list(coupon_offers)
        }
        return coupon_offers_data

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
            discount_qty_amount = request.data.get('discount_qty_amount')
            # creating Discount
            discount_obj = DiscountValue.objects.create(discount_value=discount_value)
            # creating CouponRuleSet
            coupon_obj = OffersCls.rule_set_creation(coupon_name, start_date, expiry_date, discount_qty_amount,
                                                     discount_obj)

            # creating Coupon with coupon_type(cart)
            OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', coupon_name,
                                            shop, start_date, expiry_date)
            msg = {"is_success": True, "message": "Coupon has been successfully created!",
                   "response_data": serializer.data}
            status_code = {"status_code": 201}
            return msg, status_code

    def create_combo_offer(self, request, serializer, shop_id):
        """
            Creating Ruleset & RuleSetProductMapping
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
            msg = {"is_success": False, "error": "retailer_primary_product Not Found",
                   "response_data": serializer.data },
            status_code = {"status_code": 404}
            return msg, status_code

        retailer_free_product = request.data.get('retailer_free_product')
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=retailer_free_product, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "retailer_free_product Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code

        combo_offer_name = request.data.get('combo_offer_name')
        start_date = request.data.get('start_date')
        expiry_date = request.data.get('expiry_date')
        # creating CouponRuleSet
        coupon_obj = OffersCls.rule_set_creation(combo_offer_name, start_date, expiry_date)
        # creating Combo Offer with primary & free products
        OffersCls.rule_set_product_mapping(coupon_obj.id, retailer_primary_product_obj,
                                           request.data.get('purchased_product_qty'),
                                           retailer_free_product_obj, request.data.get('free_product_qty'),
                                           combo_offer_name, start_date, expiry_date)
        # creating Coupon with coupon_type(catalog)
        OffersCls.rule_set_cart_mapping(coupon_obj.id, 'catalog', combo_offer_name,
                                        shop, start_date, expiry_date)
        msg = {"is_success": True, "message": "Combo Offer has been successfully created!",
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

        coupon_ruleset = CouponRuleSet.objects.get(rulename=coupon.coupon_name)
        discount = DiscountValue.objects.get(id=coupon_ruleset.discount.id)
        expected_input_data_list = ['id', 'coupon_name', 'discount_qty_amount', 'discount_value', 'start_date',
                                    'expiry_date', 'is_active']
        actual_input_data_list = []
        for key in expected_input_data_list:
            if key in request.data.keys():
                actual_input_data_list.append(key)

        if 'coupon_name' in actual_input_data_list:
            # If coupon_name in actual_input_data_list
            coupon_ruleset.rulename = request.data.get('coupon_name')
            coupon.coupon_name = request.data.get('coupon_name')
        if 'discount_qty_amount' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            coupon_ruleset.cart_qualifying_min_sku_value = request.data.get('discount_qty_amount')
        if 'discount_value' in actual_input_data_list:
            # If discount_qty_amount in actual_input_data_list
            discount.discount_value = request.data.get('discount_value')
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
            Updating Ruleset & RuleSetProductMapping
        """
        try:
            coupon = Coupon.objects.get(id=combo_id, shop=shop_id)
        except ObjectDoesNotExist:
            msg = {"is_success": False, "error": "Offer Not Found",
                   "response_data": serializer.data}
            status_code = {"status_code": 404}
            return msg, status_code
        coupon_ruleset = CouponRuleSet.objects.get(rulename=coupon.coupon_name)
        rule_set_product_mapping = RuleSetProductMapping.objects.get(combo_offer_name=coupon.coupon_name)
        expected_input_data_list = ['id', 'combo_offer_name', 'expiry_date', 'start_date',
                                    'retailer_primary_product', 'retailer_free_product', 'purchased_product_qty',
                                    'free_product_qty']
        actual_input_data_list = []
        for key in expected_input_data_list:
            if key in request.data.keys():
                actual_input_data_list.append(key)

        if 'combo_offer_name' in actual_input_data_list:
            # If coupon_name in actual_input_data_list
            coupon_ruleset.rulename = request.data.get('combo_offer_name')
            rule_set_product_mapping.combo_offer_name = request.data.get('combo_offer_name')
            coupon.coupon_name = request.data.get('combo_offer_name')
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

            rule_set_product_mapping.retailer_primary_product = retailer_primary_product_obj
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
            rule_set_product_mapping.retailer_free_product = retailer_free_product_obj
        if 'purchased_product_qty' in actual_input_data_list:
            # If purchased_product_qty in actual_input_data_list
            rule_set_product_mapping.purchased_product_qty = request.data.get('purchased_product_qty')
        if 'free_product_qty' in actual_input_data_list:
            # If free_product_qty in actual_input_data_list
            rule_set_product_mapping.free_product_qty = request.data.get('free_product_qty')
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


class RetailerProductShopAutocomplete(autocomplete.Select2QuerySetView):
    """
    Shop Filter for Retailer and Franchise Shops
    """
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['r', 'f'])
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


def download_retailer_products_list_form_view(request):
    """
    Products Catalogue Download View
    """
    form = RetailerProductsCSVDownloadForm()
    return render(
        request,
        'admin/pos/retailerproductscsvdownload.html',
        {'form': form}
    )


def bulk_create_products(shop_id, uploaded_data_by_user_list):
    """
        This Function will create Product by uploaded_data_by_user_list
    """
    for row in uploaded_data_by_user_list:
        # if else condition for checking whether, Product we are creating is linked with existing product or not
        # with the help of 'linked_product_id'
        if 'linked_product_sku' in row.keys():
            if row.get('linked_product_sku') != '':
                # If product is linked with existing product
                if Product.objects.filter(product_sku=row.get('linked_product_sku')):
                    product = Product.objects.get(product_sku=row.get('linked_product_sku'))
                    if str(product.product_mrp) == format(
                            decimal.Decimal(row.get('mrp')), ".2f"):
                        # If Linked_Product_MRP == Input_MRP , create a Product with [SKU TYPE : LINKED]
                        RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                                   row.get('selling_price'), product.id,
                                                                   2, row.get('description'))
                    else:
                        # If Linked_Product_MRP != Input_MRP, Create a new Product with SKU_TYPE == "LINKED_EDITED"
                        RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                                   row.get('selling_price'), product.id,
                                                                   3, row.get('description'))
        else:
            # If product is not linked with existing product, Create a new Product with SKU_TYPE == "Created"
            RetailerProductCls.create_retailer_product(shop_id, row.get('product_name'), row.get('mrp'),
                                                       row.get('selling_price'), None,
                                                       1, row.get('description'))


def bulk_update_products(request, form ,shop_id, uploaded_data_by_user_list):
    """
       This Function will update Product by uploaded_data_by_user_list
    """
    for row in uploaded_data_by_user_list:
        product_id = row.get('product_id')
        product_mrp = row.get('mrp')
        if RetailerProduct.objects.filter(id=product_id, shop_id=shop_id).exists():
            expected_input_data_list = ['product_name', 'product_id', 'mrp', 'selling_price', 'description']
            actual_input_data_list = []  # List of keys that user wants to update(If user wants to update product_name, this list wil have product_name with product_id)
            for key in expected_input_data_list:
                if key in row.keys():
                    actual_input_data_list.append(key)
            product = RetailerProduct.objects.get(id=product_id)
            linked_product_id = product.linked_product_id
            if linked_product_id:
                if 'mrp' in actual_input_data_list:
                    # If MRP in actual_input_data_list
                    linked_product = Product.objects.filter(id=linked_product_id)
                    if format(decimal.Decimal(product_mrp), ".2f") == str(
                            linked_product.values()[0].get('mrp')):
                        # If Input_MRP == Product_MRP, Update the product with [SKU Type : Linked]
                        product.sku_type = 2
                    else:
                        # If Input_MRP != Product_MRP, Update the product with [SKU Type : Linked Edited]
                        product.sku_type = 3
            if 'mrp' in actual_input_data_list:
                # If MRP in actual_input_data_list
                product.mrp = product_mrp
            if 'selling_price' in actual_input_data_list:
                # If selling price in actual_input_data_list
                product.selling_price = row.get('selling_price')
            if 'product_name' in actual_input_data_list:
                # Update Product Name
                product.name = row.get('product_name')
            if 'description' in actual_input_data_list:
                # Update Description
                product.description = row.get('description')
            product.save()

        else:
            return render(request, 'admin/pos/retailerproductscsvupload.html',
                          {'form': form,
                           'error': f"There is no product available with (product id : {product_id}) "
                                    f"for the (shop_id: {shop_id})", })


def upload_retailer_products_list(request):
    """
    Products Catalogue Upload View
    """
    if request.method == 'POST':
        form = RetailerProductsCSVUploadForm(request.POST, request.FILES)

        if form.errors:
            return render(request, 'admin/pos/retailerproductscsvupload.html', {'form': form})

        if form.is_valid():
            shop_id = request.POST.get('shop')
            product_status = request.POST.get('catalogue_product_status')
            reader = csv.reader(codecs.iterdecode(request.FILES.get('file'), 'utf-8', errors='ignore'))
            header = next(reader, None)
            uploaded_data_by_user_list = []
            csv_dict = {}
            count = 0
            for id, row in enumerate(reader):
                for ele in row:
                    csv_dict[header[count]] = ele
                    count += 1
                uploaded_data_by_user_list.append(csv_dict)
                csv_dict = {}
                count = 0
            if product_status == 'create_products':
                bulk_create_products(shop_id, uploaded_data_by_user_list)
            else:
                bulk_update_products(request, form, shop_id, uploaded_data_by_user_list)

            return render(request, 'admin/pos/retailerproductscsvupload.html',
                          {'form': form,
                           'success': 'Products Created/Updated Successfully!', })
    else:
        form = RetailerProductsCSVUploadForm()
        return render(
            request,
            'admin/pos/retailerproductscsvupload.html',
            {'form': form}
        )


def retailer_products_list(product):
    """
        This function will return product related linked_product_sku, sku_type, category, sub_category, brand & sub_brand
    """
    linked_product_sku = ''
    sku_type = product.sku_type
    sku_type = RetailerProductCls.get_sku_type(sku_type)
    category = ''
    sub_category = ''
    brand = ''
    sub_brand = ''
    if product.linked_product:
        linked_product_sku = product.linked_product.product_sku
        prodct = Product.objects.values('parent_product__parent_brand__brand_name',
                                        'parent_product__parent_brand__brand_parent__brand_name').filter(
                                        Q(id=product.linked_product.id))
        if prodct[0]['parent_product__parent_brand__brand_parent__brand_name']:
           brand = prodct[0]['parent_product__parent_brand__brand_parent__brand_name']
           sub_brand = prodct[0]['parent_product__parent_brand__brand_name']
        else:
            brand = prodct[0]['parent_product__parent_brand__brand_name']

        cat = ParentProductCategory.objects.values('category__category_name',
                                                   'category__category_parent__category_name').filter\
                                                   (parent_product__id=product.linked_product.parent_product.id)
        if cat[0]['category__category_parent__category_name']:
            category = cat[0]['category__category_parent__category_name']
            sub_category = cat[0]['category__category_name']
        else:
            category = cat[0]['category__category_name']
    return linked_product_sku, sku_type, category, sub_category, brand, sub_brand


def DownloadRetailerCatalogue(request, *args):
    """
    This function will return an File in csv format which can be used for Downloading the Product Catalogue
    (It is used when user wants to update retailer products)
    """
    shop_id = request.GET['shop_id']
    filename = "retailer_products_update_sample_file.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
        ['product_id', 'shop', 'product_sku', 'product_name', 'mrp', 'selling_price', 'linked_product_sku',
         'description',
         'sku_type', 'category', 'sub_category', 'brand', 'sub_brand', 'status'])
    if RetailerProduct.objects.filter(shop_id=int(shop_id)).exists():
        retailer_products = RetailerProduct.objects.filter(shop_id=int(shop_id))
        for product in retailer_products:
            product_data = retailer_products_list(product)
            writer.writerow([product.id, product.shop, product.sku, product.name,
                            product.mrp, product.selling_price, product_data[0], product.description,
                            product_data[1], product_data[2], product_data[3], product_data[4],
                            product_data[5], product.status])
    else:
        writer.writerow(["Products for selected shop doesn't exists"])
    return response


def RetailerCatalogueSampleFile(request, *args):
    """
    This function will return an Sample File in csv format which can be used for Downloading RetailerCatalogue Sample File
    (It is used when user wants to create new retailer products)
    """
    filename = "retailer_products_create_sample_file.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['product_name', 'mrp', 'linked_product_sku', 'selling_price', 'description'])
    writer.writerow(['Noodles', '12', 'ORCPCRTOY000000020820', '10', 'XYZ'])
    return response