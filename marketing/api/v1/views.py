from rest_framework.generics import GenericAPIView
from rest_framework import status
import logging
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_auth.authentication import TokenAuthentication
from django.core.exceptions import ObjectDoesNotExist
from products.common_function import get_response

from marketing.models import RewardPoint, Profile, UserRating
from marketing.serializers import RewardsSerializer, ProfileUploadSerializer
info_logger = logging.getLogger('file-info')


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
            rewards_obj = RewardPoint.objects.get(reward_user=user)
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
            profile = Profile.objects.get(profile_user=self.request.user)
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


class RatingFeedback(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def post(self, request):
        """
            Store ratings given by user
        """
        user = self.request.user
        pop_up = self.request.data.get("pop_up")
        rating = self.request.data.get("rating")
        code = 1
        msg = ""
        try:
            if pop_up:
                ratingobj = UserRating.objects.filter(user=user).last()
                if not ratingobj or ratingobj.rating < 4:
                    msg = "Show PopUp Rating Screen"
                    code = 2
                    return get_response(msg, data=code)
                msg = "Don't Show PopUp Rating Screen"
                return get_response(msg, data=code)
            else:
                if int(rating) > 3:
                    ratingobj = UserRating.objects.filter(user=user).last()
                    if not ratingobj or ratingobj.rating < 4:
                        msg = "We are glad you're enjoying our app. Please rate us on Playstore"
                        code = 2
                else:
                    msg = "Oh! Help us to assist you better!"
                    code = 3
                if code != 1:
                    UserRating.objects.create(
                        user=user,
                        rating=int(rating),
                    )
                    return get_response(msg, data=code)
                return get_response(msg, data=code)
        except:
            info_logger.info("User rating not created for user :: {}".format(user))


    def put(self, request):
        """
            Update feedback given by user
        """
        user = self.request.user
        feedback = self.request.data.get("feedback")
        try:
            if feedback:
                ratingobj = UserRating.objects.filter(user=user).last()
                if ratingobj:
                    ratingobj.feedback = feedback
                    ratingobj.save()
                return get_response("Feedback updated")

        except:
            info_logger.info("User feedback not created for user :: {} with id :: {}".format(user, ratingobj.id))
