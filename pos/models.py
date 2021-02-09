from django.db import models

from shops.models import Shop
from products.models import Product
from retailer_backend.validators import ProductNameValidator, NameValidator


# Create your models here.


class RetailerProduct(models.Model):
    PRODUCT_ORIGINS = (
        (1, 'CREATED'),
        (2, 'LINKED'),
        (3, 'LINKED_EDITED'),
    )
    shop = models.ForeignKey(Shop, related_name='retailer_product', on_delete=models.CASCADE)
    sku = models.CharField(max_length=255, blank=False, unique=True)
    name = models.CharField(max_length=255, validators=[ProductNameValidator])
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    linked_product = models.ForeignKey(Product, on_delete=models.CASCADE)
    description = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    new = models.IntegerField(choices=PRODUCT_ORIGINS, default=1)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class RetailerProductImage(models.Model):
    product = models.ForeignKey(RetailerProduct, on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    image_alt_text = models.CharField(max_length=255,null=True,blank=True,validators=[NameValidator])
    image = models.ImageField(upload_to='retailer_product_image')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
