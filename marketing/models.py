from __future__ import unicode_literals

import logging
import uuid

from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from retailer_backend.messages import *

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


class MLMUser(models.Model):
    """
    This model will be used to store the details of a User by their phone_number, referral_code
    """
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=70, blank=True, null=True, unique=True)
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
    """
    This model will be used to store the parent and child referral mapping details
    """
    referral_by = models.ForeignKey(MLMUser, related_name="referral_by", on_delete=models.CASCADE, null=True, blank=True)
    referral_to = models.ForeignKey(MLMUser, related_name="referral_to", on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def generate_unique_referral_code(cls, phone_number):
        """
        This Method generate an unique referral code by using UUID(Universal Unique Identifier),
        a python library which helps in generating random object
        """
        unique_referral_code = str(uuid.uuid4()).split('-')[-1]
        try:
            # MLMUserModel.objects.filter(phone_number=phone_number).update(referral_code=unique_referral_code)
            return unique_referral_code
        except Exception as e:
            info_logger.info("Something Went wrong while saving the referral_code in UserModel " + str(e))

    @classmethod
    def store_parent_referral_user(cls, parent_referral_code, child_referral_code):
        """
        parent_referral_code: Referral code of Parent
        child_referral_code: Referral code of Child
        This method will create an entry in REFERRAL Table of the Parent user, who is referring to the Child user
        """
        try:
            parentReferralCode = MLMUser.objects.filter(referral_code=parent_referral_code).values_list('id')
            childReferralCode = MLMUser.objects.filter(referral_code=child_referral_code).values_list('id')
            if parentReferralCode[0][0]:
                if childReferralCode[0][0]:
                    Referral.objects.create(referral_to_id=childReferralCode[0][0],
                                            referral_by_id=parentReferralCode[0][0])
        except Exception as e:
            info_logger.info(
                "Something Went wrong while saving the Parent and Child Referrals in Referral Model " + str(e))


class RewardPoint(models.Model):
    reward_user = models.ForeignKey(MLMUser, related_name="reward_user", on_delete=models.CASCADE, null=True, blank=True)
    direct_reward_point_earned = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    indirect_reward_point_earned = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    total_reward_point_earned = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    reward_point_used = models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)