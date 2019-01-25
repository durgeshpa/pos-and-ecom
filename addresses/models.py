from django.db import models
from retailer_backend.validators import (NameValidator, AddressNameValidator,
        MobileNumberValidator, PinCodeValidator)
from shops.models import Shop
from django.utils.translation import ugettext_lazy as _

address_type_choices = (
    ("billing","Billing"),
    ("shipping","Shipping"),
    ("registered","Registered"),
)
# Create your models here.
class Country(models.Model):
    country_name = models.CharField(max_length=255, validators=[NameValidator])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.country_name

    class Meta:
        verbose_name_plural = _("Countries")

class State(models.Model):
    country = models.ForeignKey(Country,related_name='country_state',null=True,blank=True,on_delete=models.CASCADE)
    state_name = models.CharField(max_length=255,validators=[NameValidator])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.state_name

class City(models.Model):
    country = models.ForeignKey(Country, related_name='country_city', null=True, blank=True, on_delete=models.CASCADE)
    state = models.ForeignKey(State, related_name='state_city', null=True, blank=True, on_delete=models.CASCADE)
    city_name = models.CharField(max_length=255, validators=[NameValidator])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.city_name

    class Meta:
        verbose_name_plural = _("Cities")

class Area(models.Model):
    city = models.ForeignKey(City, related_name='city_area', null=True, blank=True, on_delete=models.CASCADE)
    area_name = models.CharField(max_length=255, validators=[NameValidator])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.area_name

class Address(models.Model):
    nick_name = models.CharField(max_length=255,null=True,blank=True)
    shop_name = models.ForeignKey(Shop, related_name='shop_name_address_mapping', on_delete=models.CASCADE, null=True, blank=True)
    address_line1 = models.CharField(max_length=255,validators=[AddressNameValidator])
    address_contact_name = models.CharField(max_length=255,null=True,blank=True)
    address_contact_number = models.CharField(validators=[MobileNumberValidator], max_length=10, blank=True)
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6, blank=True)
    state = models.ForeignKey(State, related_name='state_address', on_delete=models.CASCADE, blank=True, null=True)
    city = models.ForeignKey(City, related_name='city_address', on_delete=models.CASCADE)
    address_type = models.CharField(max_length=255,choices=address_type_choices,default='shipping')
    latitude = models.FloatField(default=0,null=True,blank=True)
    longitude = models.FloatField(default=0, null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return "%s - %s"%(self.shop_name , self.address_line1)

class InvoiceCityMapping(models.Model):

    """City mapping with code

    This class is created to map city with code names used for invoicesself.
    ex: ADT/07/000001 (for Delhi) ADT/DS/000001 (for noida)
    """

    city = models.OneToOneField(City, related_name='invoice_city_code_mapping', on_delete=models.CASCADE)
    city_code = models.CharField(max_length=255, blank=False, default='07')

    def __str__(self):
        return self.city_code

    class Meta:
        verbose_name = _("Invoice City Mapping")
        verbose_name_plural = _("Invoice City Mappings")
