from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework import status

from marketing.models import RewardPoint
from pos.common_functions import serializer_error, api_response

from ecom.utils import check_ecom_user, nearby_shops, validate_address_id
from ecom.models import Address
from .serializers import (AccountSerializer, RewardsSerializer, UserLocationSerializer, ShopSerializer,
                          AddressSerializer)


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
        return Response({"is_success": True, "message": "", "response_data": serializer.data})


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
        return Response({"is_success": True, "message": "", "response_data": serializer.data})


class ShopView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @check_ecom_user
    def get(self, request, *args, **kwargs):
        """
        Get nearest franchise retailer from user location - latitude, longitude
        """
        serializer = UserLocationSerializer(data=request.GET)
        if serializer.is_valid():
            data = serializer.data
            shop = nearby_shops(data['latitude'], data['longitude'])
            if shop:
                data = ShopSerializer(shop).data
                return Response({"is_success": True, "message": "", "response_data": data})
            else:
                return api_response('No nearby shop found!')
        else:
            return api_response(serializer_error(serializer))


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
        return Response({"is_success": True, "message": "", "response_data": serializer.data})
