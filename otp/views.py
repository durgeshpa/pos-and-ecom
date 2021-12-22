import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from retailer_backend.messages import *
from accounts.tokens import account_activation_token

from .sms import SendSms, SendVoiceSms
from .models import PhoneOTP
from .serializers import PhoneOTPValidateSerializer, ResendSmsOTPSerializer, ResendVoiceOTPSerializer, \
    SendSmsOTPSerializer, api_serializer_errors

UserModel = get_user_model()


class ValidateOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = PhoneOTPValidateSerializer

    def post(self, request, *args, **kwargs):
        # Validate request data
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            return self.process_verification_request()
        else:
            return api_serializer_errors(serializer.errors)

    def process_verification_request(self):
        """
            Process valid request for otp verification
        """
        # Check if OTP requested
        user = PhoneOTP.objects.filter(phone_number=self.request.data.get("phone_number"))
        # Verify with last otp requested
        if user.exists():
            user = user.last()
            msg, status_code = self.verify(self.request.data.get("otp"), user)
            return Response(msg, status=status_code)
        # No otp requested yet
        else:
            return Response({'is_success': False, 'message': [VALIDATION_ERROR_MESSAGES['INVALID_DATA']],
                             'response_data': None}, status=status.HTTP_406_NOT_ACCEPTABLE)

    def verify(self, otp, user):
        """
            Verify if user is blocked currently
            If not blocked, match otp with last requested otp
            If matched, check for max attempts or expired otp. Else verify
            If not matched, check for max attempts or expired otp
        """
        otp_block_seconds = getattr(settings, 'OTP_BLOCK_INTERVAL', 1800)
        # Check if user was blocked
        if user.blocked:
            return self.user_blocked(user, otp_block_seconds)
        # Entered otp matches last requested otp
        if otp == user.otp:
            return self.otp_matched(user, otp_block_seconds)
        # Entered otp does not match last requested otp
        else:
            return self.otp_not_matched(user, otp_block_seconds)

    @staticmethod
    def user_blocked(user, otp_block_seconds):
        """
            If block time remains, return remaining block time
            Else refresh and request for new otp
        """
        current_time = datetime.datetime.now()
        otp_block_interval = datetime.timedelta(seconds=otp_block_seconds)
        re_request_delta = otp_block_interval - (current_time - user.modified_at)
        re_request_minutes = int(re_request_delta.total_seconds() / 60)
        msg = {'is_success': False, 'message': '', 'response_data': None}
        # If block time still remaining
        if re_request_minutes > 0:
            msg['message'] = VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(re_request_minutes)
        else:
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']]
        return msg, status.HTTP_406_NOT_ACCEPTABLE

    def otp_matched(self, user, otp_block_seconds):
        """
            Entered otp matched with last requested otp
            Check for max attempts and expired otp, else verify user
        """
        msg, status_code = {'is_success': False, 'message': '', 'response_data': None}, status.HTTP_406_NOT_ACCEPTABLE
        if not self.expired(user) and not self.max_attempts(user, 10):
            user.is_verified = 1
            user.save()
            if self.request.data.get('password_reset', 0) == 1:
                user = UserModel.objects.filter(phone_number=user.phone_number).last()
                if user:
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    token = account_activation_token.make_token(user)
                    msg['response_data'] = [{'uid': uid, 'token': token}]
            msg['is_success'], msg['message'] = True, [SUCCESS_MESSAGES['MOBILE_NUMBER_VERIFIED']]
            status_code = status.HTTP_200_OK
        elif self.max_attempts(user, 10):
            user.blocked = 1
            user.save()
            msg['message'] = [
                VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(int(otp_block_seconds / 60))]
        elif self.expired(user):
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']]
        return msg, status_code

    def otp_not_matched(self, user, otp_block_seconds):
        """
            Entered otp does not match last requested otp
            Check for max attempts or expired otp or only mismatch
        """
        msg, status_code = {'is_success': False, 'message': '', 'response_data': None}, status.HTTP_406_NOT_ACCEPTABLE
        if self.max_attempts(user, 10):
            user.blocked = 1
            user.save()
            msg['message'] = [
                VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(int(otp_block_seconds / 60))]
        elif self.expired(user):
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']]
        else:
            user.attempts += 1
            user.save()
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_NOT_MATCHED']]
        return msg, status_code

    @staticmethod
    def expired(user):
        """
            Check if otp has expired
        """
        current_time, expiry_time = datetime.datetime.now(), datetime.timedelta(seconds=user.expires_in)
        return False if (current_time - user.created_at <= expiry_time) else True

    @staticmethod
    def max_attempts(user, attempts):
        """
            Check if max attempts for otp have exceeded
        """
        return False if (user.attempts < getattr(settings, 'OTP_ATTEMPTS', attempts)) else True


