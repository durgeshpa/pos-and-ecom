from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated)
from rest_framework.response import Response
from addresses.models import Country, State, City, Area, Address, Pincode
from .serializers import (CountrySerializer, StateSerializer, CitySerializer,
        AreaSerializer, AddressSerializer, PinCityStateSerializer)
from rest_framework import generics
from rest_framework import status
from rest_framework import permissions, authentication
from shops.models import Shop, ShopUserMapping
from django.http import Http404
from rest_framework import serializers
from pos.common_functions import api_response


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
