from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from marketing.models import RewardPoint
from pos.common_functions import serializer_error, api_response

from ecom.utils import check_ecom_user, nearby_shops
from .serializers import AccountSerializer, RewardsSerializer, UserLocationSerializer, ShopSerializer


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
