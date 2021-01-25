from .serializers import SendSmsOTPSerializer, PhoneOTPValidateSerializer, RewardsSerializer, ProfileUploadSerializer
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework import status
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from dal import autocomplete

from .models import PhoneOTP, MLMUser, Referral, Token, RewardPoint, Profile

import uuid
import requests, datetime
from django.utils import timezone

from django.db.models import Q
from .validation import ValidateOTP
from .sms import SendSms

from django.conf import settings
from retailer_backend.messages import *
from global_config.models import GlobalConfig


class SendSmsOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = SendSmsOTPSerializer

    def post(self, request, format=None):
        """
               This method will take phone_number & generate unique otp.
        """
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():

            number = request.data.get("phone_number")
            phone_otp, otp = PhoneOTP.create_otp_for_number(number)
            time = datetime.datetime.now().strftime("%I:%M %p")
            message = SendSms(phone=number,
                              body="%s is your One Time Password for Peppertap Account." \
                                   " Request time is %s IST." % (otp, time))
            message.send()
            phone_otp.last_otp = timezone.now()
            phone_otp.save()
            msg = {'is_success': True,
                   'message': "otp sent",
                   'response_data': None,
                   }
            return Response(msg,
                            status=status.HTTP_200_OK
                            )
        else:
            msg = {'is_success': False,
                   'message': serializer.errors['phone_number'][0],
                   'response_data': None}
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)


def save_user_referral_code(phone_number):
    """
        This method will generate Referral Code & create or update user in database.
    """
    user_referral_code = Referral.generate_unique_referral_code()
    MLMUser.objects.update_or_create(phone_number=phone_number, referral_code=user_referral_code)
    return user_referral_code


class Registrations(GenericAPIView):

    def post(self, request):
        """
            This method will create user & if user already there in MLM database validate otp.
        """
        try:
            data = request.data
            phone_number = data.get('phone_number')
            referral_code = data.get('referral_code')
            otp = data.get('otp')

            if phone_number is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Phone_Number'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)

            if otp is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Enter_OTP'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)

            if referral_code:
                """
                    checking entered referral code is valid or not.
                """
                user_id = MLMUser.objects.filter(referral_code=referral_code)
                if not user_id:
                    return Response({'message': VALIDATION_ERROR_MESSAGES['Referral_code'],
                                     'is_success': False,
                                     'response_data': None},
                                    status=HTTP_400_BAD_REQUEST)

            user_phone = MLMUser.objects.filter(
                Q(phone_number=phone_number)
            )
            if user_phone.exists():
                user = user_phone.last()
                if user.status == 1:
                    return Response({'message': VALIDATION_ERROR_MESSAGES['User_Already_Exist'],
                                     'is_success': False,
                                     'response_data': None},
                                    status=status.HTTP_409_CONFLICT)

                if not user.referral_code or user.referral_code == '':
                    save_user_referral_code(phone_number)
                user_referral_code = user.referral_code
            else:
                user_referral_code = save_user_referral_code(phone_number)

            referred = 1 if referral_code else 0
            msg = ValidateOTP(phone_number, otp, referred)
            if referral_code:
                Referral.store_parent_referral_user(referral_code, user_referral_code)
            return Response(msg.data, status=msg.status_code)

        except Exception as e:
            return Response({'message': "Data is not valid.", 'is_success': False, 'response_data': None},
                            status=status.HTTP_403_FORBIDDEN)


class Login(GenericAPIView):

    def post(self, request):
        """
            This method will validate user & if user already there in MLM database validate otp.
        """
        try:
            data = request.data
            phone_number = data.get('phone_number')
            otp = data.get('otp')
            if phone_number is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Phone_Number'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)
            if otp is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Enter_OTP'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)

            user_phone = MLMUser.objects.filter(
                Q(phone_number=phone_number)
            )
            if user_phone.exists():
                user_referral_code_none = MLMUser.objects.filter(phone_number=phone_number, referral_code=None)
                if user_referral_code_none:
                    save_user_referral_code(phone_number)
                msg = ValidateOTP(phone_number, otp)
                return Response(msg.data, status=msg.status_code)
            else:
                phone_number_otp = PhoneOTP.objects.filter(phone_number=phone_number, otp=otp)
                if phone_number_otp.exists():
                    save_user_referral_code(phone_number)
                    msg = ValidateOTP(phone_number, otp)
                    return Response(msg.data, status=msg.status_code)
                else:
                    msg = {'is_success': False,
                           'message': VALIDATION_ERROR_MESSAGES['OTP_NOT_MATCHED'],
                           'response_data': None}
                    status_code = status.HTTP_406_NOT_ACCEPTABLE
                    return Response(msg, status=status_code)
        except Exception:
            return Response(Exception, status=status.HTTP_403_FORBIDDEN)


class RewardsDashboard(GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        if request.META['HTTP_AUTHORIZATION']:
            auth = request.META['HTTP_AUTHORIZATION']
            resp = MLMUser.authenticate(auth)
            if not isinstance(resp, str):
                user_name = resp.name if resp.name else ''
                try:
                    rewards_obj = RewardPoint.objects.get(user=resp)
                    serializer = (RewardsSerializer(rewards_obj))
                    data = serializer.data
                except:
                    data = {"direct_users_count": '0', "indirect_users_count": '0', "direct_earned_points": '0',
                            "indirect_earned_points": '0', "total_earned_points": '0', 'total_points_used': '0',
                            'remaining_points': '0', 'welcome_reward_point': '0', "discount_point": '0'}
                data['name'] = user_name.capitalize()
                return Response({"data": data}, status=status.HTTP_200_OK)
            else:
                return Response({"error": resp}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"error": 'Authentication credentials were not provided.'},
                            status=status.HTTP_401_UNAUTHORIZED)


class Logout(GenericAPIView):
    """
    This class is used only for Logout API
    """
    permission_classes = (AllowAny,)
    http_method_names = ('delete',)

    @staticmethod
    def delete(request):
        """
        request:-Delete
        response:- Success and error message
        """
        if request.META['HTTP_AUTHORIZATION']:
            auth = request.META['HTTP_AUTHORIZATION']
            # to validate token is valid or not
            resp = MLMUser.authenticate(auth)

            if not isinstance(resp, str):
                try:
                    # query to delete the token in Token model
                    Token.objects.filter(token=auth.split(" ")[1]).delete()
                except:
                    return Response({"error": "Token is not valid."}, status=status.HTTP_401_UNAUTHORIZED)

                return Response({"data": "User has been successfully logged out."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": resp}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"error": 'Authentication credentials were not provided.'},
                            status=status.HTTP_401_UNAUTHORIZED)


class UploadProfile(GenericAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ProfileUploadSerializer

    def post(self, request):
        """
            Determine the current user by their token, and update their profile
        """
        if request.META['HTTP_AUTHORIZATION']:
            auth = request.META['HTTP_AUTHORIZATION']
            resp = MLMUser.authenticate(auth)
            try:
                user_id = Profile.objects.get(user=resp)
            except:
                return Response({"error": "Token is not valid."}, status=status.HTTP_401_UNAUTHORIZED)

            serializer = ProfileUploadSerializer(user_id, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": 'Authentication credentials were not provided.'},
                            status=status.HTTP_401_UNAUTHORIZED)
