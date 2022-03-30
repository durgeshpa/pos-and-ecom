from django.contrib.auth import get_user_model
from django.db import models

# Create your models here.
from categories.models import BaseTimeModel


class ZohoFileUpload(BaseTimeModel):
    file = models.FileField(upload_to='zoho/zoho_files/')
    upload_type = models.CharField(max_length=50, default='')
    updated_by = models.ForeignKey(
        get_user_model(), null=True, related_name='zoho_file_uploaded_by',
        on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return f"BulkUpload for Zoho File Upload updated at {self.created_at} by {self.updated_by}"


# class ZohoCreditNote(models.Model):
#     pass


# class ZohoInvoice(models.Model):
#     pass


class ZohoCustomers(models.Model):
    display_name = models.CharField(max_length=133,blank=True,null=True)
    company_name = models.CharField(max_length=133,blank=True,null=True)
    salutation = models.CharField(max_length=10,blank=True,null=True)
    first_name = models.CharField(max_length=25,blank=True,null=True)
    last_name = models.CharField(max_length=25,blank=True,null=True)
    phone = models.CharField(max_length=15,blank=True,null=True)
    currency_code = models.CharField(max_length=15,blank=True,null=True)
    notes = models.CharField(max_length=255,blank=True,null=True)
    website = models.CharField(max_length=255,blank=True,null=True)
    status = models.CharField(max_length=10,blank=True,null=True)
    opening_balance = models.CharField(max_length=20,blank=True,null=True)
    exchange_rate = models.CharField(max_length=10,blank=True,null=True)
    branch_id = models.CharField(max_length=25,blank=True,null=True)
    branch_name = models.CharField(max_length=133,blank=True,null=True)
    credit_limit = models.CharField(max_length=25,blank=True,null=True)

    customer_sub_type = models.CharField(max_length=35,blank=True,null=True)
    billing_attention = models.CharField(max_length=35,blank=True,null=True)
    billing_address = models.CharField(max_length=133,blank=True,null=True)
    billing_street2 = models.CharField(max_length=133,blank=True,null=True)
    billing_city = models.CharField(max_length=133,blank=True,null=True)
    billing_state = models.CharField(max_length=133,blank=True,null=True)
    billing_country = models.CharField(max_length=133,blank=True,null=True)
    billing_code = models.CharField(max_length=33,blank=True,null=True)
    billing_phone = models.CharField(max_length=15,blank=True,null=True)
    billing_fax = models.CharField(max_length=133,blank=True,null=True)

    shipping_attention = models.CharField(max_length=35,blank=True,null=True)
    shipping_address = models.CharField(max_length=133,blank=True,null=True)
    shipping_street2 = models.CharField(max_length=133,blank=True,null=True)
    shipping_city = models.CharField(max_length=133,blank=True,null=True)
    shipping_state = models.CharField(max_length=50,blank=True,null=True)
    shipping_country = models.CharField(max_length=50,blank=True,null=True)
    shipping_code = models.CharField(max_length=33,blank=True,null=True)
    shipping_phone = models.CharField(max_length=15,blank=True,null=True)
    shipping_fax = models.CharField(max_length=133,blank=True,null=True)

    skype_identity = models.CharField(max_length=133,blank=True,null=True)
    facebook = models.CharField(max_length=133,blank=True,null=True)
    twitter = models.CharField(max_length=133,blank=True,null=True)
    department = models.CharField(max_length=133,blank=True,null=True)
    designation = models.CharField(max_length=133,blank=True,null=True)
    price_list = models.CharField(max_length=35,blank=True,null=True)
    payment_team = models.CharField(max_length=35,blank=True,null=True)
    payment_team_labs = models.CharField(max_length=35,blank=True,null=True)
    gst_treatment =  models.CharField(max_length=35,blank=True,null=True)
    gst_identification_number = models.CharField(max_length=35,blank=True,null=True)
    pan_number = models.CharField(max_length=15,blank=True,null=True)
    last_sync_time = models.CharField(max_length=15,blank=True,null=True)
    owner_name = models.CharField(max_length=25,blank=True,null=True)
    primary_contect_id = models.CharField(max_length=25,blank=True,null=True)
    email_id = models.CharField(max_length=35,blank=True,null=True)
    mobile_phone = models.CharField(max_length=15,blank=True,null=True)
    contect_id = models.CharField(max_length=15,blank=True,null=True)
    contect_type = models.CharField(max_length=15,blank=True,null=True)
    place_of_contect =  models.CharField(max_length=15,blank=True,null=True)
    place_of_contect_with_state_code =  models.CharField(max_length=25,blank=True,null=True)
    taxable = models.CharField(max_length=25,blank=True,null=True)
    tax_name = models.CharField(max_length=25,blank=True,null=True)
    tax_percentage = models.CharField(max_length=10,blank=True,null=True)
    exemption_reason = models.CharField(max_length=30,blank=True,null=True)
    contect_address_id = models.CharField(max_length=25,blank=True,null=True)
    source = models.CharField(max_length=25,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    class Meta:
        pass

