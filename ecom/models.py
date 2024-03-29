from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from products.models import Product
from retailer_backend.validators import (AddressNameValidator, MobileNumberValidator, PinCodeValidator)
from accounts.models import User
from pos.models import RetailerProduct, PosTrip
from addresses.models import City, State, Pincode
from ecom.managers import EcomTripModelManager

from retailer_to_sp.models import Cart, OrderedProduct, OrderedProductMapping, CartProductMapping, Order
from shops.models import Shop


class Address(models.Model):
    HOME_TYPE = "Home"
    OFFICE_TYPE = "Office"
    OTHER_TYPE = "Other"
    TYPE_CHOICES = (
        (HOME_TYPE, "Home"),
        (OFFICE_TYPE, "Office"),
        (OTHER_TYPE, "Other"),
    )
    user = models.ForeignKey(User, related_name='ecom_user_address', on_delete=models.CASCADE)
    type = models.CharField(max_length=20, default='other', choices=TYPE_CHOICES)
    address = models.CharField(max_length=255, validators=[AddressNameValidator])
    contact_name = models.CharField(max_length=255)
    contact_number = models.CharField(validators=[MobileNumberValidator], max_length=10)
    latitude = models.FloatField(default=0, null=True, blank=True)
    longitude = models.FloatField(default=0, null=True, blank=True)
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6)
    city = models.ForeignKey(City, related_name='city_address_ecom', on_delete=models.CASCADE)
    state = models.ForeignKey(State, related_name='state_address_ecom', on_delete=models.CASCADE)
    default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        pin_code_obj = Pincode.objects.filter(pincode=self.pincode).select_related('city', 'city__state').last()
        self.city = pin_code_obj.city
        self.state = pin_code_obj.city.state
        if self.default:
            Address.objects.filter(user=self.user).update(default=False)
        super().save(*args, **kwargs)

    @property
    def city_name(self):
        return self.city.city_name

    @property
    def state_name(self):
        return self.city.state.state_name

    @property
    def complete_address(self):
        return str(self.address) + ', ' + self.city_name + ' - ' + str(self.pincode)


class EcomOrderAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.DO_NOTHING, related_name='ecom_address_order')
    address = models.CharField(max_length=255, validators=[AddressNameValidator])
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_number = models.CharField(validators=[MobileNumberValidator], max_length=10, blank=True)
    latitude = models.FloatField(default=0, null=True, blank=True)
    longitude = models.FloatField(default=0, null=True, blank=True)
    pincode = models.CharField(validators=[PinCodeValidator], max_length=6, blank=True)
    state = models.ForeignKey(State, related_name='state_address_order', on_delete=models.CASCADE, blank=True, null=True)
    city = models.ForeignKey(City, related_name='city_address_order', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Tag(models.Model):
    key = models.CharField(max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    position = models.IntegerField()
    status = models.BooleanField(default=1)

    def __str__(self):
        return self.name

def generate_unique_key(instance):
    origin_slug = slugify(instance.name)
    updated_origin_slug = "-".join(origin_slug.split())
    unique_slug = updated_origin_slug
    numb = 1
    while Tag.objects.filter(key=unique_slug).exists():
        unique_slug = '%s-%d' % (origin_slug, numb)
        numb += 1
    return unique_slug

@receiver(pre_save, sender=Tag)
def pre_save_reciever(sender, instance, *args, **kwargs):
    if not instance.key:
        instance.key = generate_unique_key(instance)


class TagProductMapping(models.Model):
    tag = models.ForeignKey(Tag, related_name='tag_ecom', on_delete=models.CASCADE)
    product = models.ForeignKey(RetailerProduct, related_name='product_tag_ecom', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.tag.name + '-' + self.product.name


class EcomCart(Cart):
    class Meta:
        proxy = True
        app_label = 'ecom'
        verbose_name = 'Ecommerce - Cart'


class EcomCartProductMapping(CartProductMapping):
    
    class Meta:
        proxy = True
        app_label = 'ecom'
        verbose_name = 'Ecommerce - Cart Product Mapping'


class EcomOrderedProduct(OrderedProduct):
    
    class Meta:
        proxy = True
        app_label = 'ecom'
        verbose_name = 'Ecommerce - Ordered Product'


class EcomOrderedProductMapping(OrderedProductMapping):
    class Meta:
        proxy = True
        app_label = 'ecom'
        verbose_name = 'Ecommerce - Ordered Product Mapping'


class EcomTrip(PosTrip):
    objects = EcomTripModelManager()

    class Meta:
        proxy = True


class UserPastPurchases(models.Model):
    user = models.ForeignKey(User, related_name='user_purchases',null=True, on_delete=models.DO_NOTHING)
    shop = models.ForeignKey(Shop, related_name='products_sold', on_delete=models.DO_NOTHING)
    buyer_shop = models.ForeignKey(Shop, related_name='products_sold_to', null=True, on_delete=models.DO_NOTHING)
    product = models.ForeignKey(RetailerProduct, related_name='products_sold',null=True, on_delete=models.DO_NOTHING)
    retail_Product = models.ForeignKey(Product, related_name='retail_products_sold',default=None,null=True, on_delete=models.DO_NOTHING)
    last_purchased_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class ShopUserLocationMappedLog(models.Model):
    user = models.ForeignKey(get_user_model(), related_name='user_location', on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='shop_location', on_delete=models.CASCADE)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (("can_have_shop_user_mapping_view_permission",
                        "Can View shop & user mapping Log"),)
