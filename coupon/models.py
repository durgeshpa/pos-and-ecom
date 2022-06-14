import logging
import datetime

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from elasticsearch import Elasticsearch

from accounts.models import User
from brand.models import Brand
from categories.models import Category, B2cCategory
from shops.models import Shop
from addresses.models import City
from retailer_backend.settings import ELASTICSEARCH_PREFIX as es_prefix, es

error_logger = logging.getLogger('file-error')


# Create your models here.
class DiscountValue(models.Model):
    discount_value = models.FloatField(default=0, null=True, blank=True)
    is_percentage = models.BooleanField(default=False)
    max_discount = models.FloatField(default=0, null=True, blank=True)
    is_point = models.BooleanField(default=False)

    def __str__(self):
        return str(self.discount_value)


class CouponRuleSet(models.Model):
    rulename = models.CharField(max_length=255, unique=True, null=True)
    rule_description = models.CharField(max_length=255, null=True)
    no_of_users_allowed = models.ManyToManyField(User, blank=True)
    all_users = models.BooleanField(default=False)
    discount_qty_step = models.PositiveIntegerField(default=1, null=True, blank=True)
    discount_qty_amount = models.FloatField(default=0, null=True, blank=True)
    discount = models.ForeignKey(DiscountValue, related_name='discount_value_id', on_delete=models.CASCADE, null=True,
                                 blank=True)
    is_free_shipment = models.BooleanField(default=False, null=True, blank=True)
    free_product = models.ForeignKey("pos.RetailerProduct", related_name='free_product', on_delete=models.CASCADE,
                                        null=True, blank=True)
    free_product_qty = models.PositiveIntegerField(blank=True, null=True)
    cart_qualifying_min_sku_value = models.FloatField(default=0, blank=True, null=True)
    cart_qualifying_min_sku_item = models.PositiveIntegerField(default=0, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateField(default=datetime.date.today)
    expiry_date = models.DateField()

    def __str__(self):
        return self.rulename


class Coupon(models.Model):
    CART = "cart"
    CATALOG = "catalog"
    BRAND = "brand"
    CATEGORY = "category"
    COUPON_TYPE = (
        (CART, "cart"),
        (CATALOG, "catalog"),
        (BRAND, "brand"),
        (CATEGORY, "category"),
    )
    SHOP_TYPE_CHOICES = (('all', 'All'),( 'fofo', 'Fofo'),('foco','Foco'))
    ENABLED_ON = (('pos', 'Pos'),('online',"Online"),('all', 'All'))
    rule = models.ForeignKey(CouponRuleSet, related_name='coupon_ruleset', on_delete=models.CASCADE)
    coupon_name = models.CharField(max_length=255, null=True)
    coupon_code = models.CharField(max_length=255, null=True)
    limit_per_user_per_day = models.PositiveIntegerField(default=0, null=True, blank=True)
    limit_of_usages = models.PositiveIntegerField(default=0, null=True, blank=True)
    coupon_type = models.CharField(max_length=255, choices=COUPON_TYPE, null=True, blank=True, db_index=True)
    #no_of_times_used = models.PositiveIntegerField(default=0, null=True, blank=True)
    is_active = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateField(default=datetime.date.today)
    expiry_date = models.DateField(default=datetime.date.today)
    is_automate = models.BooleanField(default=True, db_index=True)
    limit_of_usages_per_customer = models.PositiveIntegerField(default=0,blank=True, null=True)
    shop = models.ForeignKey(Shop, related_name='retailer_shop_coupon', on_delete=models.CASCADE, null=True,
                             blank=True)

    coupon_shop_type = models.CharField(max_length=20, choices=SHOP_TYPE_CHOICES, null=True, blank=True)
    coupon_enable_on = models.CharField(max_length=20, choices=ENABLED_ON, default='all', blank=True)

    def __str__(self):
        return self.coupon_name

    @property
    def no_of_times_used(self):
        count = CusotmerCouponUsage.objects.filter(coupon=self).count()
        if count > 0:
            count = CusotmerCouponUsage.objects.filter(coupon=self).count()
        return count

    def save(self, *args, **kwargs):
        if self.is_active == True:
            Coupon.objects.filter(rule=self.rule, is_active=True).update(is_active=False)
            self.is_active = True
        super().save(*args, **kwargs)


class CouponLocation(models.Model):
    coupon = models.ForeignKey(Coupon, related_name='location_coupon', on_delete=models.CASCADE, null=True)
    seller_shop = models.ForeignKey(Shop, related_name='seller_shop_coupon', on_delete=models.CASCADE, blank=True,
                                    null=True)
    buyer_shop = models.ForeignKey(Shop, related_name='buyer_shop_coupon', on_delete=models.CASCADE, blank=True,
                                   null=True)
    city = models.ForeignKey(City, related_name='city_shop_coupon', on_delete=models.CASCADE, blank=True, null=True)


class CusotmerCouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, related_name='customer_coupon', on_delete=models.CASCADE, null=True)
    cart = models.ForeignKey("retailer_to_sp.Cart", related_name='customer_coupon', on_delete=models.CASCADE, null=True)
    shop = models.ForeignKey(Shop, related_name='customer_coupon_usage', on_delete=models.CASCADE, null=True,
                             blank=True)
    product = models.ForeignKey("products.Product", related_name='customer_coupon_product', on_delete=models.CASCADE,
                                null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.coupon.coupon_name


class RuleSetProductMapping(models.Model):
    rule = models.ForeignKey(CouponRuleSet, related_name='product_ruleset', on_delete=models.CASCADE)
    combo_offer_name = models.CharField(max_length=255, null=True)
    purchased_product = models.ForeignKey("products.Product", related_name='purchased_product_coupon',
                                          on_delete=models.CASCADE, null=True)
    retailer_primary_product = models.ForeignKey("pos.RetailerProduct", related_name='retailer_purchased_product_coupon',
                                                  on_delete=models.CASCADE, null=True)
    purchased_product_qty = models.PositiveIntegerField(blank=True, null=True)
    free_product = models.ForeignKey("products.Product", related_name='free_product_coupon', on_delete=models.CASCADE,
                                      null=True, blank=True)
    retailer_free_product = models.ForeignKey("pos.RetailerProduct", related_name='retailer_free_product_coupon',
                                              on_delete=models.CASCADE, null=True, blank=True)
    free_product_qty = models.PositiveIntegerField(blank=True, null=True)
    max_qty_per_use = models.PositiveIntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False, db_index=True)
    start_date = models.DateField(default=datetime.date.today)
    expiry_date = models.DateField(default=datetime.date.today)


    def __str__(self):
        if self.retailer_primary_product:
            return "%s->%s" % (self.retailer_primary_product, self.retailer_free_product)
        else:
            return "%s->%s" % (self.purchased_product, self.free_product)


