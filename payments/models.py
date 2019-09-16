import sys
import traceback
import datetime, csv, codecs, re

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from django.db.models import Case, CharField, Value, When, F, Sum
from django.contrib.auth import get_user_model

from accounts.models import UserWithName
from retailer_to_sp.models import Order, Shipment, OrderedProduct


User = get_user_model()
# Create your models here.

MAX_DISCOUNT_LIMIT = 20

CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
  )

PAYMENT_MODE_NAME = (
    ('cash_payment', 'Cash Payment'),
    ('online_payment', 'Online Payment'),
    ('credit_payment', 'Credit Payment'),
    ('wallet_payment', 'Wallet Payment')
  )

PAYMENT_STATUS_CHOICES = (
    ('not_initiated', 'not_initiated'),
    ('initiated', 'initiated'),
    #('in_progress', 'in_progress'),
    ('cancelled', 'cancelled'),
    ('failure', 'failure'),
    ('completed', 'completed'), #successful
  )

PAYMENT_APPROVAL_STATUS_CHOICES = (
    ('pending_approval', 'pending_approval'),
    ('approved_and_verified', 'approved_and_verified'),
    ('disputed', 'disputed'),
    ('rejected', 'rejected'),
  )


FINAL_PAYMENT_STATUS_CHOICES = (
    ('PENDING', 'Pending'),
    ('PARTIALLY_PAID', 'Partially_paid'),
    ('PAID', 'Paid'),
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


#if prepaid then its against order, else shipment
# replace order with user
class Payment(AbstractDateTime):
    order = models.ManyToManyField(Order, through="OrderPayment", related_name='order_payment_data')
    #order = models.ForeignKey(Order, related_name='order_payment_data', on_delete=models.CASCADE)
    # payment description
    description = models.CharField(max_length=100, null=True, blank=True)
    reference_no = models.CharField(max_length=50, null=True, blank=True)
    paid_amount = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    payment_mode_name = models.CharField(max_length=50, choices=PAYMENT_MODE_NAME, default="cash_payment")
    prepaid_or_postpaid = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES,null=True, blank=True)
    # for finance team
    payment_approval_status = models.CharField(max_length=50, choices=PAYMENT_APPROVAL_STATUS_CHOICES, default="pending_approval",null=True, blank=True)
    payment_received = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    is_payment_approved = models.BooleanField(default=False)
    mark_as_settled = models.BooleanField(default=False)

    # for payment processing
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    online_payment_type = models.CharField(max_length=50, choices=ONLINE_PAYMENT_TYPE_CHOICES, null=True, blank=True)
    initiated_time = models.DateTimeField(null=True, blank=True)
    timeout_time = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(UserWithName, related_name='payment_boy',
        null=True, blank=True, on_delete=models.SET_NULL)
    approved_by = models.ForeignKey(UserWithName, related_name='payment_approver',
        null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{} -> {}".format(
            self.payment_mode_name,
            self.paid_amount
        )

    def clean(self):
        if self.payment_mode_name != "cash_payment" and not self.reference_no:
            raise ValidationError('Referece number is required.')
        if self.reference_no and not re.match("^[a-zA-Z0-9_]*$", self.reference_no):
                raise ValidationError('Referece number can not have special character.')
        if self.payment_mode_name == "online_payment" and not self.online_payment_type:
            raise ValidationError('Online payment type is required.')
        super(Payment, self).clean()

    def save(self, *args, **kwargs):
        if self.is_payment_approved:
            if self.payment_received >= self.paid_amount:
                self.payment_approval_status = "approved_and_verified"
            elif self.payment_received == 0.0000:
                self.payment_approval_status = "rejected"
            elif self.payment_received < self.paid_amount:
                self.payment_approval_status = "disputed"            

        # create entry to edit shipment payment
        super().save(*args, **kwargs)
        # assuming that a postpaid order payment has one shipment payment
        # shipment_payment = ShipmentPayment.objects.filter(parent_payment=self) 

        # if self.prepaid_or_postpaid == "postpaid" and shipment_payment.exists():
        #     shipment_payment1 = shipment_payment[0]
        #     shipment_payment1.paid_amount = self.paid_amount
        #     shipment_payment1.save()


