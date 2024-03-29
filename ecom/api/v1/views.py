import datetime
import logging
from django.db.models import F, Count, Q, Prefetch
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_auth.authentication import TokenAuthentication
from rest_framework.generics import ListAPIView
from rest_framework import status

from accounts.models import User
from categories.models import Category, B2cCategory
from marketing.models import RewardPoint
from pos.common_functions import serializer_error, api_response
from pos.models import RetailerProduct
from retailer_backend.utils import SmallOffsetPagination
from retailer_to_sp.models import Order
from pos.models import ShopCustomerMap
from global_config.views import get_config, get_config_fofo_shop
from global_config.models import GlobalConfig

from ecom.utils import (check_ecom_user, nearby_shops, validate_address_id, check_ecom_user_shop,
                        get_categories_with_products, get_b2c_categories_with_products)
from ecom.models import Address, Tag, ShopUserLocationMappedLog
from shops.models import Shop
from .serializers import (AccountSerializer, RewardsSerializer, TagSerializer, UserLocationSerializer, ShopSerializer,
                          AddressSerializer, CategorySerializer, B2cCategorySerializer, SubCategorySerializer,
                          B2cSubCategorySerializer, TagProductSerializer, Parent_Product_Serilizer,
                          ShopInfoSerializer, PastPurchasedProductSerializer, ReferAndEarnSerializer,
                          RetailerProductSerializer)

from pos.api.v1.serializers import ContectUs

# Get an instance of a logger
from ...common_function import create_shop_user_mapping

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class AccountView(APIView):
    serializer_class = AccountSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @check_ecom_user
    def get(self, request, *args, **kwargs):
        """
        E-Commerce User Account
        """
        serializer = self.serializer_class(self.request.user)
        return api_response("", serializer.data, status.HTTP_200_OK, True)


class RewardsView(APIView):
    serializer_class = RewardsSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @check_ecom_user
    @check_ecom_user_shop
    def get(self, request, *args, **kwargs):
        """
        All Reward Credited/Used Details For User
        """
        shop = kwargs['shop']
        percentage_value = get_config_fofo_shop('Percentage_Value_Of_Each_Point', shop.id)
        serializer = self.serializer_class(RewardPoint.objects.filter(reward_user=self.request.user).
                                           select_related('reward_user').last())
        data = serializer.data
        data['redeemable_discount'] = round((data.get('redeemable_points', 0) * percentage_value) / 100)
        return api_response("", data, status.HTTP_200_OK, True)


class ReferAndEarnView(APIView):
    serializer_class = ReferAndEarnSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @check_ecom_user
    def get(self, request, *args, **kwargs):
        """
        All Reward Credited on user refer
        """
        serializer = self.serializer_class(User.objects.filter(id=self.request.user.id).
                                           prefetch_related('referral_by_user', 'referral_code_user').last())
        return api_response("", serializer.data, status.HTTP_200_OK, True)


class ShopView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @check_ecom_user
    def get(self, request, *args, **kwargs):
        """
        Get nearest franchise retailer from user location - latitude, longitude
        """
        if not int(self.request.GET.get('from_location', '0')):
            # Get shop from latest order
            order = Order.objects.filter(buyer=self.request.user,
                                         ordered_cart__cart_type__in=['BASIC', 'ECOM'],
                                         seller_shop__online_inventory_enabled=True).order_by('id').last()
            if order:
                create_shop_user_mapping(order.seller_shop, self.request.user)
                return self.serialize(order.seller_shop)

            # check mapped pos shop
            shop_map = ShopCustomerMap.objects.filter(user=self.request.user,
                                                      shop__online_inventory_enabled=True).last()
            if shop_map:
                create_shop_user_mapping(shop_map.shop, self.request.user)
                return self.serialize(shop_map.shop)

            return api_response('No shop found!')
        return self.shop_from_location()

    def shop_from_location(self):
        serializer = UserLocationSerializer(data=self.request.GET)
        if serializer.is_valid():
            data = serializer.data
            radius = get_config('pos_ecom_delivery_radius', 10)
            shop = nearby_shops(data['latitude'], data['longitude'], radius)
            if shop:
                create_shop_user_mapping(shop, self.request.user)
            return self.serialize(shop) if shop else api_response('No shop found!')
        else:
            return api_response(serializer_error(serializer))

    @staticmethod
    def serialize(shop):
        return api_response("", ShopSerializer(shop).data, status.HTTP_200_OK, True)


