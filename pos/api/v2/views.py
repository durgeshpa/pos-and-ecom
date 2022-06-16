from django.db.models import Q, Sum, F
from retailer_backend.utils import SmallOffsetPagination
from rest_auth import authentication
from rest_framework.permissions import AllowAny
from shops.models import Shop, FOFOConfigurations, FOFOConfigSubCategory
from django.http import HttpResponse
from products.common_function import get_response, serializer_error
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, UpdateAPIView, CreateAPIView
from .serializers import (ShopOwnerNameListSerializer, ShopNameListSerializer,
                            ShopTypeListSerializers, RewardConfigShopSerializers,
                            RewardConfigListShopSerializers, ShopRewardConfigKeySerilizer)
from .services import shop_owner_search, shop_name_search, shop_type_search, shop_search, shop_reward_config_key_search
import logging
from shops.common_validators import validate_shop_owner_id, ShopType
from pos.models import (
                        PosStoreRewardMappings)
from pos.common_functions import  serializer_error, RetailerProductCls, OffersCls
logger = logging.getLogger('pos-api-v2')

from pos.api.v1.serializers import ( CouponOfferSerializer, FreeProductOfferSerializer,
                          ComboOfferSerializer, CouponOfferUpdateSerializer, ComboOfferUpdateSerializer,
                          CouponListSerializer, FreeProductOfferUpdateSerializer, OfferCreateSerializer,
                          OfferUpdateSerializer, CouponGetSerializer, OfferGetSerializer, 
                          )
from rest_framework import permissions
from pos.models import RetailerProduct
from coupon.models import CouponRuleSet, RuleSetProductMapping, DiscountValue, Coupon
from pos.common_functions import api_response
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework import status
# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

"""
@Durgesh patel
"""

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


def validate_id(self, id):
    """ validation only ids that belong to a selected related model """
    if not self.queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    self.queryset = self.queryset.filter(id=id)

def validate_shop__id(queryset, id):
    """ validation only shop_ id that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid shop id'}
    return {'data': queryset.filter(id=id)}


class ShopOwnerNameListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShopOwnerNameListSerializer
    queryset = Shop.objects.filter(Q(shop_type__shop_sub_type__retailer_type_name__in=["foco", "fofo"])) \
        .only('shop_owner__id').distinct('shop_owner__id')

    def get(self, request):
        """ GET API for ShopOwnerNameList """
        info_logger.info("ShopOwnerNameList GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_shop_owner_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop List """
            search_text = self.request.GET.get('search_text')
            if search_text:
                self.queryset = shop_owner_search(self.queryset, search_text)
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shops_data, many=True)
        msg = ""
        return get_response(msg, serializer.data, True)


class ShopNameListView(GenericAPIView):
    """SHOP ShopNameListView .."""
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShopNameListSerializer
    queryset = Shop.objects.filter(Q(shop_type__shop_sub_type__retailer_type_name__in=["foco", "fofo"])) \
        .only('id').distinct('id')

    def get(self, request):
        """ GET API for ShopNameList """
        info_logger.info("ShopNameList GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_shop__id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop List """
            search_text = self.request.GET.get('search_text')
            if search_text:
                self.queryset = shop_name_search(self.queryset, search_text)
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shops_data, many=True)
        msg = ""
        return get_response(msg, serializer.data, True)