class OrderPayment(AbstractDateTime):
    # This class stores the payment information for the shipment
    description = models.CharField(max_length=50, null=True, blank=True)
    order = models.ForeignKey(Order, related_name='order_payment', on_delete=models.CASCADE) #shipment_id
    parent_payment = models.ForeignKey(Payment, 
       related_name='parent_payment_order', on_delete=models.CASCADE)
    created_by = models.ForeignKey(UserWithName, related_name='order_payment_created_by', null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(UserWithName, related_name='order_payment_updated_by', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{}->{},{}".format(
            str(self.order), 
            str(self.parent_payment.payment_mode_name), 
            str(self.parent_payment.paid_amount))

    @property
    def payment_utilised(self):
        payment = self.shipment_order_payment.all()
        if payment.exists():
            payment_data = payment.aggregate(Sum('paid_amount')) #annotate(sum_paid_amount=Sum('paid_amount')) 

            if payment_data:
                return payment_data['paid_amount__sum'] #sum_paid_amount
        else:
            return 0
        
    class Meta:
        unique_together = (("order", "parent_payment"),)


# create payment mode table shipment payment mapping
class ShipmentPayment(AbstractDateTime):
    # This class stores the payment information for the shipment
    description = models.CharField(max_length=50, null=True, blank=True)
    shipment = models.ForeignKey(OrderedProduct, related_name='shipment_payment', on_delete=models.CASCADE) #shipment_id
    parent_order_payment = models.ForeignKey(OrderPayment, 
       related_name='shipment_order_payment', on_delete=models.CASCADE)
    parent_payment = models.ForeignKey(Payment, 
       related_name='shipment_payment', on_delete=models.CASCADE, null=True, blank=True)
    paid_amount = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    created_by = models.ForeignKey(User, related_name='payment_created_by', null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(User, related_name='payment_updated_by', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.shipment.id)

    def get_parent_or_self(self,obj):
        pass
        #return brand.id

    def clean(self):
        # check the parent payment amount
        if self.parent_order_payment.payment_utilised + self.paid_amount > self.parent_order_payment.parent_payment.paid_amount:
            error_msg = "Maximum amount to be utilised from parent payment is " + str(self.parent_order_payment.parent_payment.paid_amount - self.parent_order_payment.payment_utilised)
            raise ValidationError(_(error_msg),)
        
    class Meta:
        unique_together = (("parent_order_payment", "shipment"),)


class OrderPaymentStatus(AbstractDateTime):
    # This class stores the payment information for the shipment
    description = models.CharField(max_length=50, null=True, blank=True)
    payment_status = models.CharField(max_length=50,choices=FINAL_PAYMENT_STATUS_CHOICES, null=True, blank=True)
    order = models.ForeignKey(Order, related_name='order_payment_status', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.order.id), str(self.payment_status)


        
class ShipmentPaymentStatus(AbstractDateTime):
    # This class stores the payment information for the shipment
    description = models.CharField(max_length=50, null=True, blank=True)
    payment_status = models.CharField(max_length=50,choices=FINAL_PAYMENT_STATUS_CHOICES, null=True, blank=True)
    shipment = models.ForeignKey(Shipment, related_name='shipment_payment_status', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.shipment.id), str(self.payment_status)


class PaymentMode(models.Model):
    payment_mode_name = models.CharField(max_length=50, choices=PAYMENT_MODE_NAME, null=True, blank=True)
    status = models.BooleanField(default=True)
    #payment = models.ForeignKey(ShipmentPayment, related_name='payment_mode', on_delete=models.CASCADE)

    def __str__(self):
        return self.payment_mode_name #,str(self.payment.id), self.payment_mode_name

    # class Meta:
    #     unique_together = (('payment', 'payment_mode_name'),)


class CashPayment(AbstractDateTime):
    # This method stores the info about the cash payment
    #payment = models.OneToOneField(ShipmentPayment, related_name='cash_payment', on_delete=models.CASCADE)
    #payment_reference_number = models.CharField(max_length=50, unique=True)
    payment_parent = models.OneToOneField(Payment, related_name='payment_cash', on_delete=models.CASCADE)
    #paid_amount = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    description = models.CharField(max_length=50, null=True, blank=True)


class CreditPayment(AbstractDateTime):
    # This method stores the credit payment: third party details, payment status
    #payment = models.ForeignKey(ShipmentPayment, related_name='credit_payment', on_delete=models.CASCADE)
    payment_parent = models.OneToOneField(Payment, related_name='payment_credit', on_delete=models.CASCADE)
    
    #payment_reference_number = models.CharField(max_length=50, unique=True)    
    reference_no = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=50, null=True, blank=True)
    payment_party_name = models.CharField(max_length=50, choices=PAYMENT_PARTY_CHOICES, null=True, blank=True)
    #paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')    
    #payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    #initiated_time = models.DateTimeField(null=True, blank=True)
    #timeout_time = models.DateTimeField(null=True, blank=True)
    #processed_by = models.ForeignKey(User, related_name='wallet_payment_boy', on_delete=models.CASCADE)


class WalletPayment(AbstractDateTime):
    # This method stores the wallet payment: third party details, payment status
    #payment = models.ForeignKey(ShipmentPayment, related_name='wallet_payment', on_delete=models.CASCADE)
    payment_parent = models.OneToOneField(Payment, related_name='payment_wallet', on_delete=models.CASCADE)    
    #payment_reference_number = models.CharField(max_length=50, unique=True)    
    reference_no = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=50, null=True, blank=True)
    #paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default='0.0000')    
    #payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    #initiated_time = models.DateTimeField(null=True, blank=True)
    #timeout_time = models.DateTimeField(null=True, blank=True)
    #processed_by = models.ForeignKey(User, related_name='wallet_payment_boy', on_delete=models.CASCADE)


