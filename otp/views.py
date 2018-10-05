from django.conf import settings
from django.contrib.auth import authenticate, login, get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from django.conf import settings

import requests, datetime
from .sms import SendSms, SendVoiceSms
from .models import PhoneOTP
from .serializers import PhoneOTPValidateSerializer, ResendSmsOTPSerializer, \
                         ResendVoiceOTPSerializer, RevokeOTPSerializer, \
                         SendSmsOTPSerializer
from django.utils import timezone
from rest_framework.permissions import AllowAny

from otp.models import PhoneOTP

UserModel = get_user_model()

class ValidateOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = PhoneOTPValidateSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            number = request.data.get("phone_number")
            otp = request.data.get("otp")
            user = PhoneOTP.objects.filter(phone_number=number)
            if user.exists():
                user = user.last()
                msg, status_code = self.verify(otp, user)
                return Response(msg,
                    status=status_code
                )
            else:
                msg = {'is_success': False,
                        'message': ['User does not exist'],
                        'response_data': None }
                return Response(msg,
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
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

    def expired(self, user):
        current_time = datetime.datetime.now()
        expiry_time = datetime.timedelta(seconds=user.expires_in)
        created_time = user.created_at
        if current_time - created_time <= expiry_time:
            return False
        else:
            return True

    def max_attempts(self, user, attempts):
        if user.attempts <= getattr(settings, 'OTP_ATTEMPTS', attempts):
            return False
        else:
            return True

    def verify(self, otp, user):
        if otp == user.otp:
            if not self.expired(user) and not self.max_attempts(user, 5):
                user.is_verified = 1
                user.save()
                msg = {'is_success': True,
                        'message': ['User verified'],
                        'response_data': None }
                status_code=status.HTTP_200_OK
                return msg, status_code
            elif self.max_attempts(user, 5):
                msg = {'is_success': False,
                        'message': ['You have exceeded maximum attempts'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code
            elif self.expired(user):
                msg = {'is_success': False,
                        'message': ['OTP expired! Please request a new OTP'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code

        else:
            if self.max_attempts(user, 5):
                msg = {'is_success': False,
                        'message': ['You have exceeded maximum attempts'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code
            elif self.expired(user):
                msg = {'is_success': False,
                        'message': ['OTP expired! Please request a new OTP'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code
            user.attempts += 1
            user.save()
            reason = "OTP doesn't matched"
            msg = {'is_success': False,
                    'message': ["OTP doesn't matched"],
                    'response_data': None }
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            return msg, status_code

class SendSmsOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = SendSmsOTPSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            number = request.data.get("phone_number")
            user = UserModel.objects.filter(phone_number=number)
            if user.exists():
                msg = {'is_success': True,
                        'message': ['User already exists! Please login'],
                        'response_data': None,
                        'user_exists': True }
                return Response(msg,
                    status=status.HTTP_200_OK
                )
            else:
                phone_otp, otp = PhoneOTP.create_otp_for_number(number)
                date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
                time = datetime.datetime.now().strftime("%I:%M %p")
                message = SendSms(phone=number,
                                  body="%s is your One Time Password for GramFactory Account."\
                                       " Request time is %s, %s IST." % (otp,date,time))
                status_code, reason = message.send()
                if 'success' in reason:
                    phone_otp.last_otp = timezone.now()
                    phone_otp.save()
                    msg = {'is_success': True,
                            'message': [reason],
                            'response_data': None,
                            'user_exists': False  }
                    return Response(msg,
                        status=status.HTTP_200_OK
                    )
                else:
                    msg = {'is_success': False,
                            'message': [reason],
                            'response_data': None,
                            'user_exists': False }
                    return Response(msg,
                        status=status.HTTP_406_NOT_ACCEPTABLE
                    )
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

class ResendSmsOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = ResendSmsOTPSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            number = request.data.get("phone_number")
            user = PhoneOTP.objects.filter(phone_number=number)
            if user.exists():
                user = user.last()
                if self.just_now(user):
                    msg = {'is_success': False,
                            'message': [self.waiting()],
                            'response_data': None }
                    return Response(msg,
                        status=status.HTTP_406_NOT_ACCEPTABLE
                    )
                else:
                    otp = user.otp
                    date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
                    time = datetime.datetime.now().strftime("%I:%M %p")
                    message = SendSms(phone=number,
                                      body="%s is your One Time Password for GramFactory Account."\
                                           " Request time is %s, %s IST." % (otp,date,time))
                    status_code, reason = message.send()
                    if 'success' in reason:
                        user.last_otp = timezone.now()
                        user.save()
                        msg = {'is_success': True,
                                'message': [reason],
                                'response_data': None }
                        return Response(msg,
                            status=status.HTTP_200_OK
                        )
                    else:
                        msg = {'is_success': False,
                                'message': [reason],
                                'response_data': None }
                        return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE
                        )
            else:
                msg = {'is_success': False,
                        'message': ['User does not exist'],
                        'response_data': None }
                return Response(msg,
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
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

    def just_now(self, user):
        self.last_otp_time = user.last_otp
        self.current_time = datetime.datetime.now()
        self.resend_in = datetime.timedelta(seconds=user.resend_in)
        self.time_dif = self.current_time - self.last_otp_time
        if self.time_dif <= self.resend_in:
            return True
        else:
            return False

    def waiting(self):
        waiting_time = self.resend_in - self.time_dif
        seconds = str(waiting_time.total_seconds()).split('.')[0]
        return "You can resend OTP after %s seconds" % (seconds)

class ResendVoiceOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = ResendVoiceOTPSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            number = request.data.get("phone_number")
            user = PhoneOTP.objects.filter(phone_number=number)
            if user.exists():
                user = user.last()
                if self.just_now(user):
                    msg = {'is_success': False,
                            'message': [self.waiting()],
                            'response_data': None }
                    return Response(msg,
                        status=status.HTTP_406_NOT_ACCEPTABLE
                    )
                else:
                    otp = user.otp
                    otp = ','.join(x for x in str(otp))
                    message = SendVoiceSms(phone=number,
                                      body="OTP for your GramFactory account is %s" % (otp))
                    status_code, reason = message.send()
                    if status_code == requests.codes.ok:
                        msg = {'is_success': True,
                                'message': [reason],
                                'response_data': None }
                        return Response(msg,
                            status=status.HTTP_200_OK
                        )
                    else:
                        msg = {'is_success': False,
                                'message': [reason],
                                'response_data': None }
                        return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE
                        )
            else:
                msg = {'is_success': False,
                        'message': ['User does not exist'],
                        'response_data': None }
                return Response(msg,
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
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

    def just_now(self, user):
        self.last_otp_time = user.last_otp
        self.current_time = datetime.datetime.now()
        self.resend_in = datetime.timedelta(seconds=user.resend_in + 30)
        self.time_dif = self.current_time - self.last_otp_time
        if self.time_dif <= self.resend_in:
            return True
        else:
            return False

    def waiting(self):
        waiting_time = self.resend_in - self.time_dif
        seconds = str(waiting_time.total_seconds()).split('.')[0]
        return "You can resend OTP after %s seconds" % (seconds)

class RevokeOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = RevokeOTPSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            number = request.data.get("phone_number")
            user = PhoneOTP.objects.filter(phone_number=number)
            if user.exists():
                phone_otp, otp = PhoneOTP.update_otp_for_number(number)
                date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
                time = datetime.datetime.now().strftime("%I:%M %p")
                message = SendSms(phone=number,
                                  body="%s is your One Time Password for GramFactory Account."\
                                       " Request time is %s, %s IST." % (otp,date,time))
                status_code, reason = message.send()
                if 'success' in reason:
                    phone_otp.last_otp = timezone.now()
                    phone_otp.save()
                    msg = {'is_success': True,
                            'message': [reason],
                            'response_data': None }
                    return Response(msg,
                        status=status.HTTP_200_OK
                    )
                else:
                    msg = {'is_success': False,
                            'message': [reason],
                            'response_data': None }
                    return Response(msg,
                        status=status.HTTP_406_NOT_ACCEPTABLE
                    )
            else:
                msg = {'is_success': False,
                        'message': ['User does not exist'],
                        'response_data': None }
                return Response(msg,
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
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