class ValidateOTPInternal:
    def verify(self, otp, user):
        """
            Verify if user is blocked currently
            If not blocked, match otp with last requested otp
            If matched, check for max attempts or expired otp. Else verify
            If not matched, check for max attempts or expired otp
        """
        otp_block_seconds = getattr(settings, 'OTP_BLOCK_INTERVAL', 1800)
        # Check if user was blocked
        if user.blocked:
            return self.user_blocked(user, otp_block_seconds)
        # Entered otp matches last requested otp
        if otp == user.otp:
            return self.otp_matched(user, otp_block_seconds)
        # Entered otp does not match last requested otp
        else:
            return self.otp_not_matched(user, otp_block_seconds)

    @staticmethod
    def user_blocked(user, otp_block_seconds):
        """
            If block time remains, return remaining block time
            Else refresh and request for new otp
        """
        current_time = datetime.datetime.now()
        otp_block_interval = datetime.timedelta(seconds=otp_block_seconds)
        re_request_delta = otp_block_interval - (current_time - user.modified_at)
        re_request_minutes = int(re_request_delta.total_seconds() / 60)
        msg = {'is_success': False, 'message': '', 'response_data': None}
        # If block time still remaining
        if re_request_minutes > 0:
            msg['message'] = VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(re_request_minutes)
        else:
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']]
        return msg, status.HTTP_406_NOT_ACCEPTABLE

    def otp_matched(self, user, otp_block_seconds):
        """
            Entered otp matched with last requested otp
            Check for max attempts and expired otp, else verify user
        """
        msg, status_code = {'is_success': False, 'message': '', 'response_data': None}, status.HTTP_406_NOT_ACCEPTABLE
        if not self.expired(user) and not self.max_attempts(user, 10):
            user.is_verified = 1
            user.save()
            msg['is_success'], msg['message'] = True, [SUCCESS_MESSAGES['MOBILE_NUMBER_VERIFIED']]
            status_code = status.HTTP_200_OK
        elif self.max_attempts(user, 10):
            user.blocked = 1
            user.save()
            msg['message'] = [
                VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(int(otp_block_seconds / 60))]
        elif self.expired(user):
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']]
        return msg, status_code

    def otp_not_matched(self, user, otp_block_seconds):
        """
            Entered otp does not match last requested otp
            Check for max attempts or expired otp or only mismatch
        """
        msg, status_code = {'is_success': False, 'message': '', 'response_data': None}, status.HTTP_406_NOT_ACCEPTABLE
        if self.max_attempts(user, 10):
            user.blocked = 1
            user.save()
            msg['message'] = [
                VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(int(otp_block_seconds / 60))]
        elif self.expired(user):
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']]
        else:
            user.attempts += 1
            user.save()
            msg['message'] = [VALIDATION_ERROR_MESSAGES['OTP_NOT_MATCHED']]
        return msg, status_code

    @staticmethod
    def expired(user):
        """
            Check if otp has expired
        """
        current_time, expiry_time = datetime.datetime.now(), datetime.timedelta(seconds=user.expires_in)
        return False if (current_time - user.created_at <= expiry_time) else True

    @staticmethod
    def max_attempts(user, attempts):
        """
            Check if max attempts for otp have exceeded
        """
        return False if (user.attempts < getattr(settings, 'OTP_ATTEMPTS', attempts)) else True


class SendSmsOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = SendSmsOTPSerializer

    def post(self, request, *args, **kwargs):
        # Validate request data
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            ph_no, otp_type, app_type = self.request.data.get("phone_number"), self.request.data.get('otp_type', "1") , request.data.get('app_type')
            msg, status_code = RequestOTPCls.process_otp_request(ph_no, otp_type, app_type)
            return Response(msg, status=status_code)
        else:
            return api_serializer_errors(serializer.errors)