class RuleSetBrandMapping(models.Model):
    rule = models.ForeignKey(CouponRuleSet, related_name='brand_ruleset', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name='brand_coupon', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# class RuleSetCategoryMapping(models.Model):
#     rule = models.ForeignKey(CouponRuleSet, related_name ='category_ruleset', on_delete=models.CASCADE)
#     category = models.ForeignKey(Category, related_name ='category_coupon', on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

# class RuleAreaMapping(models.Model):
#     rule = models.ForeignKey(CouponRuleSet, related_name ='area_ruleset', on_delete=models.CASCADE)
#     seller_shop = models.ForeignKey(Shop, related_name ='seller_shop_ruleset', on_delete=models.CASCADE, blank=True, null=True)
#     buyer_shop = models.ForeignKey(Shop, related_name ='buyer_shop_ruleset', on_delete=models.CASCADE, blank=True, null=True)
#     city = models.ForeignKey(City, related_name ='city_shop_ruleset', on_delete=models.CASCADE, blank=True, null=True)

class Discount(models.Model):
    """
    Discount for category | Brand | b2c category
    """
    DISCOUNT_TYPE = (
        ('brand', "brand"),
        ('category', "category"),
        ('b2c_category', "b2c category")
    )
    discount_type = models.CharField(max_length=255, choices=DISCOUNT_TYPE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='category_discount', null=True, blank=True)
    b2c_category = models.ForeignKey(B2cCategory, on_delete=models.CASCADE, related_name='b2c_category_discount', null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='Brand_discount', null=True, blank=True)
    discount_value = models.ForeignKey(DiscountValue, on_delete=models.CASCADE, related_name='retailer_discount_value')
    start_price = models.IntegerField()
    end_price = models.IntegerField()
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(default=datetime.date.today)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.category:
            return self.discount_type + " " + self.category.category_name
        else:
            return self.discount_type + " " + self.brand.brand_name

def create_es_index(index):
    """
        Return elastic search index specific to environment
    """
    return "{}-{}".format(es_prefix, index)


@receiver(post_save, sender=Coupon)
def update_elasticsearch(sender, instance=None, created=False, **kwargs):
    """
        Update coupon in es
    """
    # POS Coupons
    if instance.shop:
        try:
            params = get_common_coupon_params(instance)
            coupon_type = instance.coupon_type
            product = None
            if coupon_type == 'catalog':
                response, product = get_catalogue_coupon_params(instance)
            else:
                response = get_cart_coupon_params(instance)
            if 'error' in response:
                error_logger.error(
                    "Could not add coupon to elastic shop {}, coupon {}".format(instance.shop.id, instance.id))
                error_logger.error(response['error'])
                return
            params.update(response)
            es.index(index=create_es_index('rc-{}'.format(instance.shop.id)), id=params['id'], body=params)
            if product:
                product.save()
        except Exception as e:
            error_logger.error("Could not add coupon to elastic shop {}, coupon {}".format(instance.shop.id, instance.id))
            error_logger.error(e)


def get_common_coupon_params(coupon):
    """
        Basic coupon parameters
    """
    params = {
        'id': coupon.id,
        'coupon_code': coupon.coupon_code,
        'coupon_name': coupon.coupon_name,
        'active': coupon.is_active,
        'description': coupon.rule.rule_description,
        'start_date': coupon.start_date,
        'end_date': coupon.expiry_date
    }
    return params


def get_catalogue_coupon_params(coupon):
    """
        Get coupon fields for adding in es for catalog coupons - combo/discount
    """
    product_ruleset = RuleSetProductMapping.objects.get(rule_id=coupon.rule.id)
    if product_ruleset.retailer_free_product:
        # Combo Offer
        params = dict()
        params['coupon_type'] = 'catalogue_combo'
        params['purchased_product'] = product_ruleset.retailer_primary_product.id
        params['free_product'] = product_ruleset.retailer_free_product.id
        params['free_product_name'] = product_ruleset.retailer_free_product.name
        params['purchased_product_qty'] = product_ruleset.purchased_product_qty
        params['free_product_qty'] = product_ruleset.free_product_qty
        return params, product_ruleset.retailer_primary_product
    else:
        return {'error': "Catalogue coupon invalid"}


def get_cart_coupon_params(coupon):
    """
        Get coupon fields for adding in es for cart coupons - discount
    """
    params = dict()
    if coupon.rule.discount:
        params['coupon_type'] = 'cart'
        params['cart_minimum_value'] = coupon.rule.cart_qualifying_min_sku_value
        params['discount'] = coupon.rule.discount.discount_value
        params['is_percentage'] = coupon.rule.discount.is_percentage
        params['is_point'] = coupon.rule.discount.is_point
        params['max_discount'] = coupon.rule.discount.max_discount
    elif coupon.rule.free_product:
        params['coupon_type'] = 'cart_free_product'
        params['cart_minimum_value'] = coupon.rule.cart_qualifying_min_sku_value
        params['free_product'] = coupon.rule.free_product.id
        params['free_product_qty'] = coupon.rule.free_product_qty
    else:
        return {'error': "Cart coupon invalid"}
    return params
