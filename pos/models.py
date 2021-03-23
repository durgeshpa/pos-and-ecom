import uuid

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from shops.models import Shop
from products.models import Product
from retailer_backend.validators import ProductNameValidator, NameValidator
from accounts.models import User

PAYMENT_MODE = (
    ('cash', 'Cash Payment'),
    ('online', 'Online Payment'),
    ('credit', 'Credit Payment')
)

class RetailerProduct(models.Model):
    PRODUCT_ORIGINS = (
        (1, 'CREATED'),
        (2, 'LINKED'),
        (3, 'LINKED_EDITED'),
    )

    STATUS_CHOICES = (
            ('pending_approval', 'Pending Approval'),
            ('active', 'Active'),
            ('deactivated', 'Deactivated'),
        )

    shop = models.ForeignKey(Shop, related_name='retailer_product', on_delete=models.CASCADE)
    sku = models.CharField(max_length=255, blank=False, unique=True)
    name = models.CharField(max_length=255, validators=[ProductNameValidator])
    product_slug = models.SlugField(max_length=255, blank=True)
    product_ean_code = models.CharField(max_length=255,  blank=False)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    linked_product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    sku_type = models.IntegerField(choices=PRODUCT_ORIGINS, default=1)
    status = models.CharField(max_length=20, default='pending_approval', choices=STATUS_CHOICES, blank=False, verbose_name='Product Status')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sku + " - " + self.name

    @property
    def product_short_description(self):
        return self.name

    @property
    def product_name(self):
        return self.name

    @property
    def product_sku(self):
        return self.sku

    @property
    def product_mrp(self):
        return self.mrp

    @property
    def product_price(self):
        return self.selling_price

    def save(self, *args, **kwargs):
        self.product_slug = slugify(self.name)
        super(RetailerProduct, self).save(*args, **kwargs)


def sku_generator(shop_id):
    return (str(shop_id) + str(uuid.uuid4().hex).upper())[0:17]


@receiver(pre_save, sender=RetailerProduct)
def create_product_sku(sender, instance=None, created=False, **kwargs):
    if not instance.sku:
        # Generate a unique SKU by using shop_id & uuid4 once, then check the db. If exists, keep trying.
        sku_id = sku_generator(instance.shop.id)
        while RetailerProduct.objects.filter(sku=sku_id).exists():
            sku_id = sku_generator(instance.shop.id)
        instance.sku = sku_id


class RetailerProductImage(models.Model):
    product = models.ForeignKey(RetailerProduct, related_name='retailer_product_image', on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255,validators=[ProductNameValidator])
    image_alt_text = models.CharField(max_length=255,null=True,blank=True,validators=[NameValidator])
    image = models.ImageField(upload_to='retailer_product_image')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.product.sku + " - " + self.product.name


class UserMappedShop(models.Model):
    user = models.ForeignKey(User, related_name='registered_user', null=True, blank=True, on_delete=models.CASCADE)
    shop_id = models.ForeignKey(Shop, related_name='registered_shop', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Payment(models.Model):
    order = models.ForeignKey('retailer_to_sp.Order', related_name='rt_payment_retailer_order', on_delete=models.DO_NOTHING)
    payment_mode = models.CharField(max_length=50, choices=PAYMENT_MODE, default="cash")
    paid_by = models.ForeignKey(User, related_name='rt_payment_retailer_buyer', null=True, blank=True, on_delete=models.SET_NULL)
    processed_by = models.ForeignKey(User, related_name='rt_payment_retailer', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
