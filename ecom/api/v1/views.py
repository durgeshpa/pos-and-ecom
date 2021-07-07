from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from marketing.models import RewardPoint

from .serializers import AccountSerializer, RewardsSerializer


class AccountView(APIView):
    serializer_class = AccountSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

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

    def get(self, request, *args, **kwargs):
        """
        All Reward Credited/Used Details For User
        """
        serializer = self.serializer_class(
            RewardPoint.objects.filter(reward_user=self.request.user).select_related('reward_user').last())
        return Response({"is_success": True, "message": "", "response_data": serializer.data})
