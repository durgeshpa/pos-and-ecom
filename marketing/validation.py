from .token import tokenGeneartion
from django.conf import settings
from .models import PhoneOTP, MLMUser
from rest_framework import status
from rest_framework.response import Response
import datetime
from retailer_backend.messages import *
from .sms import SendSms
from django.utils import timezone


def ValidateOTP(phone_number, otp):
    """
         Check otp is validated or not.
    """

    user = PhoneOTP.objects.filter(phone_number=phone_number)
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
        """if OTP matched with Registered OTP"""

        if not expired(user) and not max_attempts(user, 5):
            """if OTP is not expired or not max attempts exceeds"""

            user.is_verified = 1
            user.save()
            user_id = MLMUser.objects.get(phone_number=user.phone_number)
            id = user_id.id
            user_obj = MLMUser.objects.get(pk=id)
            user_obj.status = 1
            user_obj.save()
            token = tokenGeneartion(user_id)
            msg = {'phone_number': user_obj.phone_number,
                   'token': token,
                   'referral_code': user_obj.referral_code,
                   'name': user_obj.name,
                   'email_id': user_obj.email
                   }
            status_code = status.HTTP_200_OK
            return msg, status_code

        elif max_attempts(user, 5):
            """if OTP max attempts exceeds, Resend OTP"""

            error_msg = VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED']
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            revoke = RevokeOTP(user.phone_number, error_msg)
            msg = revoke.update()
            return msg, status_code
        elif expired(user):
            """if OTP is expired, Resend OTP"""

            error_msg = VALIDATION_ERROR_MESSAGES['OTP_EXPIRED']
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            revoke = RevokeOTP(user.phone_number, error_msg)
            msg = revoke.update()
            return msg, status_code

    else:
        """if OTP doesn't matched with Registered OTP"""

        if max_attempts(user, 5):
            """if OTP max attempts exceeds, Resend OTP"""

            error_msg = VALIDATION_ERROR_MESSAGES['OTP_ATTEMPTS_EXCEEDED']
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            revoke = RevokeOTP(user.phone_number, error_msg)
            msg = revoke.update()
            return msg, status_code
        elif expired(user):
            """if OTP is expired, Resend OTP"""

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
        """Update OTP & Send to User"""

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
        msg = {'is_success': False,
               'message': VALIDATION_ERROR_MESSAGES['OTP_EXPIRED_GENERATE_AGAIN'],
               'response_data': None}
        return msg
