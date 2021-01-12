from .serializers import SendSmsOTPSerializer, PhoneOTPValidateSerializer
from rest_framework.generics import GenericAPIView, CreateAPIView
from .models import PhoneOTP, MLMUser, Referral
from rest_framework import status
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
)
from rest_framework.response import Response
import requests, datetime
from django.utils import timezone
from rest_framework.permissions import AllowAny
from retailer_backend.messages import *
from .sms import SendSms
from django.db.models import Q
import uuid
from django.conf import settings


class SendSmsOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = SendSmsOTPSerializer

    def post(self, request, format=None):
        """
               This method will take phone_number validate number & generate unique otp.
        """
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():

            number = request.data.get("phone_number")
            phone_otp, otp = PhoneOTP.create_otp_for_number(number)
            date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
            time = datetime.datetime.now().strftime("%I:%M %p")
            message = SendSms(phone=number,
                              body="%s is your One Time Password for GramFactory Account." \
                                   " Request time is %s, %s IST." % (otp, date, time))
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
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field, error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)

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
                return Response({'error': 'Please provide phone_number '},
                                status=HTTP_400_BAD_REQUEST)
            if otp is None:
                return Response({'error': 'Please provide otp sent in your registered number'},
                                status=HTTP_400_BAD_REQUEST)
            if referral_code:
                user_id = MLMUser.objects.filter(referral_code=referral_code)
                if not user_id:
                    return Response({'error': 'Please provide valid referral code'},
                                        status=HTTP_400_BAD_REQUEST)

            user_phone = MLMUser.objects.filter(
                Q(phone_number__iexact=phone_number)
            )
            if user_phone.exists():
                print("here")
                user_referral_code_none = MLMUser.objects.filter(phone_number=phone_number, referral_code=None)
                if user_referral_code_none:
                    user_referral_code = Referral.generate_unique_referral_code()
                    updated_values = {'referral_code': user_referral_code}
                    obj, created = MLMUser.objects.update_or_create(phone_number=phone_number, defaults=updated_values)
                    obj.save()
                msg = ValidateOTP(data=request.POST)
                return Response(msg.data, status=msg.status_code)
            else:
                user_referral_code = Referral.generate_unique_referral_code()
                user = MLMUser.objects.create(phone_number=phone_number, referral_code=user_referral_code)
                user.save()
                Referral.store_parent_referral_user(referral_code, user_referral_code)
                msg = ValidateOTP(data=request.POST)
                return Response(msg.data, status=msg.status_code)
        except Exception:
            return Response(Exception, status=status.HTTP_403_FORBIDDEN)

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
                return Response({'error': 'Please provide phone_number '},
                                status=HTTP_400_BAD_REQUEST)
            if otp is None:
                return Response({'error': 'Please provide otp sent in your registered number'},
                                status=HTTP_400_BAD_REQUEST)

            user_phone = MLMUser.objects.filter(
                Q(phone_number__iexact=phone_number)
            )
            if user_phone.exists():
                user_referral_code_none = MLMUser.objects.filter(phone_number=phone_number, referral_code=None)
                if user_referral_code_none:
                    user_referral_code = Referral.generate_unique_referral_code()
                    updated_values = {'referral_code': user_referral_code}
                    obj, created = MLMUser.objects.update_or_create(phone_number=phone_number, defaults=updated_values)
                    obj.save()
                msg = ValidateOTP(data=request.POST)
                return Response(msg.data, status=msg.status_code)
            else:
                user_referral_code = Referral.generate_unique_referral_code()
                user = MLMUser.objects.create(phone_number=phone_number, referral_code=user_referral_code)
                user.save()
                msg, status_code = ValidateOTP(data=request.POST)
                return Response(msg.data, status=msg.status_code)
        except Exception:
            return Response(Exception, status=status.HTTP_403_FORBIDDEN)

def ValidateOTP(data):
    number = data.get("phone_number")
    otp = data.get("otp")
    user = PhoneOTP.objects.filter(phone_number=number)
    if user.exists():
        user = user.last()
        msg, status_code = verify(otp, user)
        return Response(msg, status=status_code)
    else:
        msg = {'is_success': False,
               'message': VALIDATION_ERROR_MESSAGES['USER_NOT_EXIST'],
               'response_data': None}
        return Response(msg,
                        status=status.HTTP_406_NOT_ACCEPTABLE
                        )
def expired(user):
    current_time = datetime.datetime.now()
    expiry_time = datetime.timedelta(seconds=user.expires_in)
    created_time = user.created_at
    if current_time - created_time <= expiry_time:
        return False
    else:
        return True

def max_attempts(user, attempts):
    if user.attempts < getattr(settings, 'OTP_ATTEMPTS', attempts):
        return False
    else:
        return True

def verify(otp, user):
    if otp == user.otp:
        if not expired(user) and not max_attempts(user, 5):
            user.is_verified = 1
            user.save()
            id = MLMUser.objects.get(phone_number=user.phone_number).id
            user_obj = MLMUser.objects.get(pk=id)
            user_obj.status = 1
            user_obj.save()
            token = user_obj.id = uuid.uuid4()
            msg = {'phone_number': user_obj.phone_number,
                   'token': token,
                   'referral_code': user_obj.referral_code,
                   'name': user_obj.name,
                   'email_id': user_obj.email
                   }
            status_code = status.HTTP_200_OK
            return msg, status_code
        elif max_attempts(user, 5):
            error_msg = VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED']
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            revoke = RevokeOTP(user.phone_number, error_msg)
            msg = revoke.update()
            return msg, status_code
        elif expired(user):
            error_msg = VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            revoke = RevokeOTP(user.phone_number, error_msg)
            msg = revoke.update()
            return msg, status_code

    else:
        if max_attempts(user, 5):
            error_msg = VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED']
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            revoke = RevokeOTP(user.phone_number, error_msg)
            msg = revoke.update()
            return msg, status_code
        elif expired(user):
            error_msg = VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            revoke = RevokeOTP(user.phone_number, error_msg)
            msg = revoke.update()
            return msg, status_code
        user.attempts += 1
        user.save()
        msg = {'is_success': False,
               'message': VALIDATION_ERROR_MESSAGES['OTP_NOT_MATCHED'],
               'response_data': None}
        status_code = status.HTTP_406_NOT_ACCEPTABLE
        return msg, status_code


class RevokeOTP(object):
    """Revoke OTP if epired or attempts exceeds"""

    def __init__(self, phone, error_msg):
        super(RevokeOTP, self).__init__()
        self.phone = phone
        self.error_msg = error_msg

    def update(self):
        number = self.phone
        phone_otp, otp = PhoneOTP.update_otp_for_number(number)
        date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
        time = datetime.datetime.now().strftime("%I:%M %p")
        message = SendSms(phone=number,
                          body="%s is your One Time Password for GramFactory Account." \
                               " Request time is %s, %s IST." % (otp, date, time))
        message.send()
        phone_otp.last_otp = timezone.now()
        phone_otp.save()
        msg = {'is_success': True,
               'message': "you entered otp is expired,new otp sent in your registered number",
               'response_data': None}
        return msg
