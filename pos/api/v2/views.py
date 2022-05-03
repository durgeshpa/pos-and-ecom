from django.db.models import Q, Sum, F
from retailer_backend.utils import SmallOffsetPagination
from rest_framework import authentication
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
from pos.common_functions import  serializer_error
logger = logging.getLogger('pos-api-v2')

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

"""
@Durgesh patel
"""

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
def create_or_update(id,data):
    data_list = data
    for key in data_list.keys():
        key_name = FOFOConfigSubCategory.objects.get(name=key)
        instance, created = FOFOConfigurations.objects.update_or_create(
            shop=id, key_id=key_name.id, defaults={"value":data[key_name.name]})
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
    permission_classes = (AllowAny,)
    queryset = FOFOConfigSubCategory.objects.all()
    serializer_class = ShopRewardConfigKeySerilizer
    def put(self, request):
        """bulk update shop reward configration .."""
        data = request.data
        queryset = Shop.objects.filter(id__in=data.get('shop_id'))
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