class AddressView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = AddressSerializer

    @validate_address_id
    @check_ecom_user
    def get(self, request, pk):
        address = Address.objects.filter(user=self.request.user, id=pk).last()
        if not address:
            return api_response("Invalid address id")
        serializer = self.serializer_class(address)
        return api_response('', serializer.data, status.HTTP_200_OK, True)

    @check_ecom_user
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return api_response('', serializer.data, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @validate_address_id
    @check_ecom_user
    def put(self, request, pk):
        serializer = self.serializer_class(data=request.data, context={'user': request.user, 'pk': pk})
        if serializer.is_valid():
            serializer.update(pk, serializer.data)
            serializer = self.serializer_class(Address.objects.get(user=self.request.user, id=pk))
            return api_response('', serializer.data, status.HTTP_200_OK, True)
        else:
            return api_response(serializer_error(serializer))

    @validate_address_id
    @check_ecom_user
    def delete(self, request, pk):
        Address.objects.filter(user=self.request.user, id=pk).delete()
        return api_response('Address removed successfully!', None, status.HTTP_200_OK, True)


class AddressListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user, deleted_at__isnull=True)

    @check_ecom_user
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response('', serializer.data, status.HTTP_200_OK, True)


class CategoriesView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = CategorySerializer

    @check_ecom_user_shop
    def get(self, *args, **kwargs):
        categories_to_return = []
        categories_with_products = get_categories_with_products(kwargs['shop'])
        all_active_categories = Category.objects.filter(category_parent=None, status=True, category_type='grocery')
        # print("==============================================================")
        for c in all_active_categories:
            if c.id in categories_with_products:
                categories_to_return.append(c)
            elif c.cat_parent.filter(status=True).count() > 0:
                for sub_category in c.cat_parent.filter(status=True, category_type='grocery'):
                    # print(sub_category)
                    if sub_category.id in categories_with_products:
                        categories_to_return.append(c)
                        break
        serializer = self.serializer_class(categories_to_return, many=True)
        is_success = True if categories_to_return else False
        # print("==============================================================")
        return api_response('', serializer.data, status.HTTP_200_OK, is_success)


class SuperStoreCategoriesView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = CategorySerializer

    @check_ecom_user
    def get(self, *args, **kwargs):
        active_categories = Category.objects\
            .filter(category_parent=None,
                    category_type='superstore',
                    cat_parent__status=True,
                    status=True)\
                        .prefetch_related(Prefetch('cat_parent',\
                            queryset=Category.objects.filter(status=True,
                                                            category_type='superstore').filter(category_order__gt=0).order_by('category_order'))).order_by('category_order').distinct('category_order')
        serializer = self.serializer_class(active_categories, many=True)
        is_success = True if active_categories else False
        return api_response('', serializer.data, status.HTTP_200_OK, is_success)


class SuperStoreSubCategoriesView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = SubCategorySerializer

    @check_ecom_user
    def get(self, *args, **kwargs):
        try:
            category_id = self.request.query_params.get('category_id')
            category = Category.objects.get(id=category_id)
            sub_categories = category.cat_parent.filter(status=True,
                                                        category_type='superstore') \
                .annotate(cat_order=Count('parent_category_pro_category__product',
                                          distinct=True,
                                          filter=Q(parent_category_pro_category__status=True))) \
                .order_by('-cat_order')
            is_success = True if sub_categories else False
            serializer = self.serializer_class(sub_categories, many=True)
            return api_response('', serializer.data, status.HTTP_200_OK, is_success)
        except Category.DoesNotExist:
            return api_response('Category not found.', '', status.HTTP_404_NOT_FOUND, False)


class SubCategoriesView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = SubCategorySerializer

    @check_ecom_user_shop
    def get(self, *args, **kwargs):
        categories_with_products = get_categories_with_products(kwargs['shop'])
        category = Category.objects.get(pk=self.request.GET.get('category_id'))
        # print(category.__dict__)
        sub_categories = category.cat_parent.filter(status=True,
                                                    id__in=categories_with_products,
                                                    category_type='grocery')
        serializer = self.serializer_class(sub_categories, many=True)
        is_success = True if sub_categories else False
        return api_response('', serializer.data, status.HTTP_200_OK, is_success)


