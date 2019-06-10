import datetime, csv, codecs, re

from django.db import models
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from django.db.models import Case, CharField, Value, When, F


# Create your models here.

MAX_DISCOUNT_LIMIT = 20

CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
  )

PAYMENT_STATUS_CHOICES = (
    ('not_initiated', 'not_initiated'),
    ('initiated', 'initiated'),
    ('in_progress', 'in_progress'),
    ('cancelled', 'cancelled'),
    ('failure', 'failure'),
    ('completed', 'completed'),
  )

PAYMENT_PARTY_CHOICES = (
    ('bharatpe', 'bharatpe'),
  )

PAYMENT_TYPE_CHOICES = (
    ('prepaid', 'prepaid'),
    ('postpaid', 'postpaid'),
  )

DISCOUNT_TYPE_CHOICES = (
    ('new_user_discount', 'new_user_discount'),
    ('season_offer', 'season_offer'),
    ('loyal_user_offer', 'loyal_user_offer')
    ('lucky_user_offer', 'lucky_user_offer')
  )


OFFER_LIMITATION_CHOICES = (
    ('per_shop', 'new_user_discount'),
    ('per_day', 'per_day'),
    ('per_count', 'per_count'),
    ('per_shop_count', 'per_shop_count'),
    ('per_day_count', 'per_day_count'),
    ('unlimited', 'unlimited')
  )


class AbstractDateTime(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Payment(AbstractDateTime):
    # This class stores the payment information for the shipment
    shop = models.ForeignKey(Shop, related_name='shop_payment', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True, blank=True)
    payment_id = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    payment_type = models.CharField(max_length=255, choices=PAYMENT_TYPE_CHOICES,null=True, blank=True)
    shipment = models.ForeignKey(Shipment, related_name='shipment_payment', on_delete=models.CASCADE)
    cash_payment = models.BooleanField(default=False)
    wallet_payment = models.BooleanField(default=False)
    credit_payment = models.BooleanField(default=False)
    credit_note = models.BooleanField(default=False)
    discount = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=255, null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(User, related_name='payment_boy', on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, related_name='payment_created_by', on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(User, related_name='payment_updated_by', on_delete=models.SET_NULL)

    def __str__(self):
        return self.vendor_name

    def get_parent_or_self(self,obj):
        pass
        #return brand.id


class CashPayment(AbstractDateTime):
    # This method stores the info about the cash payment
    payment = models.ForeignKey(Payment, related_name='cash_payment', on_delete=models.CASCADE)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    description = models.CharField(max_length=255, null=True, blank=True)


class CreditPayment(AbstractDateTime):
    # This method stores the credit payment: third party details, payment status
    payment = models.ForeignKey(Payment, related_name='credit_payment', on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    payment_party_name = models.CharField(max_length=255, choices=PAYMENT_PARTY_CHOICES, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')    
    payment_status = models.CharField(max_length=255, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    initiated_time = models.DateTimeField(null=True, blank=True)
    timeout_time = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, related_name='payment_boy', on_delete=models.CASCADE)


class WalletPayment(AbstractDateTime):
    # This method stores the wallet payment: third party details, payment status
    payment = models.ForeignKey(Payment, related_name='wallet_payment', on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')    
    payment_status = models.CharField(max_length=255, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    initiated_time = models.DateTimeField(null=True, blank=True)
    timeout_time = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, related_name='payment_boy', on_delete=models.CASCADE)


class Offer(AbstractDateTime):
    # This method stores the discount description for a payment
    offer_id = models.CharField(max_length=255, unique=True)
    offer_type = models.CharField(max_length=255, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True)
    offer_amount = models.DecimalField(min=0, max=MAX_DISCOUNT_LIMIT, max_digits=6, decimal_places=4, default='0.0000')
    offer_percentage = models.FloatField(default=0)
    offer_start_at = models.DateTimeField(null=True,blank=True)
    offer_end_at = models.DateTimeField(null=True,blank=True)
    status = models.BooleanField(default=True)
    offer_limitation = models.CharField(max_length=255, choices=OFFER_LIMITATION_CHOICES, default='per_shop')

    def __str__(self):
        return self.offer_id

    class Meta:
        verbose_name = _("Offer")
        verbose_name_plural = _("Offers")



