import logging
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import authentication
from rest_framework import generics
from django.contrib.auth import get_user, get_user_model
from retailer_backend.messages import SUCCESS_MESSAGES, VALIDATION_ERROR_MESSAGES, ERROR_MESSAGES
from rest_framework.permissions import AllowAny
from retailer_backend.utils import SmallOffsetPagination

from .serializers import (
    AddressSerializer, CityAddressSerializer, PinCodeAddressSerializer, ShopTypeSerializers, ShopCrudSerializers, ShopTypeListSerializers,
    ShopOwnerNameListSerializer, StateAddressSerializer, UserSerializers
)

from addresses.models import Address
from shops.models import (
    ShopType, Shop
)
from shops.common_functions import *
from shops.services import (
    shop_search, fetch_by_id, get_distinct_pin_codes, get_distinct_cities, get_distinct_states
)
from shops.common_validators import (
    validate_data_format, validate_id, validate_shop_owner_id, validate_state_id, validate_city_id, validate_pin_code
)

User = get_user_model()

logger = logging.getLogger('shop-api-v2')

'''
@author Kamal Agarwal
'''


class ShopTypeListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ShopType.objects.all()
    serializer_class = ShopTypeListSerializers

    def get(self, request):
        """ GET Shop Type List """
        shop_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop_type, many=True)
        msg = "" if shop_type else "no shop found"
        return get_response(msg, serializer.data, True)


class ShopTypeDetailView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ShopType.objects.all()
    serializer_class = ShopTypeSerializers

    def get(self, request):
        """ GET Shop Type List """
        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shop_type_id = self.request.GET.get('id')
            if shop_type_id:
                self.queryset = fetch_by_id(self.queryset, shop_type_id)
        shop_type = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shop_type, many=True)
        msg = "" if shop_type else "no shop found"
        return get_response(msg, serializer.data, True)


class ApprovalStatusListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ApprovalStatusList """
        info_logger.info("ApprovalStatusList GET api called.")
        fields = ['id', 'status']
        data = [dict(zip(fields, d)) for d in Shop.APPROVAL_STATUS_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ShopDocumentTypeListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ShopDocumentList """
        info_logger.info("ShopDocumentList GET api called.")
        fields = ['id', 'status']
        data = [dict(zip(fields, d))
                for d in ShopDocument.SHOP_DOCUMENTS_TYPE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ShopInvoiceStatusListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        """ GET API for ShopInvoiceStatusList """
        info_logger.info("ShopInvoiceStatusList GET api called.")
        fields = ['id', 'status']
        data = [dict(zip(fields, d))
                for d in ShopInvoicePattern.SHOP_INVOICE_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ShopOwnerNameListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ShopOwnerNameListSerializer
    queryset = Shop.objects.only('shop_owner__id').distinct('shop_owner__id')

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
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shops_data, many=True)
        msg = ""
        return get_response(msg, serializer.data, True)


class AddressListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    add_serializer_class = AddressSerializer
    pincode_serializer_class = PinCodeAddressSerializer
    city_serializer_class = CityAddressSerializer
    state_serializer_class = StateAddressSerializer

    queryset = Address.objects.all()

    def get(self, request):
        """ GET API for Address """
        info_logger.info("Address GET api called.")

        if request.GET.get('pin_code'):
            """ Get Address for specific Pin Code """
            id_validation = validate_pin_code(
                self.queryset, int(request.GET.get('pin_code')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            self.queryset = id_validation['data']

        if request.GET.get('city_id'):
            """ Get Address for specific City ID """
            id_validation = validate_city_id(
                self.queryset, int(request.GET.get('city_id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            self.queryset = id_validation['data']

        if request.GET.get('state_id'):
            """ Get Address for specific State ID """
            id_validation = validate_state_id(
                self.queryset, int(request.GET.get('state_id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            self.queryset = id_validation['data']

        address_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        pin_code_list = get_distinct_pin_codes(self.queryset)
        city_list = get_distinct_cities(self.queryset)
        state_list = get_distinct_states(self.queryset)
        add_serializer = self.add_serializer_class(address_data, many=True)
        data = {
            'addresses': add_serializer.data,
            'pin_codes': self.pincode_serializer_class(pin_code_list, many=True).data,
            'cities': self.city_serializer_class(city_list, many=True).data,
            'states': self.state_serializer_class(state_list, many=True).data
        }

        msg = "" if address_data else "no Address found"
        return get_response(msg, data, True)


class RelatedUsersListView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = UserSerializers
    queryset = get_user_model().objects.all()

    def get(self, request):
        """ GET API for RelatedUsersList """
        info_logger.info("RelatedUsersList GET api called.")
        if request.GET.get('id'):
            """ Get User for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Users List """
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(shops_data, many=True)
        msg = ""
        return get_response(msg, serializer.data, True)


class ShopView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.order_by('-id')
    serializer_class = ShopCrudSerializers

    def get(self, request):
        """ GET API for Shop """
        info_logger.info("Shop GET api called.")

        if request.GET.get('id'):
            """ Get Shop for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            shops_data = id_validation['data']
        else:
            """ GET Shop List """
            self.queryset = self.search_filter_shops_data()
            shops_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(shops_data, many=True)
        msg = "" if shops_data else "no shop found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Shop Creation with Image Category & Tax """

        info_logger.info("Shop POST api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Shop Created Successfully.")
            return get_response('shop created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Shop Updation with Image Category & Tax """

        info_logger.info("Shop PUT api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update shop', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        shop_instance = id_instance['data'].last()

        serializer = self.serializer_class(
            instance=shop_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Shop Updated Successfully.")
            return get_response('shop updated!', serializer.data)
        print(serializer.errors)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Shop with image """

        info_logger.info("Shop DELETE api called.")
        if not request.data.get('shop_id'):
            return get_response('please provide shop_id', False)
        try:
            for id in request.data.get('shop_id'):
                shop_id = self.queryset.get(id=int(id))
                try:
                    shop_id.delete()
                except:
                    return get_response(f'can not delete shop {shop_id.name}', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid shop_id {id}', False)
        return get_response('shop were deleted successfully!', True)

    def search_filter_shops_data(self):
        search_text = self.request.GET.get('search_text')
        shop_type = self.request.GET.get('shop_type')
        shop_owner = self.request.GET.get('shop_owner')
        pin_code = self.request.GET.get('pin_code')
        city = self.request.GET.get('city')
        status = self.request.GET.get('status')
        approval_status = self.request.GET.get('approval_status')

        '''search using shop_name and parent_shop based on criteria that matches'''
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)

        '''Filters using shop_type, shop_owner, pin_code, city, status, approval_status'''
        if shop_type:
            self.queryset = self.queryset.filter(shop_type__id=shop_type)

        if shop_owner:
            self.queryset = self.queryset.filter(shop_owner=shop_owner)

        if pin_code:
            self.queryset = self.queryset.\
                filter(shop_name_address_mapping__address_type='shipping').\
                filter(shop_name_address_mapping__pincode=pin_code)

        if city:
            self.queryset = self.queryset.\
                filter(shop_name_address_mapping__address_type='shipping').\
                filter(shop_name_address_mapping__city__city_name=city)

        if status:
            self.queryset = self.queryset.filter(status=status)

        if approval_status:
            self.queryset = self.queryset.\
                filter(approval_status=approval_status)

        return self.queryset
