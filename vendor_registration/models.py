from django.db import models
from addresses.models import State,City
from retailer_backend.validators import (NameValidator, AddressNameValidator,MobileNumberValidator, PinCodeValidator)

VENDOR_REG_PAYMENT = (
    ("paid","Paid"),
    ("unpaid", "Un-Paid"),
)

# Create your models here.
class Vendor(models.Model):
    company_name = models.CharField(max_length=255)
    vendor_name = models.CharField(max_length=255)
    contact_person_name = models.CharField(max_length=255,null=True,blank=True)
    telephone_no = models.CharField(max_length=15,null=True,blank=True)
    mobile = models.CharField(max_length=10)
    designation = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255, validators=[AddressNameValidator])
    state = models.ForeignKey(State, related_name='vendor_state_address', on_delete=models.CASCADE, blank=True, null=True)
    city = models.ForeignKey(City, related_name='vendor_city_address', on_delete=models.CASCADE)
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6, blank=True)
    gst_number = models.CharField(max_length=100)
    msmed_reg_no = models.CharField(max_length=100,null=True,blank=True)
    msmed_reg_document = models.FileField(upload_to='vendor/msmed_doc')
    payment_terms = models.TextField(null=True,blank=True)
    vendor_registion_free = models.CharField(max_length=50,choices=VENDOR_REG_PAYMENT, null=True,blank=True)
    sku_listing_free = models.CharField(max_length=50,choices=VENDOR_REG_PAYMENT, null=True,blank=True)
    return_policy = models.TextField(null=True,blank=True)
    fssai_licence = models.FileField(upload_to='vendor/fssai_licence_doc',null=True,blank=True)
    gst_document = models.FileField(upload_to='vendor/gst_doc')
    pan_card = models.FileField(upload_to='vendor/pan_card')
    cancelled_cheque = models.FileField(upload_to='vendor/cancelled_cheque')
    list_of_sku_in_NPI_formate = models.FileField(upload_to='vendor/slu_list_in_npi')
    vendor_form = models.FileField(upload_to='vendor/vendor_form',null=True,blank=True)

    def __str__(self):
        return self.vendor_name
