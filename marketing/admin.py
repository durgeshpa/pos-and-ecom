from django.contrib import admin
from django.utils.html import format_html
from django_admin_listfilter_dropdown.filters import DropdownFilter
from rangefilter.filter import DateTimeRangeFilter

from .models import MLMUser, Referral, PhoneOTP, Token, RewardPoint, Profile, RewardLog
from global_config.models import GlobalConfig
from marketing.forms import RewardPointForm,MLMUserForm
from franchise.models import FranchiseSales
from marketing.filters import UserFilter, MlmUserAutocomplete

class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = (
        'phone_number', 'otp', 'is_verified', 'attempts', 'expires_in', 'created_at', 'last_otp', 'resend_in')
    search_fields = ('phone_number',)
    ordering = ['-created_at']

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MLMUserAdmin(admin.ModelAdmin):
    form = MLMUserForm
    list_display = ['phone_number', 'name', 'email']

    def save_model(self, request, obj, form, change):
        super(MLMUserAdmin, self).save_model(request, obj, form, change)
        user_obj = MLMUser.objects.get(pk=obj.id)
        if form.cleaned_data.get('referral_code'):
            user_obj = MLMUser.objects.get(pk=obj.id)
            Referral.store_parent_referral_user(form.cleaned_data.get('referral_code'), user_obj.referral_code)
        referred = 1 if form.cleaned_data.get('referral_code') else 0
        RewardPoint.welcome_reward(user_obj, referred)

    def has_change_permission(self, request, obj=None):
        return False


class ReferralAdmin(admin.ModelAdmin):
    model = Referral
    list_display = ('referral_to', 'referral_by', 'created_at')
    fields = ('referral_to', 'referral_by')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TokenAdmin(admin.ModelAdmin):
    model = Token
    list_display = ('user', 'token')
    fields = ('user', 'token')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RewardPoint)
class RewardPointAdmin(admin.ModelAdmin):
    form = RewardPointForm
    list_display = ("phone_number", "user_name", "email_id", "redeemable_reward_points", "max_available_discount_inr",
                    "created_at", "modified_at",
                    "direct_users", "indirect_users", "direct_earned", "indirect_earned", "points_used")
    list_filter = [UserFilter]
    try:
        conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
        used_reward_factor = int(conf_obj.value)
    except:
        used_reward_factor = 4

    def phone_number(self, obj):
        return obj.user

    def user_name(self, obj):
        return format_html('<b>%s</b>' % (obj.user.name if obj.user.name else '-'))

    def email_id(self, obj):
        return format_html('<b>%s</b>' % (obj.user.email if obj.user.email else '-'))

    def max_available_discount_inr(self, obj):
        max_av = int((obj.direct_earned + obj.indirect_earned - obj.points_used)/self.used_reward_factor)
        return format_html('<b>%s</b>' % (max_av))

    def redeemable_reward_points(self, obj):
        rrp = obj.direct_earned + obj.indirect_earned - obj.points_used
        return format_html('<b>%s</b>' % (rrp))

    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.conf.urls import url
        urls = super(RewardPointAdmin, self).get_urls()
        urls = [
                   url(
                       r'^mlm-user-autocomplete/$',
                       self.admin_site.admin_view(MlmUserAutocomplete.as_view()),
                       name="mlm-user-autocomplete"
                   ),
               ] + urls
        return urls

    class Media:
        pass


@admin.register(RewardLog)
class RewardLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'transaction_id', 'transaction_points', 'created_at', 'discount', 'changed_by',
                    'purchase_user', 'purchase_invoice', 'user_purchase_shop_location')
    list_filter = [UserFilter, ('transaction_type', DropdownFilter), ('created_at', DateTimeRangeFilter)]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def transaction_points(self, obj):
        return obj.points

    def purchase_user(self, obj):
        if obj.transaction_type == 'direct_reward' or obj.transaction_type == 'indirect_reward':
            sales_obj = FranchiseSales.objects.filter(pk=obj.transaction_id).last()
            return sales_obj.phone_number if sales_obj else '-'
        return '-'

    def user_purchase_shop_location(self, obj):
        if obj.transaction_type == 'direct_reward' or obj.transaction_type == 'indirect_reward':
            sales_obj = FranchiseSales.objects.filter(pk=obj.transaction_id).last()
            return sales_obj.shop_loc if sales_obj else '-'
        return '-'

    def purchase_invoice(self, obj):
        if obj.transaction_type == 'direct_reward' or obj.transaction_type == 'indirect_reward':
            sales_obj = FranchiseSales.objects.filter(pk=obj.transaction_id).last()
            return sales_obj.invoice_number if sales_obj else '-'
        return '-'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(RewardLogAdmin, self).get_urls()
        urls = [
                   url(
                       r'^mlm-user-autocomplete/$',
                       self.admin_site.admin_view(MlmUserAutocomplete.as_view()),
                       name="mlm-user-autocomplete"
                   ),
               ] + urls
        return urls

    class Media:
        pass


admin.site.register(MLMUser, MLMUserAdmin)
admin.site.register(PhoneOTP, PhoneOTPAdmin)
admin.site.register(Referral, ReferralAdmin)
admin.site.register(Token, TokenAdmin)
admin.site.register(Profile)