class ShopTypeListView(GenericAPIView):
    """SHOP Type .."""
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ShopType.objects.filter(Q(shop_sub_type__retailer_type_name__in=["foco", "fofo"]))
    serializer_class = ShopTypeListSerializers

    def get(self, request):
        """ GET Shop Type List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_type_search(self.queryset, search_text)
        shop_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop_type, many=True)
        msg = "" if shop_type else "no shop found"
        return get_response(msg, serializer.data, True)

class RewardConfigShopListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = PosStoreRewardMappings.objects.filter(Q(shop_type__shop_sub_type__retailer_type_name__in=["foco", "fofo"])).order_by('-id')
    serializer_class = RewardConfigListShopSerializers # ShopCrudSerializers

    def get(self, request):
        """ GET API for RewardConfig """
        info_logger.info("RewardConfig GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            error = validate_id(
                self, int(request.GET.get('id')))
            if error:
                return get_response(error['error'])
            shops_data = self.queryset
        else:
            """ GET Shop List """
            self.queryset = self.search_filter_shops_data()
            shop_total_count = self.queryset.count()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        shop_total_count = self.queryset.count()
        serializer = self.serializer_class(shops_data, many=True)
        msg = f"total count {shop_total_count}" if shops_data else "no shop found"
        return get_response(msg, serializer.data, True)
    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        shop_type = self.request.GET.get('shop_type')
        shop_owner = self.request.GET.get('shop_owner')
        pin_code = self.request.GET.get('pin_code')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')
        shop = self.request.GET.get('shop_id')
        '''search using shop_name and parent_shop based on criteria that matches'''
        if search_text:
            self.queryset = self.queryset.filter(Q(shop_name__icontains=search_text) |
                               Q(retiler_mapping__parent__shop_name__icontains=search_text))

        '''Filters using shop_type, shop_owner, pin_code, city, status, approval_status'''
        if shop:
            self.queryset = self.queryset.filter(id=shop)
        if shop_type:
            self.queryset = self.queryset.filter(shop_type__id=shop_type)

        if shop_owner:
            self.queryset = self.queryset.filter(shop_owner__id=shop_owner)

        if pin_code:
            self.queryset = self.queryset.filter(shop_name_address_mapping__pincode_link__id=pin_code)

        if city:
            self.queryset = self.queryset.filter(shop_name_address_mapping__city__id=city)

        if status:
            self.queryset = self.queryset.filter(status=status)

        return self.queryset.distinct('id')
def create_or_update(id,data):
    data_list = data
    for key in data_list.keys():
        reward_configration_key = FOFOConfigSubCategory.objects.get(name=key)
        instance, created = FOFOConfigurations.objects.update_or_create(
            shop=id, key_id=reward_configration_key.id, defaults={"value":data[reward_configration_key.name]})
        instance.save()

class RewardConfigShopCrudView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = PosStoreRewardMappings.objects.filter(Q(shop_type__shop_sub_type__retailer_type_name__in=["foco", "fofo"])).order_by('-id')
    serializer_class = RewardConfigShopSerializers # ShopCrudSerializers

    def get(self, request):
        """ GET API for RewardConfig """
        info_logger.info("RewardConfig GET api called.")
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            error = validate_id(
                self, int(request.GET.get('id')))
            if error:
                return get_response(error['error'])
            shops_data = self.queryset
        else:
            """ GET Shop List """
            self.queryset = self.search_filter_shops_data()
            shop_total_count = self.queryset.count()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        shop_total_count = self.queryset.count()

        serializer = self.serializer_class(shops_data, many=True)
        msg = f"total count {shop_total_count}" if shops_data else "no shop found"
        return get_response(msg, serializer.data, True)


    def put(self, request):
        """ PUT API for Shop Updation with Image """

        info_logger.info("RewardConfig PUT api called.")
        modified_data = request.data

        if 'id' not in modified_data:
            return get_response('please provide id to update RewardConfig', False)

        # validations for input id
        error = validate_id(self, int(modified_data['id']))
        if error:
            return get_response(error)
        shop_instance = self.queryset.last()
        data = modified_data.get('shop_config')
        serializer = self.serializer_class(instance=shop_instance, data=modified_data, context={'request':request})
        if serializer.is_valid():
            try:
                create_or_update(shop_instance, data)
            except Exception as e:
                return get_response(str(e), False)
            serializer.save()
            #create_or_update(modified_data['id'], data)
            info_logger.info("RewardConfig Updated Successfully.")
            return get_response('RewardConfig Updated Successfully.', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Shop with image """

        info_logger.info("Shop DELETE api called.")
        if not request.data.get('shop_id'):
            return get_response('please provide shop_id', False)
        try:
            for s_id in request.data.get('shop_id'):
                shop_id = self.queryset.get(id=int(s_id))
                try:
                    shop_id.delete()
                except:
                    return get_response(f'can not delete shop | {shop_id.shop_name} | getting used', False)
        except Exception as e:
            error_logger.error(e)
            return get_response(f'please provide a valid shop id {s_id}', False)
        return get_response('shop were deleted successfully!', True)

    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        shop_type = self.request.GET.get('shop_type')
        shop_owner = self.request.GET.get('shop_owner')
        pin_code = self.request.GET.get('pin_code')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')
        shop = self.request.GET.get('shop_id')
        '''search using shop_name and parent_shop based on criteria that matches'''
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)

        '''Filters using shop_type, shop_owner, pin_code, city, status, approval_status'''
        if shop:
            self.queryset = self.queryset.filter(id=shop)
        if shop_type:
            self.queryset = self.queryset.filter(shop_type__id=shop_type)

        if shop_owner:
            self.queryset = self.queryset.filter(shop_owner__id=shop_owner)

        if pin_code:
            self.queryset = self.queryset.filter(shop_name_address_mapping__pincode_link__id=pin_code)

        if city:
            self.queryset = self.queryset.filter(shop_name_address_mapping__city__id=city)

        if status:
            self.queryset = self.queryset.filter(status=status)

        return self.queryset.distinct('id')

