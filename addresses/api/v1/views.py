from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated)
from rest_framework.response import Response
from addresses.models import Country, State, City, Area, Address, Pincode, Route
from retailer_backend.utils import SmallOffsetPagination
from .serializers import (CountrySerializer, StateSerializer, CitySerializer,
                          AreaSerializer, AddressSerializer, PinCityStateSerializer, CityRouteSerializer,
                          StateBasicSerializer, CityBasicSerializer)
from rest_framework import generics
from rest_framework import status
from rest_framework import permissions
from rest_auth import authentication
from shops.models import Shop, ShopUserMapping
from django.http import Http404
from rest_framework import serializers
from pos.common_functions import api_response
from ...common_functions import serializer_error_batch, serializer_error
from ...common_validators import get_validate_routes, validate_data_dict_format, validate_id
import logging


info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class CountryView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (AllowAny,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': None,
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

class StateView(generics.ListAPIView):
    serializer_class = StateSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = State.objects.all().order_by('state_name')
        country_id = self.request.query_params.get('country_id', None)
        if country_id is not None:
            queryset = queryset.filter(country=country_id)
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': None,
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

class CityView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = City.objects.all().order_by('city_name')
        state_id = self.request.query_params.get('state_id', None)
        if state_id is not None:
            queryset = queryset.filter(state__id=state_id)
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': None,
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

class AreaView(generics.ListCreateAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = (AllowAny,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True,
                'message': None,
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True,
                    'message': ["Area added"],
                    'response_data': None}
            return Response(msg,
                            status=status.HTTP_200_OK)
        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)

class AddressView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        shop_id = self.request.query_params.get('shop_id', None)
        queryset = Address.objects.filter(shop_name=shop_id)
        return queryset

    def create(self, request, *args, **kwargs):
        pincode_id = Pincode.objects.filter(
            city=request.data.get('city', None),
            pincode=request.data.get('pincode', None))
        if not pincode_id.exists():
            msg = {'is_success': False,
                   'message': ['Invalid pincode for selected City'],
                   'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(pincode_link=pincode_id.last())
            msg = {'is_success': True,
                    'message': ["Address added successfully"],
                    'response_data': serializer.data}
            return Response(msg,
                            status=status.HTTP_200_OK)
        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)

    def list(self, request):
        queryset = self.get_queryset()
        shipping_queryset = queryset.filter(address_type='shipping')
        billing_queryset = queryset.filter(address_type='billing')
        shipping_serializer = self.get_serializer(shipping_queryset, many=True)
        billing_serializer = self.get_serializer(billing_queryset, many=True)

        msg = {'is_success': True,
                'message': ["%s objects found" % (queryset.count())],
                'response_data': {'shipping_address':shipping_serializer.data,
                                'billing_address':billing_serializer.data}}
        return Response(msg,
                        status=status.HTTP_200_OK)

class AddressDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self, pk):
        try:
            return Address.objects.get(pk=pk)
        except Address.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        address = self.get_object(pk)
        serializer = AddressSerializer(address)
        msg = {'is_success': True,
                'message': ["shop address"],
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        address = self.get_object(pk)
        serializer = AddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            msg = {'is_success': True,
                    'message': ["Address updated!"],
                    'response_data': serializer.data}
            return Response(msg,
                            status=status.HTTP_200_OK)
        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)

    def delete(self, request, pk, format=None):
        address = self.get_object(pk)
        address.delete()
        msg = {'is_success': True,
                'message': ["shop address deleted successfully"],
                'response_data': None }
        return Response(msg, status=status.HTTP_204_NO_CONTENT)


class DefaultAddressView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        default = self.kwargs.get(self.lookup_url_kwarg)
        user_shops = Shop.objects.filter(shop_owner=self.request.user)
        address_list = []
        for shop in user_shops:
            shop_address = Address.objects.filter(shop_name=shop).order_by('created_at').first()
            if shop_address:
                address_list.append(shop_address)
        queryset = address_list
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        msg = {'is_success': True if serializer.data else False,
                'message': [""],
                'response_data': serializer.data}
        return Response(msg,
                        status=status.HTTP_200_OK)


