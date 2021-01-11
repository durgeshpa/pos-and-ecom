from __future__ import unicode_literals
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from retailer_backend.messages import *

import uuid
from django.dispatch import receiver
from django.db.models.signals import pre_save
class MLMUser(models.Model):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=70,blank=True, null= True, unique= True)
    referral_code = models.CharField(max_length=300, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    """(Status choice)"""
    Active_Status = 1
    Inactive_Status = 0
    STATUS_CHOICES = (
        (Active_Status, 'Active'),
        (Inactive_Status, 'Inactive'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=Inactive_Status)

    def __str__(self):
        return self.phone_number

    def save(self, *args, **kwargs):
        if self.email is not None and self.email.strip() == '':
            self.email = None
        super().save(*args, **kwargs)


@receiver(pre_save, sender=MLMUser)
def generate_referral_code(sender, instance=None, created=False, **kwargs):
    if not instance.referral_code: # check for status also ????
        instance.referral_code = str(uuid.uuid4()).split('-')[-1]


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
    reward_status = models.IntegerField(choices=((0, 'not considered'), (1, 'considered')), default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class RewardPoint(models.Model):
    user = models.ForeignKey(MLMUser, related_name="reward_user", on_delete=models.CASCADE),
    direct_users = models.IntegerField(default=0)
    indirect_users = models.IntegerField(default=0)
    direct_earned = models.DecimalField(max_digits=10, decimal_places=2, default='0.00')
    indirect_earned = models.DecimalField(max_digits=10, decimal_places=2, default='0.00')
    points_used = models.DecimalField(max_digits=10, decimal_places=2, default='0.00')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
