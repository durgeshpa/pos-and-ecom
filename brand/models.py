from django.db import models
from adminsortable.fields import SortableForeignKey
from adminsortable.models import SortableMixin
#from vendor_registration.models import Vendor
from mptt.models import TreeForeignKey
from django.core.exceptions import ValidationError
from addresses.models import City,State
from retailer_backend.validators import ( AddressNameValidator, PinCodeValidator)
from django.core.validators import RegexValidator
from retailer_backend.validators import CapitalAlphabets
from django.dispatch import receiver
from django.db.models.signals import post_save
import datetime, csv, codecs, re
from django.urls import reverse

VENDOR_REG_PAYMENT = (
    ("paid","Paid"),
    ("unpaid", "Un-Paid"),
)

# Create your models here.
CHOICES = (
    (1, 'Active'),
    (2, 'Inactive'),
  )

def validate_image(image):
    file_size = image.file.size
    if file_size > 300 * 300:
        raise ValidationError("Max size of file is 300 * 300" )

    #limit_mb = 8
    #if file_size > limit_mb * 1024 * 1024:
    #    raise ValidationError("Max size of file is %s MB" % limit_mb)

# Create your models here.
class Vendor(models.Model):
    company_name = models.CharField(max_length=255)
    vendor_name = models.CharField(max_length=255)
    contact_person_name = models.CharField(max_length=255,null=True,blank=True)
    telephone_no = models.CharField(max_length=15,null=True,blank=True)
    mobile = models.CharField(max_length=10)
    designation = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255, validators=[AddressNameValidator])
    state = models.ForeignKey(State, related_name='vendor_state_address', on_delete=models.CASCADE)
    city = models.ForeignKey(City, related_name='vendor_city_address', on_delete=models.CASCADE)
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6)
    payment_terms = models.TextField(null=True,blank=True)
    vendor_registion_free = models.CharField(max_length=50,choices=VENDOR_REG_PAYMENT, null=True,blank=True)
    sku_listing_free = models.CharField(max_length=50,choices=VENDOR_REG_PAYMENT, null=True,blank=True)
    return_policy = models.TextField(null=True,blank=True)
    GST_number = models.CharField(max_length=100)
    MSMED_reg_no = models.CharField(max_length=100, null=True, blank=True)
    MSMED_reg_document = models.FileField(upload_to='vendor/msmed_doc', null=True, blank=True)
    fssai_licence = models.FileField(upload_to='vendor/fssai_licence_doc',null=True,blank=True)
    GST_document = models.FileField(upload_to='vendor/gst_doc')
    pan_card = models.FileField(upload_to='vendor/pan_card')
    cancelled_cheque = models.FileField(upload_to='vendor/cancelled_cheque')
    list_of_sku_in_NPI_formate = models.FileField(upload_to='vendor/slu_list_in_npi',null=True,blank=True)
    vendor_form = models.FileField(upload_to='vendor/vendor_form',null=True,blank=True)
    vendor_products_csv = models.FileField(upload_to='vendor/vendor_products_csv', null=True,blank=True)

    def __str__(self):
        return self.vendor_name

class Brand(models.Model):
    brand_name = models.CharField(max_length=20)
    #brand_slug = models.SlugField(unique=True)
    brand_logo = models.FileField(validators=[validate_image], blank=False,null=True)
    brand_parent = models.ForeignKey('self', related_name='brnd_parent', null=True, blank=True,on_delete=models.CASCADE)
    brand_description = models.TextField(null=True, blank=True)
    brand_code = models.CharField(max_length=3,validators=[CapitalAlphabets],help_text="Please enter three character for SKU")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active_status = models.PositiveSmallIntegerField(('Active Status'),choices=CHOICES,default='1')

    def __str__(self):
        full_path = [self.brand_name]
        k = self.brand_parent

        while k is not None:
            full_path.append(k.brand_name)
            k = k.brand_parent

        return ' -> '.join(full_path[::-1])

    # class Meta:
    #     unique_together = ('brand_name', 'brand_slug',)


class BrandPosition(SortableMixin):
    #page = models.ForeignKey(Page,on_delete=models.CASCADE, null=True)
    position_name = models.CharField(max_length=255)
    brand_position_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.position_name

    class Meta:
        ordering = ['brand_position_order']

class BrandData(SortableMixin):
    slot = SortableForeignKey(BrandPosition,related_name='brand_data',null=True,blank=True, on_delete=models.CASCADE)
    brand_data = models.ForeignKey(Brand,related_name='brand_position_data',null=True,blank=True, on_delete=models.CASCADE)
    brand_data_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

    def __str__(self):
        return self.slot.position_name

    class Meta:
        ordering = ['brand_data_order']
