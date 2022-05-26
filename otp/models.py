
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator
from django.utils.crypto import get_random_string
from django.utils import timezone

from retailer_backend.messages import *

import logging
error_logger = logging.getLogger('otp_issue_log_file')

info_logger = logging.getLogger('file-info')
debug_logger = logging.getLogger('file-debug')


class PhoneOTP(models.Model):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message=VALIDATION_ERROR_MESSAGES['INVALID_MOBILE_NUMBER'])
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False)
    otp = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_in = models.IntegerField(default=getattr(settings, 'OTP_EXPIRES_IN', 300))
    blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    modified_at = models.DateTimeField(auto_now=True)
    last_otp = models.DateTimeField(default=timezone.now)
    resend_in = models.IntegerField(default=getattr(settings, 'OTP_RESEND_IN', 30))

    class Meta:
        verbose_name = "Phone OTP"

    def __str__(self):
        return "{} - {}".format(self.phone_number, self.otp)

    @classmethod
    def create_otp_for_number(cls, number):
        try:
            otp = cls.generate_otp(length=getattr(settings, 'OTP_LENGTH', 6),
                                   allowed_chars=getattr(settings, 'OTP_CHARS', '0123456789'))
            info_logger.info(f"create_otp_for_number|otp {otp} for number {number}")
        except Exception as e:
            otp = '895674'
            error_logger.error(e)
            info_logger.error(f"create_otp_for_number|Error while creating otp for number {number}|Msg: {e}")
        phone_otp = PhoneOTP.objects.create(phone_number=number, otp=otp)
        info_logger.info(f"create_otp_for_number|{number} - {otp}|phone_otp {phone_otp}")
        return phone_otp, otp

    @classmethod
    def update_otp_for_number(cls, number):
        try:
            otp = cls.generate_otp(length=getattr(settings, 'OTP_LENGTH', 6),
                                   allowed_chars=getattr(settings, 'OTP_CHARS', '0123456789'))
            info_logger.error(f"update_otp_for_number|Generating otp {otp}")
        except Exception as e:
            otp = '895675'
            error_logger.error(e)
            info_logger.error(f"update_otp_for_number|Error while updating otp for number {number}|Msg: {e}")
        user = PhoneOTP.objects.filter(phone_number=number).last()
        user.otp = otp
        user.attempts = 0
        user.created_at = timezone.now()
        user.save()
        info_logger.info(f"update_otp_for_number|user {user} & otp {otp}")
        return user, otp

    @classmethod
    def generate_otp(cls, length=6, allowed_chars='0123456789'):
        try:
            otp = get_random_string(length, allowed_chars)
            if not otp:
                otp = '895673'
            info_logger.error(f"generate_otp|generated otp {otp}")
        except Exception as e:
            otp = '895672'
            error_logger.error(e)
            info_logger.error(f"generate_otp|Error while generating otp|Msg: {e}")
        return otp
