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
from admin_auto_filters.filters import AutocompleteFilter
from daterange_filter.filter import DateRangeFilter
from retailer_backend.admin import InputFilter

class CouponNameFilter(InputFilter):
    parameter_name = 'coupon_name'
    title = 'Coupon Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(coupon_name__icontains=self.value())
            )

class CouponCodeFilter(InputFilter):
    parameter_name = 'coupon_code'
    title = 'Coupon Code'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(coupon_code__icontains=self.value())
            )

class RuleNameFilter(InputFilter):
    parameter_name = 'rulename'
    title = 'Rule Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(
                Q(rulename__icontains=self.value())
            )

class RuleSetFilter(AutocompleteFilter):
    title = 'Rule Set' # display title
    field_name = 'rule' # name of the foreign key field

class DiscountValueAdmin(admin.ModelAdmin):
    list_display = ('discount_value', 'is_percentage', 'max_discount')

class CouponRuleSetAdmin( admin.ModelAdmin):
    search_fields = ('rulename',)
    list_filter = [RuleNameFilter, 'is_active', ('created_at', DateRangeFilter), ('expiry_date', DateRangeFilter)]
    list_display = ('rulename', 'rule_description', 'all_users', 'discount_qty_step', 'discount_qty_amount', 'discount', 'is_free_shipment', 'cart_qualifying_min_sku_value', 'cart_qualifying_min_sku_item', 'is_active', 'created_at', 'expiry_date')

class CouponAdmin( admin.ModelAdmin):
    fields = ('coupon_code', 'coupon_name', 'rule', 'limit_per_user_per_day', 'limit_of_usages', 'coupon_type', 'no_of_times_used', 'is_active', 'expiry_date')
    list_display = ('coupon_code', 'coupon_name', 'rule', 'limit_per_user_per_day', 'limit_of_usages', 'coupon_type', 'no_of_times_used', 'is_active', 'created_at', 'expiry_date')
    list_filter = (RuleSetFilter, CouponNameFilter, CouponCodeFilter,'coupon_type', 'is_active')
    readonly_fields = ('no_of_times_used',)

    class Media:
        pass

class CusotmerCouponUsageAdmin( admin.ModelAdmin):
    list_display = ('coupon', 'cart', 'shop', 'product', 'times_used')

class RuleSetProductMappingAdmin(ImportExportModelAdmin):
    resource_class = RuleSetProductMappingResource
    list_display = ('purchased_product', 'free_product', 'rule', 'max_qty_per_use', 'created_at')

class RuleSetBrandMappingAdmin( admin.ModelAdmin):
    list_display = ('rule', 'brand', 'created_at')
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
admin.site.register(RuleSetBrandMapping, RuleSetBrandMappingAdmin)
# admin.site.register(RuleSetCategoryMapping, RuleSetCategoryMappingAdmin)
# admin.site.register(RuleAreaMapping, RuleAreaMappingAdmin)
admin.site.register(CouponLocation, CouponLocationAdmin)
