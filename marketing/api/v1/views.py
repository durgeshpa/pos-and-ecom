from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.core.exceptions import ObjectDoesNotExist

from marketing.models import RewardPoint, Profile
from marketing.serializers import RewardsSerializer, ProfileUploadSerializer


class RewardsDashboard(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def get(self, request):
        """
            All Reward Credited/Used Details For User
        """
        user = self.request.user
        user_name = user.first_name if user.first_name else ''
        try:
            rewards_obj = RewardPoint.objects.get(user=user)
        except ObjectDoesNotExist:
            data = {"direct_users_count": '0', "indirect_users_count": '0', "direct_earned_points": '0',
                    "indirect_earned_points": '0', "total_earned_points": '0', 'total_points_used': '0',
                    'remaining_points': '0', 'welcome_reward_point': '0', "discount_point": '0'}
        else:
            data = RewardsSerializer(rewards_obj).data
        data['name'] = user_name.capitalize()
        return Response({'is_success': True, 'message': ['Success'], 'response_data': data}, status=status.HTTP_200_OK)


class UploadProfile(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ProfileUploadSerializer

    def post(self, request):
        """
            Update User Profile
        """
        try:
            profile = Profile.objects.get(user=self.request.user)
        except ObjectDoesNotExist:
            return Response({'is_success': False, 'message': ['User Profile Not Found'], 'response_data': None},
                            status=status.HTTP_200_OK)

        serializer = ProfileUploadSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'is_success': True, 'message': ['Successfully Updated Profile'],
                             'response_data': serializer.data}, status=status.HTTP_200_OK)
        else:
            errors = self.serializer_errors(serializer.errors)
            msg = {'is_success': False, 'message': [error for error in errors], 'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    @staticmethod
    def serializer_errors(serializer_errors):
        errors = []
        for field in serializer_errors:
            for error in serializer_errors[field]:
                if 'non_field_errors' in field:
                    result = error
                else:
                    result = ''.join('{} : {}'.format(field, error))
                errors.append(result)
        return errors
