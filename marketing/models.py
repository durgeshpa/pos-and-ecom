from __future__ import unicode_literals
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from retailer_backend.messages import *


class MLMUser(models.Model):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False, unique=True)
    referral_code = models.CharField(max_length=300, blank=True, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.phone_number


class PhoneOTP(models.Model):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message=VALIDATION_ERROR_MESSAGES['INVALID_MOBILE_NUMBER'])
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False)
    otp = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_in = models.IntegerField(default=300)  #in seconds
    created_at = models.DateTimeField(default=timezone.now)
    last_otp = models.DateTimeField(default=timezone.now)
    resend_in = models.IntegerField(default=getattr(settings, 'OTP_RESEND_IN', 30))  #in seconds

    class Meta:
        verbose_name = "Phone OTP"

    def __str__(self):
        return "{} - {}".format(self.phone_number, self.otp)


class Referral(models.Model):
    referral_by = models.ForeignKey(MLMUser, related_name="referral_by", on_delete=models.CASCADE),
    referral_to = models.ForeignKey(MLMUser, related_name="referral_to", on_delete=models.CASCADE),
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class RewardPoint(models.Model):
    reward_user = models.ForeignKey(MLMUser, related_name="reward_user", on_delete=models.CASCADE),
    direct_reward_point_earned = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    indirect_reward_point_earned = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    total_reward_point_earned = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    reward_point_used = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

