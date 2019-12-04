from django.db import models
from accounts.models import User
from brand.models import Brand
from categories.models import Category
from shops.models import Shop
from addresses.models import City
from django.db.models import F, FloatField, Sum
# Create your models here.
class DiscountValue(models.Model):
    discount_value = models.FloatField(default = 0, null=True, blank=True)
    is_percentage = models.BooleanField(default=False)
    max_discount = models.FloatField(default = 0, null=True, blank=True)

    def __str__(self):
        return str(self.discount_value)

class CouponRuleSet(models.Model):
    rulename = models.CharField(max_length=255, unique=True, null=True)
    rule_description = models.CharField(max_length=255, null=True)
    no_of_users_allowed = models.ManyToManyField(User, blank=True)
    all_users = models.BooleanField(default=False)
    discount_qty_step = models.PositiveIntegerField(default=1, null=True, blank=True)
    discount_qty_amount = models.PositiveIntegerField(default=0, null=True, blank=True)
    discount = models.ForeignKey(DiscountValue, related_name='discount_value_id', on_delete=models.CASCADE, null=True, blank=True)
    is_free_shipment = models.BooleanField(default=False, null=True, blank=True)
    cart_qualifying_min_sku_value = models.PositiveIntegerField(default=0, blank=True, null =True)
    cart_qualifying_min_sku_item = models.PositiveIntegerField(default=0, blank=True, null =True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()

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
    rule = models.ForeignKey(CouponRuleSet, related_name ='coupon_ruleset', on_delete=models.CASCADE)
    coupon_name = models.CharField(max_length=255, null=True)
    coupon_code = models.CharField(max_length=255, null=True)
    limit_per_user_per_day = models.PositiveIntegerField(default=0, null=True, blank=True)
    limit_of_usages = models.PositiveIntegerField(default=0, null=True, blank=True)
    coupon_type = models.CharField(max_length=255, choices=COUPON_TYPE,null=True, blank=True)
    # no_of_times_used = models.PositiveIntegerField(default=0, null=True, blank=True)
    is_display = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()

    def __str__(self):
        return self.coupon_name

    @property
    def no_of_times_used(self):
        count = CusotmerCouponUsage.objects.filter(coupon = self).count()
        if count > 0:
            count = CusotmerCouponUsage.objects.filter(coupon = self).count()
        return count


    def save(self, *args, **kwargs):
        if self.is_active == True:
            Coupon.objects.filter(rule = self.rule, is_active=True).update(is_active=False)
            self.is_active = True
        super().save(*args, **kwargs)

class CouponLocation(models.Model):
    coupon = models.ForeignKey(Coupon, related_name ='location_coupon', on_delete=models.CASCADE, null=True)
    seller_shop = models.ForeignKey(Shop, related_name ='seller_shop_coupon', on_delete=models.CASCADE, blank=True, null=True)
    buyer_shop = models.ForeignKey(Shop, related_name ='buyer_shop_coupon', on_delete=models.CASCADE, blank=True, null=True)
    city = models.ForeignKey(City, related_name ='city_shop_coupon', on_delete=models.CASCADE, blank=True, null=True)


class CusotmerCouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, related_name ='customer_coupon', on_delete=models.CASCADE, null= True)
    cart = models.ForeignKey("retailer_to_sp.Cart", related_name ='customer_coupon', on_delete=models.CASCADE, null=True)
    shop = models.ForeignKey(Shop, related_name='customer_coupon_usage', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey("products.Product", related_name='customer_coupon_product', on_delete=models.CASCADE, null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.coupon.coupon_name


class RuleSetProductMapping(models.Model):
    rule = models.ForeignKey(CouponRuleSet, related_name ='product_ruleset', on_delete=models.CASCADE)
    purchased_product = models.ForeignKey("products.Product", related_name ='purchased_product_coupon', on_delete=models.CASCADE, null=True)
    free_product = models.ForeignKey("products.Product", related_name ='free_product_coupon', on_delete=models.CASCADE, null=True, blank=True)
    max_qty_per_use = models.PositiveIntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return  "%s->%s"%(self.purchased_product, self.free_product)

class RuleSetBrandMapping(models.Model):
    rule = models.ForeignKey(CouponRuleSet, related_name ='brand_ruleset', on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, related_name ='brand_coupon', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

# class RuleSetCategoryMapping(models.Model):
#     rule = models.ForeignKey(CouponRuleSet, related_name ='category_ruleset', on_delete=models.CASCADE)
#     category = models.ForeignKey(Category, related_name ='category_coupon', on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#
# class RuleAreaMapping(models.Model):
#     rule = models.ForeignKey(CouponRuleSet, related_name ='area_ruleset', on_delete=models.CASCADE)
#     seller_shop = models.ForeignKey(Shop, related_name ='seller_shop_ruleset', on_delete=models.CASCADE, blank=True, null=True)
#     buyer_shop = models.ForeignKey(Shop, related_name ='buyer_shop_ruleset', on_delete=models.CASCADE, blank=True, null=True)
#     city = models.ForeignKey(City, related_name ='city_shop_ruleset', on_delete=models.CASCADE, blank=True, null=True)
