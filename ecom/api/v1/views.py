from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import ListAPIView
from rest_framework import status

from categories.models import Category
from marketing.models import RewardPoint
from shops.models import Shop
from pos.common_functions import serializer_error, api_response
from pos.models import RetailerProduct
from retailer_backend.utils import SmallOffsetPagination
from retailer_to_sp.models import Order
from pos.models import ShopCustomerMap
from global_config.views import get_config

from ecom.utils import (check_ecom_user, nearby_shops, validate_address_id, check_ecom_user_shop,
                        get_categories_with_products)
from ecom.models import Address, Tag
from .serializers import (AccountSerializer, RewardsSerializer, TagSerializer, UserLocationSerializer, ShopSerializer,
                          AddressSerializer, CategorySerializer, SubCategorySerializer, TagProductSerializer, Parent_Product_Serilizer,
                          ShopInfoSerializer)

from pos.api.v1.serializers import ContectUs

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
    def get(self, request, *args, **kwargs):
        """
        All Reward Credited/Used Details For User
        """
        serializer = self.serializer_class(
            RewardPoint.objects.filter(reward_user=self.request.user).select_related('reward_user').last())
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
                return self.serialize(order.seller_shop)

            # check mapped pos shop
            shop_map = ShopCustomerMap.objects.filter(user=self.request.user,
                                                      shop__online_inventory_enabled=True).last()
            if shop_map:
                return self.serialize(shop_map.shop)

            return api_response('No shop found!')
        return self.shop_from_location()

    def shop_from_location(self):
        serializer = UserLocationSerializer(data=self.request.GET)
        if serializer.is_valid():
            data = serializer.data
            radius = get_config('pos_ecom_delivery_radius', 10)
            shop = nearby_shops(data['latitude'], data['longitude'], radius)
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
        all_active_categories = Category.objects.filter(category_parent=None, status=True, b2c_status=True)
        # print("==============================================================")
        for c in all_active_categories:
            if c.id in categories_with_products:
                categories_to_return.append(c)
            elif c.cat_parent.filter(status=True).count() > 0:
                for sub_category in c.cat_parent.filter(status=True, b2c_status=True):
                    # print(sub_category)
                    if sub_category.id in categories_with_products:
                        categories_to_return.append(c)
                        break
        serializer = self.serializer_class(categories_to_return, many=True)
        is_success = True if categories_to_return else False
        # print("==============================================================")
        return api_response('', serializer.data, status.HTTP_200_OK, is_success)


class SubCategoriesView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = SubCategorySerializer

    @check_ecom_user_shop
    def get(self, *args, **kwargs):
        categories_with_products = get_categories_with_products(kwargs['shop'])
        category = Category.objects.get(pk=self.request.GET.get('category_id'))
        # print(category.__dict__)
        sub_categories = category.cat_parent.filter(status=True, b2c_status=True, id__in=categories_with_products)
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
        products = RetailerProduct.objects.filter(product_tag_ecom__tag=tag, shop=shop, is_deleted=False, online_enabled=True)
        is_success, data = False, []
        if products.count() >= 3:
            products = self.pagination_class().paginate_queryset(products, self.request)
            serializer = TagProductSerializer(tag, context={'product': products})
            is_success, data = True, serializer.data
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

class Contect_Us(APIView):
    authentication_classes = (TokenAuthentication,)
    def get(self, request, format=None):
        data = {'phone_number':"7777777777",'email' :'papertap@gmail.com'}
        serializer = ContectUs(data=data)
        if serializer.is_valid():
            return api_response('contct us details',serializer.data,status.HTTP_200_OK, True)

class ParentProductDetails(APIView):
    authentication_classes = (TokenAuthentication,)
    serializer_class = Parent_Product_Serilizer
    @check_ecom_user_shop
    def get(self, request, pk, *args, **kwargs):
        shop = kwargs['shop']
        serializer = RetailerProduct.objects.filter(id=pk, shop=shop, is_deleted=False, online_enabled=True)
        serializer = self.serializer_class(serializer, many=True)
        return api_response('products information',serializer.data,status.HTTP_200_OK, True)
