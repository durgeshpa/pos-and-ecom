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
    company_name = models.CharField(max_length=255, null=True)
    vendor_name = models.CharField(max_length=255, null=True)
    contact_person_name = models.CharField(max_length=255,null=True,blank=True)
    telephone_no = models.CharField(max_length=15,null=True,blank=True)
    mobile = models.CharField(max_length=10, null=True)
    designation = models.CharField(max_length=255, null=True)
    address_line1 = models.CharField(max_length=255, validators=[AddressNameValidator], null=True)
    state = models.ForeignKey(State, related_name='vendor_state_address', on_delete=models.CASCADE, null=True)
    city = models.ForeignKey(City, related_name='vendor_city_address', on_delete=models.CASCADE, null=True)
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6, null=True)
    payment_terms = models.TextField(null=True,blank=True)
    vendor_registion_free = models.CharField(max_length=50,choices=VENDOR_REG_PAYMENT, null=True,blank=True)
    sku_listing_free = models.CharField(max_length=50,choices=VENDOR_REG_PAYMENT, null=True,blank=True)
    return_policy = models.TextField(null=True,blank=True)
    GST_number = models.CharField(max_length=100, null=True)
    MSMED_reg_no = models.CharField(max_length=100, null=True, blank=True)
    MSMED_reg_document = models.FileField(upload_to='vendor/msmed_doc', null=True, blank=True)
    fssai_licence = models.FileField(upload_to='vendor/fssai_licence_doc',null=True,blank=True)
    GST_document = models.FileField(upload_to='vendor/gst_doc', null=True)
    pan_card = models.FileField(upload_to='vendor/pan_card', null=True)
    cancelled_cheque = models.FileField(upload_to='vendor/cancelled_cheque', null=True)
    list_of_sku_in_NPI_formate = models.FileField(upload_to='vendor/slu_list_in_npi',null=True,blank=True)
    vendor_form = models.FileField(upload_to='vendor/vendor_form',null=True,blank=True)
    vendor_products_csv = models.FileField(upload_to='vendor/vendor_products_csv', null=True,blank=True)
    vendor_products_brand = ArrayField(models.PositiveIntegerField(),null=True, blank=True,editable=False)

    def __str__(self):
        return self.vendor_name

    def get_parent_or_self(self,obj):
        pass
        #return brand.id
