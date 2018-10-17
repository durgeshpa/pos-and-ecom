from django.db import models
from retailer_backend.validators import NameValidator, AddressNameValidator

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

class Area(models.Model):
    city = models.ForeignKey(City, related_name='city_area', null=True, blank=True, on_delete=models.CASCADE)
    area_name = models.CharField(max_length=255, validators=[NameValidator])
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.area_name

class Address(models.Model):
    nick_name = models.CharField(max_length=255,validators=[NameValidator],null=True,blank=True)
    address_line1 = models.CharField(max_length=255,validators=[AddressNameValidator])
    #address_line2 = models.CharField(max_length=255,validators=[AddressNameValidator],null=True,blank=True)
    #locality = models.CharField(max_length=255,validators=[AddressNameValidator],null=True,blank=True)
    #country = models.ForeignKey(Country, related_name='country_address', null=True, blank=True, on_delete=models.CASCADE)
    #state = models.ForeignKey(State, related_name='state_address', on_delete=models.CASCADE)
    city = models.ForeignKey(City, related_name='city_address', on_delete=models.CASCADE)
    address_type = models.CharField(max_length=255,choices=address_type_choices,default='billing')
    latitude = models.FloatField(default=0,null=True,blank=True)
    longitude = models.FloatField(default=0, null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.nick_name
