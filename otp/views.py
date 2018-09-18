from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from django.conf import settings

import requests, datetime
from .sms import SendSms, SendVoiceSms
from .models import PhoneOTP
from .serializers import PhoneOTPValidateSerializer, ResendSmsOTPSerializer, ResendVoiceOTPSerializer, RevokeOTPSerializer
from django.utils import timezone
from rest_framework.permissions import AllowAny

class ValidateOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = PhoneOTPValidateSerializer

    def post(self, request, format=None):
        ser = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if ser.is_valid():
            number = request.data.get("phone_number")
            otp = request.data.get("otp")
            try:
                user = PhoneOTP.objects.get(phone_number=number)
                if user:
                    import pdb;
                    #pdb.set_trace()
                    reason, status_code = self.verify(otp, user)
                    return Response(
                        {'reason': reason},
                        status=status_code
                    )
            except ObjectDoesNotExist:
                return Response(
                    {'reason': 'User does not exist'},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)

    def expired(self, user):
        current_time = datetime.datetime.now()
        expiry_time = datetime.timedelta(seconds=user.expires_in)
        created_time = user.created_at
        if current_time - created_time <= expiry_time:
            return False
        else:
            return True

    def max_attempts(self, otp, user, attempts):
        if user.attempts <= getattr(settings, 'OTP_ATTEMPTS', attempts):
            return False
        else:
            return True

    def verify(self, otp, user):
        if otp == user.otp:
            if not self.expired(user) and not self.max_attempts(otp, user, 5):
                user.is_verified = 1
                user.save()
                reason = "User Verified"
                status_code=status.HTTP_200_OK
                return reason, status_code
            elif self.max_attempts(otp, user, 5):
                reason = "You have exceeded maximum attempts"
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return reason, status_code
            elif self.expired(user):
                reason = "OTP has been expired"
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return reason, status_code

        else:
            user.attempts += 1
            user.save()
            reason = "OTP doesn't matched"
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            return reason, status_code

class ResendSmsOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = ResendSmsOTPSerializer

    def post(self, request, format=None):
        ser = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if ser.is_valid():
            number = request.data.get("phone_number")
            try:
                user = PhoneOTP.objects.get(phone_number=number)
                if user:
                    if self.just_now(user):
                        reason = self.waiting()
                        return Response(
                            {'reason': reason},
                            status=status.HTTP_406_NOT_ACCEPTABLE
                        )
                    else:
                        otp = user.otp
                        message = SendSms(phone=number,
                                          body="%s is the OTP for your GramFactory Account." % (otp))
                        status_code, reason = message.send()
                        if 'success' in reason:
                            user.last_otp = timezone.now()
                            user.save()
                        if status_code == requests.codes.ok:
                            return Response(
                                {'reason': reason},
                                status=status.HTTP_200_OK
                            )
                        else:
                            return Response(
                                {'reason': reason},
                                status=status.HTTP_406_NOT_ACCEPTABLE
                            )
            except ObjectDoesNotExist:
                return Response(
                    {'reason': 'User does not exist'},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)

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
        ser = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if ser.is_valid():
            number = request.data.get("phone_number")
            try:
                user = PhoneOTP.objects.get(phone_number=number)
                if user:
                    if self.just_now(user):
                        reason = self.waiting()
                        return Response(
                            {'reason': reason},
                            status=status.HTTP_406_NOT_ACCEPTABLE
                        )
                    else:
                        otp = user.otp
                        message = SendVoiceSms(phone=number,
                                          body="OTP for your GramFactory account is %s" % (otp))
                        status_code, reason = message.send()
                        if status_code == requests.codes.ok:
                            if 'success' in reason:
                                user.last_otp = timezone.now()
                                user.save()
                            return Response(
                                {'reason': reason},
                                status=status.HTTP_200_OK
                            )
                        else:
                            return Response(
                                {'reason': reason},
                                status=status.HTTP_406_NOT_ACCEPTABLE
                            )
            except ObjectDoesNotExist:
                return Response(
                    {'reason': 'User does not exist'},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)

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
        ser = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if ser.is_valid():
            number = request.data.get("phone_number")
            try:
                user = PhoneOTP.objects.get(phone_number=number)
                if user:
                    PhoneOTP.update_otp_for_number(number)
                    return Response(
                        {'reason': 'OTP sent'},
                        status=status.HTTP_200_OK
                    )
            except ObjectDoesNotExist:
                return Response(
                    {'reason': 'User does not exist'},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)
