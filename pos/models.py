from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from shops.models import Shop
from products.models import Product
from retailer_backend.validators import ProductNameValidator, NameValidator


PRODUCT_ORIGINS = (
        (1, 'CREATED'),
        (2, 'LINKED'),
        (3, 'LINKED_EDITED'),
    )

STATUS_CHOICES = (
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
    )

class RetailerProduct(models.Model):

    shop = models.ForeignKey(Shop, related_name='retailer_product', on_delete=models.CASCADE)
    sku = models.CharField(max_length=255, blank=False, unique=True)
    name = models.CharField(max_length=255, validators=[ProductNameValidator])
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    linked_product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    sku_type = models.IntegerField(choices=PRODUCT_ORIGINS, default=1)
    status = models.CharField(max_length=20, default='pending_approval', choices=STATUS_CHOICES, blank=False, verbose_name='Product Status')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sku + " - " + self.name


class RetailerProductImage(models.Model):
    product = models.ForeignKey(RetailerProduct, on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    image_alt_text = models.CharField(max_length=255,null=True,blank=True,validators=[NameValidator])
    image = models.ImageField(upload_to='retailer_product_image')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)