class RequestOTPCls(object):

    @classmethod
    def process_otp_request(cls, ph_no, otp_type, app_type='2'):
        """
            Process valid request for otp
        """
        # Check if user is currently blocked OR has to be blocked OR has to be unblocked
        block_unblock_response = RequestOTPCls.block_unblock_user(ph_no)
        if not block_unblock_response['success']:
            return block_unblock_response, status.HTTP_406_NOT_ACCEPTABLE
        # Send new sms or voice OTP
        if otp_type == "2":
            return RequestOTPCls.send_new_voice_otp(ph_no)
        else:
            return RequestOTPCls.send_new_text_otp(ph_no, app_type)

    @staticmethod
    def send_new_voice_otp(ph_no):
        """
            Generate and send new otp on call
        """
        phone_otp, otp = PhoneOTP.create_otp_for_number(ph_no)
        sms_body = "OTP for your Peppertap  account is %s" % otp
        message = SendVoiceSms(phone=ph_no, body=sms_body)
        message.send()
        phone_otp.last_otp = timezone.now()
        phone_otp.save()
        msg = {'is_success': True, 'message': ["You will receive a call soon on {}".format(ph_no)],
               'response_data': None}
        return msg, status.HTTP_200_OK

    @staticmethod
    def send_new_text_otp(ph_no, app_type):
        """
            Generate and send new otp on sms
        """
        phone_otp, otp = PhoneOTP.create_otp_for_number(ph_no)
        date, time = datetime.datetime.now().strftime("%a(%d/%b/%y)"), datetime.datetime.now().strftime("%I:%M %p")
        sms_body = ''
        mask ='GRMFAC'
        if app_type =='3':
            sms_body = "%s is your One Time Password for Peppertap  Account. Request time is %s, %s IST." % (
                otp, date, time)
            mask = 'PEPTAB'
        else:
            sms_body = "%s is your One Time Password for Gramfactory  Account. Request time is %s, %s IST." % (
                otp, date, time)
            mask = 'GRMFAC'

        message = SendSms(phone=ph_no, body=sms_body, mask=mask)
        message.send()
        phone_otp.last_otp = timezone.now()
        phone_otp.save()
        msg = {'is_success': True, 'message': ["OTP sent to {}".format(ph_no)], 'response_data': None}
        return msg, status.HTTP_200_OK

    @staticmethod
    def block_unblock_user(ph_no):
        """
            Check if user is currently blocked OR has to be blocked OR has to be unblocked
        """
        response = {'success': True, 'message': [], 'response_data': None}
        user = PhoneOTP.objects.filter(phone_number=ph_no)
        if user.exists():
            user = user.last()
            current_time = datetime.datetime.now()
            otp_block_seconds = getattr(settings, 'OTP_BLOCK_INTERVAL', 1800)
            otp_block_interval = datetime.timedelta(seconds=otp_block_seconds)
            if user.blocked:
                re_request_delta = otp_block_interval - (current_time - user.modified_at)
                re_request_minutes = int(re_request_delta.total_seconds() / 60)
                if re_request_minutes > 0:
                    response['success'] = False
                    response['message'] = [
                        VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(re_request_minutes)]
            else:
                otp_requests = PhoneOTP.objects.filter(phone_number=ph_no, is_verified=False,
                                                       created_at__gt=current_time - otp_block_interval, ).count()
                if otp_requests >= getattr(settings, 'OTP_REQUESTS', 3):
                    user.blocked = 1
                    user.save()
                    re_request_minutes = int(otp_block_seconds / 60)
                    response['success'] = False
                    response['message'] = [
                        VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED'].format(re_request_minutes)]
        return response


# Todo remove
class ResendVoiceOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = ResendVoiceOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            number = request.data.get("phone_number")
            user = PhoneOTP.objects.filter(phone_number=number)
            if user.exists():
                user = user.last()
                if self.just_now(user):
                    msg = {'is_success': False, 'message': [self.waiting()], 'response_data': None}
                    return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    otp = user.otp
                    otp = ','.join(x for x in str(otp))
                    message = SendVoiceSms(phone=number, body="OTP for your GramFactory account is %s" % otp)
                    message.send()
                    user.last_otp = timezone.now()
                    user.save()
                    msg = {'is_success': True, 'message': ["You will receive your call soon"], 'response_data': None}
                    return Response(msg, status=status.HTTP_200_OK)
            else:
                msg = {'is_success': False, 'message': [VALIDATION_ERROR_MESSAGES['INVALID_DATA']],
                       'response_data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            return api_serializer_errors(serializer.errors)

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
        return "You can resend OTP after %s seconds" % seconds


# Todo remove
class SendSmsOTPAnytime(CreateAPIView):
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
                           'response_data': None}
                    return Response(msg,
                                    status=status.HTTP_406_NOT_ACCEPTABLE
                                    )
                else:
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
                           'message': ["message sent"],
                           'response_data': None}
                    return Response(msg,
                                    status=status.HTTP_200_OK
                                    )
            else:
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
                       'message': ["message sent"],
                       'response_data': None}
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
                   'response_data': None}
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
