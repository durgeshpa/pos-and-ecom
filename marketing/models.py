from __future__ import unicode_literals
import logging
import uuid

from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from django.db import models, transaction
from django.core.validators import RegexValidator
from django.core.exceptions import ObjectDoesNotExist

from retailer_backend.messages import *
from global_config.models import GlobalConfig
from accounts.models import User

from .sms import SendSms

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class MLMUser(models.Model):
    # TODO: Remove This Model After Data Migration - Replaced By Default User Model
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=70, blank=True, null=True, unique=True)
    referral_code = models.CharField(max_length=300, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    Active_Status = 1
    Inactive_Status = 0
    STATUS_CHOICES = (
        (Active_Status, 'Active'),
        (Inactive_Status, 'Inactive'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=Inactive_Status)


class ReferralCode(models.Model):
    """
        Auto Generated Referral Codes For Users
    """
    user = models.OneToOneField(get_user_model(), related_name='referral_code_user', on_delete=models.CASCADE)
    referral_code = models.CharField(max_length=300, blank=True, null=True, unique=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def generate_user_referral_code(cls, user, added_by):
        """
            This Method Will Generate Referral Code & Map To User
        """
        user_referral_code = str(uuid.uuid4()).split('-')[-1][:6].upper()
        while ReferralCode.objects.filter(referral_code=user_referral_code).exists():
            user_referral_code = str(uuid.uuid4()).split('-')[-1][:6].upper()
        ReferralCode.objects.create(user=user, referral_code=user_referral_code, added_by=added_by)
        Profile.objects.get_or_create(profile_user=user)
        return user_referral_code

    @classmethod
    def register_user_for_mlm(cls, user, added_by, used_referral_code=None):
        with transaction.atomic():
            if not ReferralCode.is_marketing_user(user):
                user_referral_code = ReferralCode.generate_user_referral_code(user, added_by)
                if used_referral_code:
                    Referral.store_parent_referral_user(used_referral_code, user_referral_code)
                RewardPoint.welcome_reward(user, used_referral_code, added_by)

    @classmethod
    def is_marketing_user(cls, user):
        return True if ReferralCode.objects.filter(user=user).exists() else False

    @classmethod
    def user_referral_code(cls, user):
        ref_code_obj = ReferralCode.objects.filter(user=user).last()
        return ref_code_obj.referral_code if ref_code_obj else None

    def __str__(self):
        return ''

    class Meta:
        verbose_name = "   User"


class Profile(models.Model):
    """
        Mlm User Profile
    """
    user = models.OneToOneField(MLMUser, on_delete=models.CASCADE, null=True, blank=True)
    profile_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile', null=True, blank=True)
    image = models.ImageField(upload_to='profile_pics', blank=True)

    def __str__(self):
        return f'{self.user.phone_number} Profile'


class Referral(models.Model):
    """
    Parent - Child Referral Mapping
    """
    referral_by = models.ForeignKey(MLMUser, related_name="referral_by", on_delete=models.CASCADE, null=True, blank=True)
    referral_to = models.ForeignKey(MLMUser, related_name="referral_to", on_delete=models.CASCADE, null=True, blank=True)
    referral_by_user = models.ForeignKey(User, related_name="referral_by_user", on_delete=models.CASCADE, null=True, blank=True)
    referral_to_user = models.ForeignKey(User, related_name="referral_to_user", on_delete=models.CASCADE, null=True, blank=True)
    user_count_considered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def store_parent_referral_user(cls, parent_referral_code, child_referral_code):
        """
        Create Referral Mapping of the Parent User (Who Is Referring The Child User) And Child User
        """
        parent_ref_obj = ReferralCode.objects.filter(referral_code=parent_referral_code).last()
        child_ref_obj = ReferralCode.objects.filter(referral_code=child_referral_code).last()
        if parent_ref_obj and child_ref_obj and not Referral.objects.filter(referral_to_user=child_ref_obj.user).exists():
            Referral.objects.create(referral_to_user=child_ref_obj.user, referral_by_user=parent_ref_obj.user)


class RewardPoint(models.Model):
    """
        All Reward Credited/Used Details Of Any User
    """
    user = models.ForeignKey(MLMUser, related_name="reward_user", on_delete=models.CASCADE, null=True, blank=True)
    reward_user = models.OneToOneField(User, related_name="reward_user_mlm", on_delete=models.CASCADE, null=True, blank=True)
    direct_users = models.PositiveIntegerField(default=0)
    indirect_users = models.PositiveIntegerField(default=0)
    direct_earned = models.PositiveIntegerField(default=0)
    indirect_earned = models.PositiveIntegerField(default=0)
    points_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "  Rewards Dashboard"

    @staticmethod
    def welcome_reward(user, referred=None, changed_by=None):
        """
            Reward On User Registration
        """
        # Check existing user
        if RewardPoint.objects.filter(reward_user=user).exists():
            return False
        # Get Welcome Reward Points From Config
        try:
            conf_obj = GlobalConfig.objects.get(key='welcome_reward_points_referral')
            on_referral_points = int(conf_obj.value)
        except ObjectDoesNotExist:
            on_referral_points = 10
        # Half points if user is not referred
        points = on_referral_points if referred else int(on_referral_points / 2)
        # Create Reward Point And Log
        with transaction.atomic():
            reward_obj, created = RewardPoint.objects.get_or_create(reward_user=user)
            reward_obj.direct_earned += points
            reward_obj.save()
            RewardLog.objects.create(reward_user=user, transaction_type='welcome_reward', transaction_id=user.id,
                                     points=points, changed_by=changed_by)
        # Send SMS To User For Discount That Can be Availed Using Welcome Rewards credited
        try:
            conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
            used_reward_factor = int(conf_obj.value)
        except ObjectDoesNotExist:
            used_reward_factor = 4
        referral_code_obj = ReferralCode.objects.filter(user=user).last()
        referral_code = referral_code_obj.referral_code if referral_code_obj else ''
        message = SendSms(phone=user.phone_number,
                          body="Welcome to rewards.peppertap.in %s points are added to your account. Get Rs %s off on"
                               " next purchase. Login and share your referral code:%s with friends and win more points."
                               % (points, int(points / used_reward_factor), referral_code))
        message.send()

    @property
    def redeemable_points(self):
        return max(self.direct_earned + self.indirect_earned - self.points_used, 0)

    @property
    def redeemable_discount(self):
        reward_factor = int(GlobalConfig.objects.get(key='used_reward_factor').value)
        return str(round(self.redeemable_points / reward_factor, 2)).rstrip('0').rstrip('.')

    def __str__(self):
        return "Reward Points For - {}".format(self.reward_user)


class RewardLog(models.Model):
    """
        Logs For Credited/Used Rewards Transactions
    """
    TRANSACTION_CHOICES = (
        ('welcome_reward', "Welcome Credit"),
        ('order_credit', 'Order Credit'),
        ('order_debit', 'Order Debit'),
        ('order_return_credit', 'Order Return Credit'),
        ('order_return_debit', 'Order Return Debit'),
        ('order_cancel_credit', 'Order Cancel Credit'),
        ('order_cancel_debit', 'Order Cancel Debit'),
        ('order_indirect_credit', 'Order Indirect Credit'),
        ('used_reward', 'Purchase Debit (Admin)'),
        ('direct_reward', 'Hdpos Sales - Direct Credit'),
        ('indirect_reward', 'Hdpos Sales - Indirect Credit'),
        ('purchase_reward', 'Hdpos Sales - Purchase Credit'),
    )
    user = models.ForeignKey(MLMUser, on_delete=models.CASCADE, null=True, blank=True)
    reward_user = models.ForeignKey(User, related_name='reward_log_user', on_delete=models.CASCADE, null=True, blank=True)
    transaction_type = models.CharField(max_length=25, null=True, blank=True, choices=TRANSACTION_CHOICES)
    transaction_id = models.CharField(max_length=25, null=True, blank=True)
    points = models.IntegerField(default=0)
    discount = models.IntegerField(null=True, blank=True, default=0)
    changed_by = models.ForeignKey(User, related_name='changed_by', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} - {}".format(self.user, self.transaction_type)

    class Meta:
        verbose_name_plural = " Reward Logs"


class PhoneOTP(models.Model):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message=VALIDATION_ERROR_MESSAGES['INVALID_MOBILE_NUMBER'])
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False)
    otp = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_in = models.IntegerField(default=300)  # in seconds
    created_at = models.DateTimeField(default=timezone.now)
    last_otp = models.DateTimeField(default=timezone.now)
    resend_in = models.IntegerField(default=getattr(settings, 'OTP_RESEND_IN', 30))  # in seconds


class Token(models.Model):
    user = models.ForeignKey(MLMUser, on_delete=models.CASCADE)
    token = models.UUIDField()