class B2cCategoriesView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = B2cCategorySerializer

    @check_ecom_user_shop
    def get(self, *args, **kwargs):
        categories_to_return = []
        categories_with_products = get_b2c_categories_with_products(kwargs['shop'])
        all_active_categories = B2cCategory.objects.filter(category_parent=None, status=True)
        # print("==============================================================")
        for c in all_active_categories:
            if c.id in categories_with_products:
                categories_to_return.append(c)
            elif c.b2c_cat_parent.filter(status=True).count() > 0:
                for sub_category in c.b2c_cat_parent.filter(status=True):
                    # print(sub_category)
                    if sub_category.id in categories_with_products:
                        categories_to_return.append(c)
                        break
        serializer = self.serializer_class(categories_to_return, many=True)
        is_success = True if categories_to_return else False
        # print("==============================================================")
        return api_response('', serializer.data, status.HTTP_200_OK, is_success)


class B2cSubCategoriesView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = B2cSubCategorySerializer

    @check_ecom_user_shop
    def get(self, *args, **kwargs):
        categories_with_products = get_b2c_categories_with_products(kwargs['shop'])
        category = B2cCategory.objects.get(pk=self.request.GET.get('category_id'))
        # print(category.__dict__)
        sub_categories = category.b2c_cat_parent.filter(status=True,
                                                        id__in=categories_with_products)
        serializer = self.serializer_class(sub_categories, many=True)
        is_success = True if sub_categories else False
        return api_response('', serializer.data, status.HTTP_200_OK, is_success)


class TagView(APIView):
    """
    Get list of all tags
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @check_ecom_user
    def get(self, *args, **kwargs):
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        is_success = True
        return api_response('', serializer.data, status.HTTP_200_OK, is_success)


class TagProductView(APIView):
    """
    Get Product by tag id
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    pagination_class = SmallOffsetPagination

    @check_ecom_user_shop
    def get(self, request, pk, *args, **kwargs):
        try:
            tag = Tag.objects.get(id=pk)
        except:
            return api_response('Invalid Tag Id')
        shop = kwargs['shop']
        products = RetailerProduct.objects.filter(product_tag_ecom__tag=tag, shop=shop, is_deleted=False,
                                                  online_enabled=True).distinct()
        is_success, data = False, []
        count = products.count()
        if products.count() >= 3:
            products = self.pagination_class().paginate_queryset(products, self.request)
            serializer = TagProductSerializer(tag, context={'product': products})
            # serializer = RetailerProductSerializer(products, many=True)
            is_success, data = True, serializer.data

        if count >= 10:
            url = request.get_full_path().split('?')[0]+f'?limit=50&offset=0'
            data.update({'total_items': count, 'view_more': url})
        return api_response('Tag Found', data, status.HTTP_200_OK, is_success)


