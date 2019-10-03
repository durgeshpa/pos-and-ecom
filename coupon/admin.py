from django.contrib import admin
from .models import *
from retailer_backend.admin import InputFilter
from django.db.models import Q
from import_export.admin import ExportActionMixin
from products.admin import ExportCsvMixin
from admin_auto_filters.filters import AutocompleteFilter
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .resources import RuleSetProductMappingResource

class DiscountValueAdmin( admin.ModelAdmin):
    list_display = ('discount_value', 'is_percentage', 'max_discount')

class CouponRuleSetAdmin( admin.ModelAdmin):
    list_display = ('rulename', 'rule_description', 'all_users', 'discount_qty_step', 'discount_qty_amount', 'discount', 'is_free_shipment', 'cart_qualifying_min_sku_value', 'cart_qualifying_min_sku_item', 'is_active', 'created_at', 'expiry_date')

class CouponAdmin( admin.ModelAdmin):
    list_display = ('coupon_code', 'coupon_name', 'rule', 'limit_per_user', 'limit_of_usages', 'coupon_type', 'no_of_times_used', 'is_display', 'is_active', 'created_at', 'expiry_date')

class CusotmerCouponUsageAdmin( admin.ModelAdmin):
    list_display = ('coupon', 'cart', 'shop', 'times_used')

class RuleSetProductMappingAdmin(ImportExportModelAdmin):
    resource_class = RuleSetProductMappingResource
    list_display = ('purchased_product', 'free_product', 'rule', 'max_qty_per_use', 'created_at')

# class RuleSetBrandMappingAdmin( admin.ModelAdmin):
#     list_display = ('rule', 'brand', 'created_at')
#
# class RuleSetCategoryMappingAdmin( admin.ModelAdmin):
#     list_display = ('rule', 'category', 'created_at')
#
# class RuleAreaMappingAdmin( admin.ModelAdmin):
#     list_display = ('rule', 'seller_shop', 'buyer_shop', 'city')

class CouponLocationAdmin( admin.ModelAdmin):
    list_display = ('coupon', 'seller_shop', 'buyer_shop', 'city')



admin.site.register(DiscountValue,DiscountValueAdmin)
admin.site.register(CouponRuleSet,CouponRuleSetAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(CusotmerCouponUsage, CusotmerCouponUsageAdmin)
admin.site.register(RuleSetProductMapping, RuleSetProductMappingAdmin)
# admin.site.register(RuleSetBrandMapping, RuleSetBrandMappingAdmin)
# admin.site.register(RuleSetCategoryMapping, RuleSetCategoryMappingAdmin)
# admin.site.register(RuleAreaMapping, RuleAreaMappingAdmin)
admin.site.register(CouponLocation, CouponLocationAdmin)
