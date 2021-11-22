import sys
import traceback
import datetime, csv, codecs, re
import uuid

from django.db import models
from django.utils.html import format_html_join, format_html
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from django.db.models import Case, CharField, Value, When, F, Sum
from django.contrib.auth import get_user_model

from accounts.models import UserWithName
from retailer_backend.common_function import payment_id_pattern
from retailer_to_sp.models import Order, Shipment, OrderedProduct
from shops.models import Shop


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

#default is initiated
PAYMENT_STATUS_CHOICES = (
    ('not_initiated', 'not_initiated'),
    ('initiated', 'initiated'),
    #('in_progress', 'in_progress'),
    ('cancelled', 'cancelled'),
    ('failure', 'failure'),
    ('completed', 'completed'), #successful
    #('refunded', 'refunded') # add this one.
  )

PAYMENT_APPROVAL_STATUS_CHOICES = (
    ('pending_approval', 'pending_approval'),
    ('approved_and_verified', 'approved_and_verified'),
    #('disputed', 'disputed'),
    ('rejected', 'rejected'),
  )


FINAL_PAYMENT_STATUS_CHOICES = (
    ('PENDING', 'Pending'),
    ('PARTIALLY_PAID', 'Partially_paid'),
    ('PAID', 'Paid'),
)

USER_DOCUMENTS_TYPE_CHOICES = (
    ("payment_screenshot", "payment_screenshot"),
)

