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
CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
  )


# Create your models here.
class Payment(models.Model):
    # This class stores the payment information for the shipment
    shop = 
    invoice = 
    cash_payment = models.BooleanField(default=False)
    wallet_payment = models.BooleanField(default=False)
    credit_payment = models.BooleanField(default=False)
    credit_note = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, related_name=payment_created_by)
    updated_by = models.ForeignKey(User, related_name=payment_updated_by)


    def __str__(self):
        return self.vendor_name

    def get_parent_or_self(self,obj):
        pass
        #return brand.id
