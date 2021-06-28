from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator
from django.utils.crypto import get_random_string
from django.utils import timezone

from retailer_backend.messages import *


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
        otp = cls.generate_otp(length=getattr(settings, 'OTP_LENGTH', 6),
                               allowed_chars=getattr(settings, 'OTP_CHARS', '0123456789'))
        phone_otp = PhoneOTP.objects.create(phone_number=number, otp=otp)
        return phone_otp, otp

    @classmethod
    def update_otp_for_number(cls, number):
        otp = cls.generate_otp(length=getattr(settings, 'OTP_LENGTH', 6),
                               allowed_chars=getattr(settings, 'OTP_CHARS', '0123456789'))
        user = PhoneOTP.objects.filter(phone_number=number).last()
        user.otp = otp
        user.attempts = 0
        user.created_at = timezone.now()
        user.save()
        return user, otp

    @classmethod
    def generate_otp(cls, length=6, allowed_chars='0123456789'):
        otp = get_random_string(length, allowed_chars)
        return otp
