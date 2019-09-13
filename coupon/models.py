from django.db import models
from accounts.models import User
# Create your models here.
class DiscountValue(models.Model):
    discount_value = models.PositiveIntegerField(default=0, null=True, blank=True)
    is_percentage = models.BooleanField(default=False)
    max_discount = models.PositiveIntegerField(default=0, null=True, blank=True)

class CouponRuleSet(models.Model):
    rulename = models.CharField(max_length=255, unique=True, null=True)
    rule_description = models.CharField(max_length=255, null=True)
    no_of_users_allowed = models.ManyToManyField(User, blank=True, null=True)
    discount_qty_step = models.PositiveIntegerField(default=0, null=True, blank=True)
    discount_qty_amount = models.PositiveIntegerField(default=0, null=True, blank=True)
    discount_id = models.ForeignKey(DiscountValue, related_name='discount_value_id' on_delete=models.CASCADE, null=True, blank=True)
    is_free_shipment = models.BooleanField(default=False, null=True, blank=True)
    cart_qualifying_min_sku_value = models.PositiveIntegerField(default=0)
    cart_qualifying_min_sku_item = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(auto_now=True)

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
    rule_id = models.ForeignKey(CouponRuleSet, related_name ='coupon_ruleset' on_delete=models.CASCADE)
    coupon_name = models.CharField(max_length=255, null=True)
    coupon_code = models.CharField(max_length=255, null=True)
    limit_per_user = models.PositiveIntegerField(default=0, null=True, blank=True)
    limit_of_usages = models.PositiveIntegerField(default=0, null=True, blank=True)
    coupon_type = models.CharField(max_length=255, choices=COUPON_TYPE,null=True, blank=True)
