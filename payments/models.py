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
from django.contrib.auth import get_user_model

from retailer_to_sp.models import Order, Shipment

User = get_user_model()
# Create your models here.

MAX_DISCOUNT_LIMIT = 20

CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
  )

PAYMENT_STATUS_CHOICES = (
    ('not_initiated', 'not_initiated'),
    ('initiated', 'initiated'),
    #('in_progress', 'in_progress'),
    ('cancelled', 'cancelled'),
    ('failure', 'failure'),
    ('completed', 'completed'), #successful
  )

ONLINE_PAYMENT_TYPE_CHOICES = (
    #('paytm', 'paytm'),
    ('upi', 'upi'),
    ('neft', 'neft'),
    ('imps', 'imps'),
    ('rtgs', 'rtgs'),
  )

ORDER_PAYMENT_STATUS_CHOICES = (
    ('not_initiated', 'not_initiated'),
    ('initiated', 'initiated'),
    ('completed', 'completed'),
  )

PAYMENT_PARTY_CHOICES = (
    ('bharatpe', 'bharatpe'),
  )

PAYMENT_TYPE_CHOICES = (
    ('prepaid', 'prepaid'),
    ('postpaid', 'postpaid'),
  )

ORDER_PAYMENT_TYPE_CHOICES = (
    ('prepaid', 'prepaid'),
    ('postpaid', 'postpaid'),
  )


DISCOUNT_TYPE_CHOICES = (
    ('new_user_discount', 'new_user_discount'),
    ('season_offer', 'season_offer'),
    ('loyal_user_offer', 'loyal_user_offer'),
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

# merge and create payment table : tbd: let it be same for now       
# field name : order_payment_or_shipment_payment

class OrderPayment(AbstractDateTime):
    # This class stores the payment information for the shipment
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    payment_type = models.CharField(max_length=255, choices=ORDER_PAYMENT_TYPE_CHOICES,null=True, blank=True)
    order = models.ForeignKey(Order, related_name='order_payment', on_delete=models.CASCADE) #order_id
    payment_status = models.CharField(max_length=255, choices=ORDER_PAYMENT_STATUS_CHOICES, null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, related_name='payment_created', null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(User, related_name='payment_updated', null=True, blank=True, on_delete=models.SET_NULL)

# create payment mode table
class ShipmentPayment(AbstractDateTime):
    # This class stores the payment information for the shipment
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    payment_type = models.CharField(max_length=255, choices=PAYMENT_TYPE_CHOICES,null=True, blank=True)
    shipment = models.ForeignKey(Shipment, unique=True, related_name='shipment_payment', on_delete=models.CASCADE) #shipment_id
    is_cash_payment = models.BooleanField(default=False)
    is_wallet_payment = models.BooleanField(default=False)
    is_credit_payment = models.BooleanField(default=False)
    is_credit_note = models.BooleanField(default=False)
    is_discount = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=255, null=True, blank=True)
    #collected_payment = models.DecimalField()
    due_date = models.DateTimeField(null=True, blank=True)
    #received_by = models.ForeignKey(User, related_name='payment_boy', on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, related_name='payment_created_by', null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(User, related_name='payment_updated_by', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.shipment.id)

    def get_parent_or_self(self,obj):
        pass
        #return brand.id



class CashPayment(AbstractDateTime):
    # This method stores the info about the cash payment
    payment = models.ForeignKey(ShipmentPayment, unique=True, related_name='cash_payment', on_delete=models.CASCADE)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')
    description = models.CharField(max_length=255, null=True, blank=True)


class CreditPayment(AbstractDateTime):
    # This method stores the credit payment: third party details, payment status
    payment = models.ForeignKey(ShipmentPayment, related_name='credit_payment', on_delete=models.CASCADE)
    reference_no = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    payment_party_name = models.CharField(max_length=255, choices=PAYMENT_PARTY_CHOICES, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')    
    payment_status = models.CharField(max_length=255, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    initiated_time = models.DateTimeField(null=True, blank=True)
    timeout_time = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, related_name='credit_payment_boy', on_delete=models.CASCADE)


class WalletPayment(AbstractDateTime):
    # This method stores the wallet payment: third party details, payment status
    payment = models.ForeignKey(ShipmentPayment, related_name='wallet_payment', on_delete=models.CASCADE)
    reference_no = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')    
    payment_status = models.CharField(max_length=255, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    initiated_time = models.DateTimeField(null=True, blank=True)
    timeout_time = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, related_name='wallet_payment_boy', on_delete=models.CASCADE)


class OnlinePayment(AbstractDateTime):
    # This method stores the credit payment: third party details, payment status
    payment = models.ForeignKey(ShipmentPayment, related_name='online_payment', on_delete=models.CASCADE)
    reference_no = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    online_payment_type = models.CharField(max_length=255, choices=ONLINE_PAYMENT_TYPE_CHOICES, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')    
    payment_status = models.CharField(max_length=255, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    initiated_time = models.DateTimeField(null=True, blank=True)
    timeout_time = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, related_name='online_payment_boy', on_delete=models.CASCADE)



class Offer(AbstractDateTime):
    # This method stores the discount description for a payment
    offer_id = models.CharField(max_length=255, unique=True)
    offer_type = models.CharField(max_length=255, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True)
    offer_amount = models.DecimalField(max_digits=6, decimal_places=4, default='0.0000')
    offer_percentage = models.FloatField(default=0.0)
    offer_start_at = models.DateTimeField(null=True,blank=True)
    offer_end_at = models.DateTimeField(null=True,blank=True)
    status = models.BooleanField(default=True)
    offer_limitation = models.CharField(max_length=255, choices=OFFER_LIMITATION_CHOICES, default='per_shop')

    def __str__(self):
        return self.offer_id

    class Meta:
        verbose_name = _("Offer")
        verbose_name_plural = _("Offers")