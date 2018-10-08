from django.db import models
from addresses.models import Address
from django.contrib.auth import get_user_model


SHOP_TYPE_CHOICES = (
    ("sp","Service Partner"),
    ("r","Retailer"),
    ("sr","Super Retailer"),
)

class RetailerType(models.Model):
    retailer_type_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.retailer_type_name

class ShopType(models.Model):
    shop_type = models.CharField(max_length=50, choices=SHOP_TYPE_CHOICES, default='r')
    shop_sub_type = models.ForeignKey(RetailerType, related_name='shop_sub_type_shop', null=True, blank=True,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return "%s - %s"%(self.get_shop_type_display(),self.shop_sub_type.retailer_type_name) if self.shop_sub_type else "%s"%(self.get_shop_type_display())

class Shop(models.Model):
    shop_name = models.CharField(max_length=255)
    shop_owner = models.ForeignKey(get_user_model(), related_name='shop_owner_shop',on_delete=models.CASCADE)
    shop_shipping_address = models.ForeignKey(Address,related_name='shipping_add_shop',on_delete=models.CASCADE)
    shop_billing_address = models.ForeignKey(Address,related_name='billing_add_shop',on_delete=models.CASCADE)
    shop_type = models.ForeignKey(ShopType,related_name='shop_tyoe_shop',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return "%s - %s"%(self.shop_name, self.shop_type.get_shop_type_display())

class SpRetailerMapping(models.Model):
    service_partner = models.ForeignKey(Shop,related_name='sp_mapping',on_delete=models.CASCADE)
    retailer = models.ForeignKey(Shop,related_name='retiler_mapping',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