class SellerShopAddress(generics.ListAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AddressSerializer

    def get_queryset(self):
        queryset = Address.objects.none()
        shop_id = self.request.query_params.get('shop_id', None)
        if shop_id is not None:
            queryset = Address.objects.filter(shop_name_id=shop_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        shipping_queryset = queryset.filter(address_type='shipping')
        billing_queryset = queryset.filter(address_type='billing')
        shipping_serializer = self.get_serializer(shipping_queryset, many=True)
        billing_serializer = self.get_serializer(billing_queryset, many=True)

        msg = {'is_success': True,
                'message': ["%s objects found" % (queryset.count())],
                'response_data': {'shipping_address':shipping_serializer.data,
                                'billing_address':billing_serializer.data}}
        return Response(msg,
                        status=status.HTTP_200_OK)


class PinCityStateView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PinCityStateSerializer

    def get(self, request, *args, **kwargs):
        pin_code = self.request.GET.get('pincode')
        if not pin_code:
            return api_response("Please provide a pin code")
        pin_code_obj = Pincode.objects.filter(pincode=pin_code).select_related(
            'city', 'city__state').last()
        if pin_code_obj:
            data = self.serializer_class(pin_code_obj).data
            return api_response('', data, status.HTTP_200_OK, True)
        return api_response('No City Found For Given Pin Code')


class StateFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = StateBasicSerializer
    queryset = State.objects.all()

    def get(self, request):
        self.queryset = self.search_filter_state()
        state_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(state_data, many=True)
        msg = "" if state_data else "no state found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)

    def search_filter_state(self):
        """ Filters the data based on request"""
        search_text = self.request.GET.get('search_text')
        country = self.request.GET.get('country')

        if search_text:
            self.queryset = self.queryset.filter(Q(state_name__icontains=search_text)|
                                                 Q(country__country_name__icontains=search_text))

        if country:
            self.queryset = self.queryset.filter(country_id=country)

        return self.queryset.distinct('id')


class CityFilterView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = CityBasicSerializer
    queryset = City.objects.all()

    def get(self, request):
        self.queryset = self.search_filter_city()
        city_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(city_data, many=True)
        msg = "" if city_data else "no city found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)

    def search_filter_city(self):
        """ Filters the data based on request"""
        search_text = self.request.GET.get('search_text')
        state = self.request.GET.get('state')

        if search_text:
            self.queryset = self.queryset.filter(Q(city_name__icontains=search_text)|
                                                 Q(state__state_name__icontains=search_text))

        if state:
            self.queryset = self.queryset.filter(state_id=state)

        return self.queryset.distinct('id')


class RouteView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Route.objects.order_by('-id')
    serializer_class = CityRouteSerializer

    def get(self, request):
        self.queryset = self.search_filter_route_data()
        self.queryset = self.queryset.values('city_id').order_by('city_id').distinct()
        routes = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(routes, many=True)
        msg = "" if routes else "no route found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)

    def put(self, request, *args, **kwargs):
        modified_data = validate_data_dict_format(self.request)
        if 'error' in modified_data:
            return api_response(modified_data['error'])
        validated_data = get_validate_routes(modified_data)
        if 'error' in validated_data:
            return api_response(validated_data['error'])

        if validated_data['data']['route_update_ids']:
            self.remove_non_exist_city_routes(validated_data['data']['route_update_ids'], modified_data['city_id'])

        resp_data = self.create_update_city_routes(validated_data['data']['routes'])
        if 'error' in resp_data:
            return api_response(resp_data['error'])
        return api_response(resp_data['data'], self.serializer_class({"city_id": modified_data['city_id']}).data,
                            status.HTTP_200_OK, True)

    def remove_non_exist_city_routes(self, route_ids, city_id):
        routes_to_be_deleted = Route.objects.filter(~Q(id__in=route_ids), city_id=city_id)
        for route in routes_to_be_deleted:
            if route.route_shops.exists():
                route.route_shops.all().delete()
        routes_to_be_deleted.delete()

    def create_update_city_routes(self, data_list):
        try:
            for data in data_list:
                if 'id' in data and data['id']:
                    Route.objects.filter(id=data['id'], city_id=data['city']).\
                        update(name=data['name'], updated_by=self.request.user)
                else:
                    Route.objects.create(city_id=data['city'], name=data['name'], created_by=self.request.user)
        except Exception as ex:
            return {"error": "Unable to add/update route."}
        return {'data': 'City Route has been done successfully!'}

    def search_filter_route_data(self):
        search_text = self.request.GET.get('search_text')
        name = self.request.GET.get('name')
        city_id = self.request.GET.get('city_id')
        state_id = self.request.GET.get('state_id')

        if search_text:
            self.queryset = self.queryset.filter(name__icontains=search_text)

        if name:
            self.queryset = self.queryset.filter(name=name)

        if city_id:
            self.queryset = self.queryset.filter(city_id=city_id)

        if state_id:
            self.queryset = self.queryset.filter(city__state_id=state_id)

        return self.queryset


class CitiesView(generics.GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = City.objects.order_by('-id')
    serializer_class = CityBasicSerializer

    def get(self, request):
        """ GET API for City """
        info_logger.info("City GET api called.")
        city_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get City for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return api_response(id_validation['error'])
            cities_data = id_validation['data']
        else:
            """ GET City List """
            self.queryset = self.search_filter_city_data()
            city_total_count = self.queryset.count()
            cities_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(cities_data, many=True)
        msg = f"total count {city_total_count}" if cities_data else "no city found"
        return api_response(msg, serializer.data, status.HTTP_200_OK, True)

    def post(self, request):
        """ POST API for City Creation with Image """

        info_logger.info("City POST api called.")
        modified_data = validate_data_dict_format(self.request)
        if 'error' in modified_data:
            return api_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data, context={"user": self.request.user})
        if serializer.is_valid():
            serializer.save()
            info_logger.info("City Created Successfully.")
            return api_response('city created successfully!', serializer.data, status.HTTP_200_OK, True)
        return api_response(serializer_error(serializer))

    def put(self, request):
        """ PUT API for City Updation """

        info_logger.info("City PUT api called.")
        modified_data = validate_data_dict_format(self.request)
        if 'error' in modified_data:
            return api_response(modified_data['error'])

        if 'id' not in modified_data:
            return api_response('please provide id to update city', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_validation:
            return api_response(id_validation['error'])
        city_instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=city_instance, data=modified_data,
                                           context={"user": self.request.user})
        if serializer.is_valid():
            serializer.save()
            info_logger.info("City Updated Successfully.")
            return api_response('city updated!', serializer.data, status.HTTP_200_OK, True)
        return api_response(serializer_error(serializer))

    def delete(self, request):
        """ Delete City """

        info_logger.info("City DELETE api called.")
        if not request.data.get('city_id'):
            return api_response('please provide city_id')
        try:
            for city in request.data.get('city_id'):
                city_id = self.queryset.get(id=int(city))
                try:
                    city_id.delete()
                except:
                    return api_response(f'can not delete city | {city_id.id} | getting used')
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return api_response(f'please provide a valid city')
        return api_response('city were deleted successfully!', None, status.HTTP_200_OK, True)

    def search_filter_city_data(self):
        search_text = self.request.GET.get('search_text')
        route_name = self.request.GET.get('route_name')
        route_id = self.request.GET.get('route_id')
        state_id = self.request.GET.get('state_id')

        if search_text:
            self.queryset = self.queryset.filter(Q(city_routes__name__icontains=search_text) |
                                                 Q(city_name__icontains=search_text)).distinct()

        if route_name:
            self.queryset = self.queryset.filter(city_routes__name=route_name)

        if route_id:
            self.queryset = self.queryset.filter(city_routes__id=route_id)

        if state_id:
            self.queryset = self.queryset.filter(state_id=state_id)

        return self.queryset