ONLINE_PAYMENT_TYPE_CHOICES = (
    #('paytm', 'paytm'),
    ('UPI', 'UPI'),
    ('NEFT', 'NEFT'),
    ('IMPS', 'IMPS'),
    ('RTGS', 'RTGS'),
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


class PaymentImage(models.Model):
    user = models.ForeignKey(User, related_name='payment_screenshot', on_delete=models.SET_NULL,
        null=True, blank=True)
    user_document_type = models.CharField(max_length=100, choices=USER_DOCUMENTS_TYPE_CHOICES, default='payment_screenshot')
    #reference_number = models.CharField(max_length=100)
    reference_image = models.FileField(upload_to='payment/screenshot/')

    def reference_image_thumbnail(self):
        return mark_safe('<img alt="%s" src="%s" />' % (self.user, self.reference_image.url))

    def __str__(self):
        return "%s - %s"%(self.user, self.reference_image.url)

    class Meta:
        verbose_name = "Payment Screenshot"


#if prepaid then its against order, else shipment
# replace order with user

class Payment(AbstractDateTime):
    order = models.ManyToManyField(Order, through="OrderPayment", related_name='order_payment_data')
    #order = models.ForeignKey(Order, related_name='order_payment_data', on_delete=models.CASCADE)
    # payment description
    description = models.CharField(max_length=100, null=True, blank=True)
    reference_no = models.CharField(max_length=50, null=True, blank=True)
    #payment_screenshot = models.ImageField(upload_to='payment_screenshot/', null=True, blank=True)
    payment_screenshot = models.ForeignKey(PaymentImage, null=True, blank=True, on_delete = models.SET_NULL)
    paid_amount = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    payment_mode_name = models.CharField(max_length=50, choices=PAYMENT_MODE_NAME, default="cash_payment")
    prepaid_or_postpaid = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES,null=True, blank=True)
    #payment_id = models.CharField(max_length=255, null=True, blank=True)
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # for finance team
    payment_approval_status = models.CharField(max_length=50, choices=PAYMENT_APPROVAL_STATUS_CHOICES, default="pending_approval",null=True, blank=True)
    payment_received = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    is_payment_approved = models.BooleanField(default=False)
    mark_as_settled = models.BooleanField(default=False)

    # for payment processing
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True, default="initiated")
    online_payment_type = models.CharField(max_length=50, choices=ONLINE_PAYMENT_TYPE_CHOICES, null=True, blank=True)
    initiated_time = models.DateTimeField(null=True, blank=True)
    timeout_time = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(UserWithName, related_name='payment_user',
        null=True, blank=True, on_delete=models.SET_NULL)
    processed_by = models.ForeignKey(UserWithName, related_name='payment_boy',
        null=True, blank=True, on_delete=models.SET_NULL)
    approved_by = models.ForeignKey(UserWithName, related_name='payment_approver',
        null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{} -> {}".format(
            self.payment_mode_name,
            self.paid_amount
        )

    def orders(self):
        # if hasattr(self, 'order_objects'):
        #     return self.order_objects
        self.order_objects = self.parent_payment_order.all()
        return format_html_join(
                "","{}<br><br>",
                        ((s.order.order_no,
                        ) for s in self.order_objects)
                )  

    def shipments(self):
        # if hasattr(self, 'order_objects'):
        #     return self.order_objects
        invoice_objects = ShipmentPayment.objects.filter(parent_order_payment__parent_payment__id=self.id)
        return format_html_join(
                "","{}<br><br>",
                        ((s.shipment.invoice_no,
                        ) for s in invoice_objects)
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
            self.payment_approval_status = "approved_and_verified"
        if self.payment_mode_name == "cash_payment":
            self.payment_approval_status = "approved_and_verified"    

        super().save(*args, **kwargs)


class Error(Exception):
   """Base class for other exceptions"""
   pass

class ValueTooLargeError(Error):
   """Raised when the input value is too large"""
   pass

class OrderPayment(AbstractDateTime):
    # This class stores the payment information for the shipment
    description = models.CharField(max_length=50, null=True, blank=True)
    order = models.ForeignKey(Order, related_name='order_payment', on_delete=models.CASCADE) #shipment_id
    parent_payment = models.ForeignKey(Payment, 
       related_name='parent_payment_order', on_delete=models.CASCADE)
    paid_amount = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    payment_id = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(UserWithName, related_name='order_payment_created_by', null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(UserWithName, related_name='order_payment_updated_by', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{}->{},{}".format(
            str(self.order), 
            str(self.parent_payment.payment_mode_name), 
            str(self.paid_amount),
            #str(self.paid_amount - self.payment_utilised)
            )

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

    @property
    def payment_utilised_excluding_current(self):
        payment = self.parent_payment.parent_payment_order.all()
        payment_excluding_current = payment.exclude(id=self.id)
        if payment_excluding_current.exists():
            payment_data = payment_excluding_current.aggregate(Sum('paid_amount')) #annotate(sum_paid_amount=Sum('paid_amount')) 

            if payment_data:
                return payment_data['paid_amount__sum'] #sum_paid_amount
        else:
            return 0

    def clean(self):
        #payment except current
        try:
            if float(self.payment_utilised_excluding_current) + float(self.paid_amount) > float(self.parent_payment.paid_amount):
                error_msg = "Maximum amount to be utilised from parent payment is " + str(self.parent_payment.paid_amount - self.payment_utilised_excluding_current)
                raise ValueTooLargeError #ValidationError(_(error_msg),)   
        except ValueTooLargeError:
            raise ValidationError(_(error_msg),)
        except:
            pass

# create payment mode table shipment payment mapping
class ShipmentPayment(AbstractDateTime):
    # This class stores the payment information for the shipment
    description = models.CharField(max_length=50, null=True, blank=True)
    shipment = models.ForeignKey(OrderedProduct, related_name='shipment_payment', on_delete=models.CASCADE) #shipment_id
    parent_order_payment = models.ForeignKey(OrderPayment, 
       related_name='shipment_order_payment', on_delete=models.CASCADE)
    paid_amount = models.DecimalField(validators=[MinValueValidator(0)], max_digits=20, decimal_places=4, default='0.0000')
    created_by = models.ForeignKey(User, related_name='payment_created_by', null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(User, related_name='payment_updated_by', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.shipment.id)

    # def get_parent_or_self(self,obj):
    #     pass
        #return brand.id
    
    @property
    def payment_utilised_excluding_current(self):
        payment = self.parent_order_payment.shipment_order_payment.all()
        payment_excluding_current = payment.exclude(id=self.id)
        if payment_excluding_current.exists():
            payment_data = payment_excluding_current.aggregate(Sum('paid_amount')) #annotate(sum_paid_amount=Sum('paid_amount')) 

            if payment_data:
                return payment_data['paid_amount__sum'] #sum_paid_amount
        else:
            return 0

    def clean(self):
        # if self.payment_utilised_excluding_current + self.paid_amount > self.parent_order_payment.paid_amount:
        #     error_msg = "Maximum amount to be utilised from parent order payment is " + str(self.parent_order_payment.paid_amount - self.payment_utilised_excluding_current)
        #     raise ValidationError(_(error_msg),)
        cash_to_be_collected = self.shipment.cash_to_be_collected()
        if cash_to_be_collected < self.paid_amount:
            error_msg = "Maximum amount to be collected is " + str(cash_to_be_collected)
            raise ValidationError(_(error_msg),)

        try:
            if float(self.payment_utilised_excluding_current) + float(self.paid_amount) > float(self.parent_order_payment.paid_amount):
                error_msg = "Maximum amount to be utilised from parent order payment is " + str(self.parent_order_payment.paid_amount - self.payment_utilised_excluding_current)
                raise ValueTooLargeError #ValidationError(_(error_msg),)   
        except ValueTooLargeError:
            raise ValidationError(_(error_msg),)
        except:
            pass
            
        # try:
        #     payment = self.parent_order_payment
        # except:
        #     pass #raise ValidationError(_("Parent Order Payment is required"))
        # else:
        #     if float(self.payment_utilised_excluding_current) + float(self.paid_amount) > float(self.parent_order_payment.paid_amount):
        #         error_msg = "Maximum amount to be utilised from parent order payment is " + str(self.parent_order_payment.paid_amount - self.payment_utilised_excluding_current)
        #         raise ValidationError(_(error_msg),)

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

    @property
    def payment_approval_status(self):
        payments = self.shipment.shipment_payment.all()
        for payment in payments:
            payment_status = payment.parent_order_payment.parent_payment.payment_approval_status
            if payment_status == "pending_approval":
                return "pending_approval"
        else:
            return  "approved_and_verified"


class PaymentMode(models.Model):
    payment_mode_name = models.CharField(max_length=50, choices=PAYMENT_MODE_NAME, null=True, blank=True)
    status = models.BooleanField(default=True)
    #payment = models.ForeignKey(ShipmentPayment, related_name='payment_mode', on_delete=models.CASCADE)

    def __str__(self):
        return self.payment_mode_name #,str(self.payment.id), self.payment_mode_name

    # class Meta:
    #     unique_together = (('payment', 'payment_mode_name'),)


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


# @receiver(post_save, sender=Payment)
# def create_payment_id(sender, instance=None, created=False, **kwargs):
#     if created:
#         shop = Shop.objects.get(shop_owner=instance.paid_by)
#         instance.payment_id = payment_id_pattern(
#                                     sender, 'payment_id', instance.pk,
#                                     shop.shop_name_address_mapping.filter(
#                                         address_type='billing').last().pk)
#         instance.save()


@receiver(post_save, sender=OrderPayment)
def create_payment_id(sender, instance=None, created=False, **kwargs):
    if created:
        try:
            instance.payment_id = payment_id_pattern(
                                        sender, 'payment_id', instance.pk,
                                        instance.order.seller_shop.
                                        shop_name_address_mapping.filter(
                                            address_type='billing').last().pk)
            instance.save()
        except:
            pass

# @receiver(pre_save, sender=ShipmentPayment)
# def check_max_shipment_payment(sender, instance=None, created=False, **kwargs):
#     cash_to_be_collected = instance.shipment.cash_to_be_collected()
#     if cash_to_be_collected < instance.paid_amount:
#         error_msg = "Maximum amount to be collected is " + str(cash_to_be_collected)
#         raise ValidationError(_(error_msg),)