class ShopRewardConfigKeys(GenericAPIView):
    """SHOP Type .."""
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = FOFOConfigSubCategory.objects.all()
    serializer_class = ShopRewardConfigKeySerilizer

    def get(self, request):
        """ GET Shop Type List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_reward_config_key_search(self.queryset, search_text)
        shop_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop_type, many=True)
        msg = "" if shop_type else "no shop found"
        return get_response(msg, serializer.data, True)

class BulkUpdate(GenericAPIView):
    """Bulk update reward configartions """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = FOFOConfigSubCategory.objects.all()
    serializer_class = ShopRewardConfigKeySerilizer
    def put(self, request):
        """bulk update shop reward configration .."""
        data = request.data
        queryset = Shop.objects.filter(id__in=data.get('id'))
        for obj in queryset:
            try:
                create_or_update(obj, data.get('shop_config'))
                obj.enable_loyalty_points = data.get('enable_loyalty_points', obj.enable_loyalty_points)
                obj.updated_by=request.user
                obj.save()
            except Exception as e:
                error_logger.error(e)
                return get_response(str(e), False)
        return get_response("updated successfully", "", True)


class AdminOffers(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SmallOffsetPagination


    def get(self, request, *args, **kwargs):
        """
            Get Offer / Offers List
        """
        id = request.GET.get('id')
        if id:
            serializer = OfferGetSerializer(data={'id': id})
            if serializer.is_valid():
                return self.get_offer(id)
            else:
                return api_response(serializer_error(serializer))
        else:
            return self.get_offers_list(request,None)


    def post(self, request, *args, **kwargs):
        """
            Create Any Offer
        """
        shop_name = request.data.get('shop_name')
        shop = None
        if shop_name:
            shop = Shop.objects.filter(shop_name=shop_name).last()
        elif request.data.get('shop_id'):
            shop = Shop.objects.get(id=shop_name)

        if not shop:
            raise serializers.ValidationError("Shop name or id is mendotry")

        serializer = OfferCreateSerializer(data=request.data)
        if serializer.is_valid():
            return self.create_offer(serializer.data, shop.id)
        else:
            return api_response(serializer_error(serializer))


    def put(self, request, *args, **kwargs):
        """
           Update Any Offer
        """
        shop_name = request.data.get('shop_name')
        shop = None
        if shop_name:
            shop = Shop.objects.filter(shop_name=shop_name).last()
        elif request.data.get('shop_id'):
            shop = Shop.objects.get(id=shop_name)

        if not shop:
            raise serializers.ValidationError("Shop name or id is mendotry")
        data = request.data
        data['shop_id'] = shop.id
        serializer = OfferUpdateSerializer(data=data)
        if serializer.is_valid():
            return self.update_offer(serializer.data, shop.id)
        else:
            return api_response(serializer_error(serializer))

    def create_offer(self, data, shop_id):
        offer_type = data['offer_type']
        
        serializer_class = OFFER_SERIALIZERS_MAP[data['offer_type']]
        serializer = serializer_class(data=self.request.data)
        if serializer.is_valid():
            with transaction.atomic():
                data.update(serializer.data)
                if offer_type == 1:
                    return self.create_coupon(data, shop_id)
                elif offer_type == 2:
                    return self.create_combo_offer(data, shop_id)
                else:
                    return self.create_free_product_offer(data, shop_id)
        else:
            return api_response(serializer_error(serializer))

    def update_offer(self, data, shop_id):
        offer_type = data['offer_type']
        serializer_class = OFFER_UPDATE_SERIALIZERS_MAP[data['offer_type']]
        serializer = serializer_class(data=self.request.data)
        if serializer.is_valid():
            with transaction.atomic():
                data.update(serializer.data)
                success_msg = 'Offer has been updated successfully!'
                if 'coupon_name' not in data and 'is_active' in data:
                    success_msg = 'Offer has been activated successfully!' if data[
                        'is_active'] else 'Offer has been deactivated successfully!'
                if offer_type == 1:
                    return self.update_coupon(data, shop_id, success_msg)
                elif offer_type == 2:
                    return self.update_combo(data, shop_id, success_msg)
                else:
                    return self.update_free_product_offer(data, shop_id, success_msg)
        else:
            return api_response(serializer_error(serializer))

    @staticmethod
    def get_offer(coupon_id):
        coupon = CouponGetSerializer(Coupon.objects.get(id=coupon_id)).data
        coupon.update(coupon['details'])
        coupon.pop('details')
        return api_response("Offers", coupon, status.HTTP_200_OK, True)

    def get_offers_list(self, request, shop_id):
        """
          Get Offers List
       """
        if shop_id:
            coupon = Coupon.objects.select_related('rule').filter(shop=shop_id)
        else:
            coupon = Coupon.objects.select_related('rule').all()
        if request.GET.get('search_text'):
            coupon = coupon.filter(coupon_name__icontains=request.GET.get('search_text'))
        coupon = coupon.order_by('-updated_at')
        objects = self.pagination_class().paginate_queryset(coupon, self.request)
        data = CouponListSerializer(objects, many=True).data
        for coupon in data:
            coupon.update(coupon['details'])
            coupon.pop('details')
        return api_response("Offers List", data, status.HTTP_200_OK, True)

    @staticmethod
    def create_coupon(data, shop_id):
        """
            Discount on order
        """
        shop = Shop.objects.filter(id=shop_id).last()
        start_date, expiry_date, discount_value, discount_amount = data['start_date'], data['end_date'], data[
            'discount_value'], data['order_value']
        discount_value_str = str(discount_value).rstrip('0').rstrip('.')
        discount_amount_str = str(discount_amount).rstrip('0').rstrip('.')
        if data['is_percentage']:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value,
                                                        max_discount=data['max_discount'], is_percentage=True)
            if discount_obj.max_discount and float(discount_obj.max_discount) > 0:
                max_discount_str = str(discount_obj.max_discount).rstrip('0').rstrip('.')
                coupon_code = discount_value_str + "% off upto ₹" + max_discount_str + " on orders above ₹" + discount_amount_str
            else:
                coupon_code = discount_value_str + "% off on orders above ₹" + discount_amount_str
            rule_set_name_with_shop_id = str(shop_id) + "_" + coupon_code
        elif data['is_point']:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value,
                                                        max_discount=data['max_discount'], is_percentage=False, is_point=True)
            coupon_code = "get " + discount_value_str + " points on orders above ₹" + discount_amount_str
            rule_set_name_with_shop_id = str(shop_id) + "_" + coupon_code
        else:
            discount_obj = DiscountValue.objects.create(discount_value=discount_value, is_percentage=False)
            coupon_code = "₹" + discount_value_str + " off on orders above ₹" + discount_amount_str
            rule_set_name_with_shop_id = str(shop_id) + "_" + coupon_code

        coupon_obj = OffersCls.rule_set_creation(rule_set_name_with_shop_id, start_date, expiry_date, discount_amount,
                                                 discount_obj)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)
        else:
            coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', data['coupon_name'], coupon_code, shop,
                                                     start_date, expiry_date, data.get('limit_of_usages_per_customer', None))
            data['id'] = coupon.id
            coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get('coupon_enable_on') else 'all'
            coupon.coupon_shop_type = data.get('coupon_shop_type') if data.get('coupon_shop_type') else coupon.coupon_shop_type
            data['coupon_enable_on'] = coupon.coupon_enable_on
            data['coupon_shop_type'] = coupon.coupon_shop_type

            coupon.save()
            return api_response("Coupon Offer has been created successfully!", data, status.HTTP_200_OK, True)

    @staticmethod
    def create_combo_offer(data, shop_id):
        """
            Buy X Get Y Free
        """
        shop = Shop.objects.filter(id=shop_id).last()
        retailer_primary_product = data['primary_product_id']
        try:
            retailer_primary_product_obj = RetailerProduct.objects.get(~Q(sku_type=4), id=retailer_primary_product,
                                                                       shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Primary product not found")
        retailer_free_product = data['free_product_id']
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=retailer_free_product, shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Free product not found")

        combo_offer_name, start_date, expiry_date, purchased_product_qty, free_product_qty = data['coupon_name'], data[
            'start_date'], data['end_date'], data['primary_product_qty'], data['free_product_qty']
        offer = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                     retailer_primary_product=retailer_primary_product_obj,
                                                     rule__coupon_ruleset__is_active=True)
        if offer:
            return api_response("Offer already exists for this Primary Product")

        offer = RuleSetProductMapping.objects.filter(rule__coupon_ruleset__shop__id=shop_id,
                                                     retailer_primary_product=retailer_free_product_obj,
                                                     rule__coupon_ruleset__is_active=True)

        if offer and offer[0].retailer_free_product.id == data['primary_product_id']:
            return api_response("Offer already exists for this Primary Product as a free product for same free product")

        combo_code = f"Buy {purchased_product_qty} {retailer_primary_product_obj.name}" \
                     f" + Get {free_product_qty} {retailer_free_product_obj.name} Free"
        combo_rule_name = str(shop_id) + "_" + combo_code
        coupon_obj = OffersCls.rule_set_creation(combo_rule_name, start_date, expiry_date)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)

        OffersCls.rule_set_product_mapping(coupon_obj.id, retailer_primary_product_obj, purchased_product_qty,
                                           retailer_free_product_obj, free_product_qty, combo_offer_name, start_date,
                                           expiry_date)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'catalog', combo_offer_name, combo_code, shop,
                                                 start_date, expiry_date, data.get('limit_of_usages_per_customer',None))
        coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get('coupon_enable_on') else 'all'
        coupon.coupon_shop_type = data.get('coupon_shop_type') if data.get(
            'coupon_shop_type') else coupon.coupon_shop_type
        data['coupon_enable_on'] = coupon.coupon_enable_on
        data['coupon_shop_type'] = coupon.coupon_shop_type
        coupon.save()
        data['id'] = coupon.id
        return api_response("Combo Offer has been created successfully!", data, status.HTTP_200_OK, True)

    @staticmethod
    def create_free_product_offer(data, shop_id):
        """
            Cart Free Product
        """
        shop, free_product = Shop.objects.filter(id=shop_id).last(), data['free_product_id']
        try:
            retailer_free_product_obj = RetailerProduct.objects.get(id=free_product, shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Free product not found")

        coupon_name, discount_amount, start_date, expiry_date, free_product_qty = data['coupon_name'], data[
            'order_value'], data['start_date'], data['end_date'], data['free_product_qty']
        coupon_rule_discount_amount = Coupon.objects.filter(rule__cart_qualifying_min_sku_value=discount_amount,
                                                            shop=shop_id, rule__coupon_ruleset__is_active=True)
        if coupon_rule_discount_amount:
            return api_response(f"Offer already exists for Order Value {discount_amount}")

        coupon_rule_product_qty = Coupon.objects.filter(rule__free_product=retailer_free_product_obj,
                                                        rule__free_product_qty=free_product_qty,
                                                        shop=shop_id, rule__coupon_ruleset__is_active=True)
        if coupon_rule_product_qty:
            return api_response("Offer already exists for same quantity of free product")

        discount_amount_str = str(discount_amount).rstrip('0').rstrip('.')
        coupon_code = str(free_product_qty) + " " + str(
            retailer_free_product_obj.name) + " free on orders above ₹" + discount_amount_str
        rule_name = str(shop_id) + "_" + coupon_code
        coupon_obj = OffersCls.rule_set_creation(rule_name, start_date, expiry_date, discount_amount, None,
                                                 retailer_free_product_obj, free_product_qty)
        if type(coupon_obj) == str:
            return api_response(coupon_obj)
        coupon = OffersCls.rule_set_cart_mapping(coupon_obj.id, 'cart', coupon_name, coupon_code, shop, start_date,
                                                 expiry_date, data.get('limit_of_usages_per_customer',None))
        coupon.coupon_enable_on = data.get('coupon_enable_on') if data.get('coupon_enable_on') else 'all'
        coupon.coupon_shop_type = data.get('coupon_shop_type') if data.get(
            'coupon_shop_type') else coupon.coupon_shop_type
        data['coupon_enable_on'] = coupon.coupon_enable_on
        data['coupon_shop_type'] = coupon.coupon_shop_type
        coupon.save()
        data['id'] = coupon.id
        return api_response("Free Product Offer has been created successfully!", data, status.HTTP_200_OK, True)

    @staticmethod
    def update_coupon(data, shop_id, success_msg):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Coupon Id Invalid")
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            error_logger.error("Coupon RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Coupon RuleSet not found")

        coupon.coupon_name = data['coupon_name'] if 'coupon_name' in data else coupon.coupon_name
        if 'start_date' in data:
            rule.start_date = coupon.start_date = data['start_date']
        if 'end_date' in data:
            rule.expiry_date = coupon.expiry_date = data['end_date']
        if 'is_active' in data:
            rule.is_active = coupon.is_active = data['is_active']
        rule.save()
        coupon.limit_of_usages_per_customer = data.get('limit_of_usages_per_customer',coupon.limit_of_usages_per_customer)
        coupon.coupon_enable_on = data.get('coupon_enable_on', coupon.coupon_enable_on)
        coupon.coupon_shop_type = data.get('coupon_shop_type', coupon.coupon_shop_type )
        coupon.save()
        return api_response(success_msg, None, status.HTTP_200_OK, True)

    @staticmethod
    def update_combo(data, shop_id, success_msg):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Coupon Id Invalid")
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            error_logger.error("Coupon RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Coupon RuleSet not found")
        try:
            rule_set_product_mapping = RuleSetProductMapping.objects.get(rule=coupon.rule)
        except ObjectDoesNotExist:
            error_logger.error("Product RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Product mapping Not Found with Offer")

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
        coupon.limit_of_usages_per_customer = data.get('limit_of_usages_per_customer',coupon.limit_of_usages_per_customer)
        coupon.coupon_enable_on = data.get('coupon_enable_on', coupon.coupon_enable_on)
        coupon.coupon_shop_type = data.get('coupon_shop_type', coupon.coupon_shop_type )
        coupon.save()
        return api_response(success_msg, None, status.HTTP_200_OK, True)

    @staticmethod
    def update_free_product_offer(data, shop_id, success_msg):
        try:
            coupon = Coupon.objects.get(id=data['id'], shop=shop_id)
        except ObjectDoesNotExist:
            return api_response("Coupon Id Invalid")
        try:
            rule = CouponRuleSet.objects.get(id=coupon.rule.id)
        except ObjectDoesNotExist:
            error_logger.error("Coupon RuleSet not found for coupon id {}".format(coupon.id))
            return api_response("Coupon RuleSet not found")

        coupon.coupon_name = data['coupon_name'] if 'coupon_name' in data else coupon.coupon_name
        if 'start_date' in data:
            rule.start_date = coupon.start_date = data['start_date']
        if 'expiry_date' in data:
            rule.expiry_date = coupon.expiry_date = data['end_date']
        if 'is_active' in data:
            rule.is_active = coupon.is_active = data['is_active']
        rule.save()
        coupon.limit_of_usages_per_customer = data.get('limit_of_usages_per_customer',coupon.limit_of_usages_per_customer)
        coupon.coupon_enable_on = data.get('coupon_enable_on', coupon.coupon_enable_on)
        coupon.coupon_shop_type = data.get('coupon_shop_type', coupon.coupon_shop_type )
        coupon.save()
        return api_response(success_msg, None, status.HTTP_200_OK, True)

