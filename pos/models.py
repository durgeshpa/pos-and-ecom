from django.utils.safestring import mark_safe
from django.db import models
from material.frontend.templatetags.material_frontend import verbose_name_plural

from shops.models import Shop
from products.models import Product
from retailer_backend.validators import ProductNameValidator, NameValidator
from accounts.models import User

PAYMENT_MODE_POS = (
    ('cash', 'Cash Payment'),
    ('online', 'Online Payment'),
    ('credit', 'Credit Payment')
)


class  RetailerProduct(models.Model):
    PRODUCT_ORIGINS = (
        (1, 'CREATED'),
        (2, 'LINKED'),
        # (3, 'LINKED_EDITED'),
        (4, 'DISCOUNTED')
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('deactivated', 'Deactivated'),
    )
    shop = models.ForeignKey(Shop, related_name='retailer_product', on_delete=models.CASCADE)
    sku = models.CharField(max_length=255, blank=False, unique=True)
    name = models.CharField(max_length=255, validators=[ProductNameValidator])
    product_ean_code = models.CharField(max_length=255, blank=False)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    # discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=False)
    linked_product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    sku_type = models.IntegerField(choices=PRODUCT_ORIGINS, default=1)
    product_ref = models.OneToOneField('self', related_name='discounted_product', null=True, blank=True,
                                       on_delete=models.CASCADE, verbose_name='Reference Product')
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES, blank=False,
                              verbose_name='Product Status')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id) + ' - ' + str(self.sku) + " - " + str(self.name)

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
        super(RetailerProduct, self).save(*args, **kwargs)


    class Meta:
        verbose_name = 'Product'


class RetailerProductImage(models.Model):
    product = models.ForeignKey(RetailerProduct, related_name='retailer_product_image', on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255, validators=[ProductNameValidator], null=True, blank=True)
    image_alt_text = models.CharField(max_length=255, null=True, blank=True, validators=[NameValidator])
    image = models.ImageField(upload_to='uploads/retailer_product_image/')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def image_thumbnail(self):
        return mark_safe(
            '<a href="{}"><img alt="{}" src="{}" height="200px" width="300px"/></a>'.format(self.image.url,
                                                                                            self.image_name,
                                                                                            self.image.url))

    def __str__(self):
        return self.product.sku + " - " + self.product.name

    class Meta:
        verbose_name = 'Product Image'


class ShopCustomerMap(models.Model):
    user = models.ForeignKey(User, related_name='registered_user', null=True, blank=True, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='registered_shop', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shop User Mapping'


class Payment(models.Model):
    order = models.ForeignKey('retailer_to_sp.Order', related_name='rt_payment_retailer_order',
                              on_delete=models.DO_NOTHING)
    payment_mode = models.CharField(max_length=50, choices=PAYMENT_MODE_POS, default="cash")
    paid_by = models.ForeignKey(User, related_name='rt_payment_retailer_buyer', null=True, blank=True,
                                on_delete=models.DO_NOTHING)
    processed_by = models.ForeignKey(User, related_name='rt_payment_retailer', null=True, blank=True,
                                     on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class DiscountedRetailerProduct(RetailerProduct):
    class Meta:
        proxy = True
        verbose_name = 'Discounted Product'
        verbose_name_plural = 'Discounted Products'