class UserShopView(APIView):
    """
    Get the list of shop user is mapped to
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def get(self, request, format=None):
        user = request.user
        # shop_customer_mapping = ShopCustomerMap.objects.filter(user=user)
        # shop = Shop.objects.filter(registered_shop__in=shop_customer_mapping)
        is_success, data, message = False, [], "No shop found"
        orders = Order.objects.filter(buyer=user, ordered_cart__cart_type__in=['BASIC', 'ECOM'],
                                      seller_shop__online_inventory_enabled=True)
        shop = []
        for order in orders:
            if order.seller_shop not in shop:
                shop.append(order.seller_shop)
        data = ShopInfoSerializer(shop, many=True).data
        if data:
            is_success, message = True, "Shop Found"
        return api_response(message, data, status.HTTP_200_OK, is_success)

    def post(self, request, *args, **kwargs):
        if not self.request.GET.get('shop_id'):
            return api_response("please provide shop", "", status.HTTP_406_NOT_ACCEPTABLE, False)
        shop_id = self.request.GET.get('shop_id')
        try:
            shop = Shop.objects.get(id=int(shop_id))
        except:
            info_logger.error(f"shop not found for shop id {shop_id}")
            return api_response("Invalid shop has been selected", "", status.HTTP_406_NOT_ACCEPTABLE, False)
        create_shop_user_mapping(shop, self.request.user)
        return api_response("New shop mapped successfully.", "", status.HTTP_200_OK, True)


class Contect_Us(APIView):
    authentication_classes = (TokenAuthentication,)

    def get(self, request, format=None):
        phone_no = "999-010-5700"
        obj = GlobalConfig.objects.filter(key='contect_us_ecom_phone').last()
        if obj:
            phone_no = obj.value
        email = "care@peppertap.in"
        obj = GlobalConfig.objects.filter(key='contect_us_ecom_email').last()
        if obj:
            email = obj.value

        data = {'phone_number': phone_no, 'email': email}
        serializer = ContectUs(data=data)
        if serializer.is_valid():
            return api_response('contct us details', serializer.data, status.HTTP_200_OK, True)


class ParentProductDetails(APIView):
    """
    retailer product details with parent product discriptions .....
    """

    authentication_classes = (TokenAuthentication,)
    serializer_class = Parent_Product_Serilizer

    @check_ecom_user_shop
    def get(self, request, pk, *args, **kwargs):
        '''get retailer product details ....'''
        shop = kwargs['shop']
        serializer = RetailerProduct.objects.filter(id=pk, shop=shop, is_deleted=False, online_enabled=True)
        serializer = self.serializer_class(serializer, many=True)
        return api_response('products information', serializer.data, status.HTTP_200_OK, True)


class PastPurchasedProducts(APIView):
    """
    API to get the products purchased by a user
    """

    authentication_classes = (TokenAuthentication,)
    serializer_class = PastPurchasedProductSerializer
    pagination_class = SmallOffsetPagination

    @check_ecom_user_shop
    def get(self, request, *args, **kwargs):
        '''
        Get retailer products purchase by a user for specific shop
        '''
        shop = kwargs['shop']
        products = RetailerProduct.objects.filter(products_sold__user=request.user, products_sold__shop=shop,
                                                  is_deleted=False, online_enabled=True, ).order_by(
            '-products_sold__id')
        count = products.count()
        products = self.pagination_class().paginate_queryset(products, self.request)
        serializer = RetailerProductSerializer(products, many=True)
        is_success, data, msg = True, serializer.data, f"{count} record/s found"
        if count >10:
            view_more = request.get_full_path().split('?')[0]
            view_more += '?offset=0&limit=100'
            data.append({'total': count, 'vew_more': view_more})
        return api_response(msg, data, status.HTTP_200_OK, is_success)


class ProductFunctionView(APIView):
    """
    Get Product by tag id
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    pagination_class = SmallOffsetPagination

    @check_ecom_user_shop
    def get(self, request, pk, *args, **kwargs):
        try:
            tag = Tag.objects.get(id=pk)
        except:
            return api_response('Invalid Tag Id')
        shop = kwargs['shop']
        products = RetailerProduct.objects.filter(product_tag_ecom__tag=tag, shop=shop, is_deleted=False,
                                                  online_enabled=True)
        is_success, data = False, []
        counts = products.count()
        if products.count() >= 3:
            view_more = None
            if products.count() > 10:
                view_more = request.get_full_path().split("?")[0]
                view_more += '?offset=0&limit=100'
            products = self.pagination_class().paginate_queryset(products, self.request)
            # serializer = TagProductSerializer(tag, context={'product': products})
            serializer = RetailerProductSerializer(products, many=True)
            is_success, data = True, serializer.data
            if view_more:
                data.append({'total': counts, 'view_more': view_more})

        return api_response('Tag Found', data, status.HTTP_200_OK, is_success)


class CustomProductFunctionView(APIView):
    """
    Get Product by identifier and not stored in tag table
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    pagination_class = SmallOffsetPagination

    @check_ecom_user_shop
    def get(self, request, identifier, *args, **kwargs):
        shop = kwargs['shop']
        if identifier == "private_label":
            private_label_parent_brand = ['Navshree', 'Gramfactory']
            products = RetailerProduct.objects.filter(
                shop=shop, is_deleted=False,
                online_enabled=True,
                linked_product__parent_product__parent_brand__brand_parent__brand_name__in=private_label_parent_brand, )
            is_success, data = False, []
            if products.count() >= 3:
                products = self.pagination_class().paginate_queryset(products, self.request)
                serializer = RetailerProductSerializer(products, many=True)
                is_success, data = True, serializer.data
            return api_response('Product Found', data, status.HTTP_200_OK, is_success)
        else:
            return api_response('invalid identifier')