class OnlinePayment(AbstractDateTime):
    # This method stores the credit payment: third party details, payment status
    #payment = models.OneToOneField(ShipmentPayment, related_name='online_payment', on_delete=models.CASCADE)
    #payment_reference_number = models.CharField(max_length=50, unique=True)    
    payment_parent = models.OneToOneField(Payment, related_name='payment_online', on_delete=models.CASCADE)    
    reference_no = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=50, null=True, blank=True)
    online_payment_type = models.CharField(max_length=50, choices=ONLINE_PAYMENT_TYPE_CHOICES, null=True, blank=True)
    #paid_amount = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')    
    #payment_approval_status = models.CharField(max_length=50, choices=PAYMENT_APPROVAL_STATUS_CHOICES, default="pending_approval",null=True, blank=True)
    #payment_received = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    #is_payment_approved = models.BooleanField(default=False)
    #payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    #initiated_time = models.DateTimeField(null=True, blank=True)
    #timeout_time = models.DateTimeField(null=True, blank=True)
    #processed_by = models.ForeignKey(User, related_name='wallet_payment_boy', on_delete=models.CASCADE)

    def clean(self):
        if not re.match("^[a-zA-Z0-9_]*$", self.reference_no):
            raise ValidationError('Referece number can not have special character.')
        super(OnlinePayment, self).clean()


class Offer(AbstractDateTime):
    # This method stores the discount description for a payment
    offer_id = models.CharField(max_length=50, unique=True)
    offer_type = models.CharField(max_length=50, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True)
    offer_amount = models.DecimalField(max_digits=6, decimal_places=4, default='0.0000')
    offer_percentage = models.FloatField(default=0.0)
    offer_start_at = models.DateTimeField(null=True,blank=True)
    offer_end_at = models.DateTimeField(null=True,blank=True)
    status = models.BooleanField(default=True)
    offer_limitation = models.CharField(max_length=50, choices=OFFER_LIMITATION_CHOICES, default='per_shop')

    def __str__(self):
        return self.offer_id

    class Meta:
        verbose_name = _("Offer")
        verbose_name_plural = _("Offers")


class ShipmentPaymentApproval(OrderedProduct):
    class Meta:
        proxy = True

class ShipmentPaymentEdit(OrderedProduct):
    class Meta:
        proxy = True
        

class ShipmentData(OrderedProduct):
    class Meta:
        proxy = True        


class PaymentEdit(Payment):
    class Meta:
        proxy = True


class PaymentApproval(Payment):
    class Meta:
        proxy = True        


# @receiver(post_save, sender=Payment)
# def add_online_payment(sender, instance=None, created=False, **kwargs):
#     '''
#     Method to update online payment
#     '''
#     #assign shipment to picklist once SHIPMENT_CREATED
#     if created:
#         OnlinePayment.objects.create(
#             payment_parent=instance,

#             )
