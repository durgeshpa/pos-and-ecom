from __future__ import unicode_literals
import logging
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from retailer_backend.messages import *
from django.utils.crypto import get_random_string
from django.db import transaction

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from global_config.models import GlobalConfig
from accounts.models import User
from marketing.sms import SendSms


class MLMUser(models.Model):
    """
    This model will be used to store the details of a User by their phone_number, referral_code
    """
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=70, blank=True, null=True, unique=True)
    referral_code = models.CharField(max_length=300, blank=True, null=True, unique=True)
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

    @staticmethod
    def authenticate(auth):
        try:
            auth_token = auth.split(" ")[1] if auth else ''
            if auth_token == '':
                return 'Invalid token header. No credentials provided.'
            token = Token.objects.get(token=auth_token)
            user = token.user
            return user
        except:
            return 'Invalid Token.'

    def save(self, *args, **kwargs):
        if self.email is not None and self.email.strip() == '':
            self.email = None
        super(MLMUser, self).save(*args, **kwargs)


@receiver(pre_save, sender=MLMUser)
def generate_referral_code(sender, instance=None, created=False, **kwargs):
    if not instance.referral_code:
        instance.referral_code = str(uuid.uuid4()).split('-')[-1][:6].upper()


class PhoneOTP(models.Model):
    """
       This model will be used to store the details of a User by their phone_number, otp
    """
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message=VALIDATION_ERROR_MESSAGES['INVALID_MOBILE_NUMBER'])
    phone_number = models.CharField(validators=[phone_regex], max_length=10, blank=False)
    otp = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_in = models.IntegerField(default=300)  # in seconds
    created_at = models.DateTimeField(default=timezone.now)
    last_otp = models.DateTimeField(default=timezone.now)
    resend_in = models.IntegerField(default=getattr(settings, 'OTP_RESEND_IN', 30))  # in seconds

    class Meta:
        verbose_name = "Phone OTP"

    def __str__(self):
        return "{} - {}".format(self.phone_number, self.otp)

    @classmethod
    def create_otp_for_number(cls, number):
        otp = cls.generate_otp(length=getattr(settings, 'OTP_LENGTH', 6),
                               allowed_chars=getattr(settings, 'OTP_CHARS', '0123456789')
                               )
        phone_otp = PhoneOTP.objects.create(phone_number=number, otp=otp)
        return phone_otp, otp

    @classmethod
    def update_otp_for_number(cls, number):
        otp = cls.generate_otp(length=getattr(settings, 'OTP_LENGTH', 6),
                               allowed_chars=getattr(settings, 'OTP_CHARS', '0123456789')
                               )
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


class Referral(models.Model):
    """
    This model will be used to store the parent and child referral mapping details
    """

    referral_by = models.ForeignKey(MLMUser, related_name="referral_by", on_delete=models.CASCADE, null=True,
                                    blank=True)
    referral_to = models.ForeignKey(MLMUser, related_name="referral_to", on_delete=models.CASCADE, null=True,
                                    blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def generate_unique_referral_code(cls):
        """
        This Method generate an unique referral code by using UUID(Universal Unique Identifier),
        a python library which helps in generating random object
        """
        try:
            unique_referral_code = str(uuid.uuid4()).split('-')[-1][:6].upper()
            return unique_referral_code
        except Exception as e:
            error_logger.info("Something Went wrong while saving the referral_code in UserModel " + str(e))

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
            error_logger.info(
                "Something Went wrong while saving the Parent and Child Referrals in Referral Model " + str(e))


class RewardPoint(models.Model):
    user = models.ForeignKey(MLMUser, related_name="reward_user", on_delete=models.CASCADE, null=True, blank=True)
    direct_users = models.IntegerField(default=0)
    indirect_users = models.IntegerField(default=0)
    direct_earned = models.IntegerField(default=0)
    indirect_earned = models.IntegerField(default=0)
    points_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Rewards Dashboard"

    @staticmethod
    def welcome_reward(user, referred=0):
        if RewardPoint.objects.filter(user=user).exists():
            return ''
        try:
            conf_obj = GlobalConfig.objects.get(key='welcome_reward_points_referral')
            on_referral_points = int(conf_obj.value)
        except:
            on_referral_points = 10

        points = on_referral_points if referred else int(on_referral_points / 2)
        with transaction.atomic():
            reward_obj, created = RewardPoint.objects.get_or_create(user=user)
            reward_obj.direct_earned += points
            reward_obj.save()
            RewardLog.objects.create(user=user, transaction_type='welcome_reward', transaction_id=user.id,
                                     points=points)
        try:
            conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
            used_reward_factor = int(conf_obj.value)
        except:
            used_reward_factor = 4
        message = SendSms(phone=user.phone_number,
                          body="Welcome to rewards.peppertap.in %s points are added to your account. Get Rs %s"
                               " off on next purchase. Login and share your referral code:%s with friends and win more points."
                               % (points, int(points / used_reward_factor), user.referral_code))

        message.send()

    def __str__(self):
        return "Reward Points For - {}".format(self.user)


class Token(models.Model):
    """
    This model will be used to store the user id & user token
    """
    user = models.ForeignKey(MLMUser, on_delete=models.CASCADE)
    token = models.UUIDField()

    def __str__(self):
        return "{} - {}".format(self.user, self.token)


class Profile(models.Model):
    user = models.OneToOneField(MLMUser, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics', blank=True)

    def __str__(self):
        return f'{self.user.phone_number} Profile'

    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    post_save.connect(create_user_profile, sender=MLMUser)


class RewardLog(models.Model):
    TRANSACTION_CHOICES = (
        ('welcome_reward', "Welcome Reward"),
        ('used_reward', 'Used Reward'),
        ('direct_reward', 'Direct Reward'),
        ('indirect_reward', 'Indirect Reward')
    )
    user = models.ForeignKey(MLMUser, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=25, null=True, blank=True, choices=TRANSACTION_CHOICES)
    transaction_id = models.CharField(max_length=25, null=True, blank=True)
    points = models.IntegerField(default=0)
    discount = models.IntegerField(null=True, blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} - {}".format(self.user, self.transaction_type)


