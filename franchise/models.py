# Create your models here.
from django.db.models.signals import post_save
from django.db import models
from django.core.validators import RegexValidator

from wms.models import Bin, create_order_id
from audit.models import AuditDetail
from shops.models import Shop
from products.models import Product


phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
def get_default_virtual_bin_id():
    return 'V2VZ01SR001-0001'


class Fbin(Bin):
    class Meta:
        proxy = True
        verbose_name = 'Bin'


class Faudit(AuditDetail):
    class Meta:
        proxy = True
        verbose_name = 'Audit'


class ShopLocationMap(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, unique=True, verbose_name='Shop Name')
    location_name = models.CharField(max_length=255, unique=True, verbose_name='Shop Location')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.shop) + ' | ' + str(self.location_name)


class FranchiseSales(models.Model):
    shop_loc = models.CharField(max_length=255, verbose_name='Shop Location', null=True, blank=True)
    barcode = models.CharField(max_length=255, null=True,blank=True)
    product_sku = models.CharField(max_length=255,null=True,blank=True)
    quantity = models.FloatField(default=0, null=True, blank=True)
    amount = models.FloatField(default=0, null=True, blank=True)
    invoice_date = models.DateTimeField(null=True, blank=True)
    invoice_number = models.CharField(max_length=255, null=True, blank=True)
    discount_amount = models.FloatField(default=0, null=True, blank=True)
    process_status = models.IntegerField(choices=((0, 'Started'), (1, 'Processed'), (2, 'Error')), default=0)
    rewards_status = models.IntegerField(choices=((0, 'Pending'), (1, 'Rewarded'), (2, 'Failed')), default=0)
    error = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(validators=[phone_regex], max_length=10, null=True,blank=True)
    customer_name = models.CharField(max_length=255,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.shop_loc) + ' | ' + str(self.barcode)


class FranchiseReturns(models.Model):
    shop_loc = models.CharField(max_length=255, verbose_name='Shop Location', null=True, blank=True)
    barcode = models.CharField(max_length=255,null=True,blank=True)
    product_sku = models.CharField(max_length=255,null=True,blank=True)
    quantity = models.FloatField(default=0, null=True, blank=True)
    amount = models.FloatField(default=0, null=True, blank=True)
    sr_date = models.DateTimeField(null=True, blank=True)
    sr_number = models.CharField(max_length=255, null=True, blank=True)
    invoice_date = models.DateTimeField(null=True, blank=True)
    invoice_number = models.CharField(max_length=255, null=True, blank=True)
    process_status = models.IntegerField(choices=((0, 'Started'), (1, 'Processed'), (2, 'Error')), default=0)
    error = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(validators=[phone_regex], max_length=10, null=True,blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.shop_loc) + ' | ' + str(self.barcode)


class HdposDataFetch(models.Model):
    type = models.IntegerField(choices=((0, 'Sales'), (1, 'Returns')))
    from_date = models.DateTimeField(null=True, blank=True)
    to_date = models.DateTimeField(null=True, blank=True)
    process_text = models.CharField(max_length=255, null=True, blank=True)
    status = models.IntegerField(choices=((0, 'Started'), (1, 'Completed'), (2, 'Error')), default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class HdposInventoryHistory(models.Model):
    shop_name = models.CharField(max_length=255, null=True, blank=True)
    product_sku = models.CharField(max_length=255, null=True, blank=True)
    product_name = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.CharField(max_length=255, null=True, blank=True)
    error = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WmsInventoryHistory(models.Model):
    warehouse = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.DO_NOTHING)
    sku = models.ForeignKey(Product, to_field='product_sku', on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


# Fbin proxy model for Bin - Signals need to be connected separately (again) for proxy model (if required)
post_save.connect(create_order_id, sender=Fbin)