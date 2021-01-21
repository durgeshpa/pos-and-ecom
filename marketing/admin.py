from django.contrib import admin
from django.utils.html import format_html

from .models import MLMUser, Referral, PhoneOTP, Token, RewardPoint, Profile, RewardLog
from global_config.models import GlobalConfig
from marketing.forms import RewardPointForm

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
    model = MLMUser
    list_display = ['phone_number', 'name', 'email']

    def has_add_permission(self, request, obj=None):
        return False

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
    try:
        conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
        used_reward_factor = int(conf_obj.value)
    except:
        used_reward_factor = 3

    def phone_number(self, obj):
        return obj.user

    def user_name(self, obj):
        return format_html('<b>%s</b>' % (obj.user.name))

    def email_id(self, obj):
        return format_html('<b>%s</b>' % (obj.user.email))

    def max_available_discount_inr(self, obj):
        max_av = self.used_reward_factor * (obj.direct_earned + obj.indirect_earned - obj.points_used)
        return format_html('<b>%s</b>' % (max_av))

    def redeemable_reward_points(self, obj):
        rrp = obj.direct_earned + obj.indirect_earned - obj.points_used
        return format_html('<b>%s</b>' % (rrp))

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RewardLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'transaction_id', 'points', 'discount', 'changed_by',
                    'created_at', 'modified_at')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(MLMUser, MLMUserAdmin)
admin.site.register(PhoneOTP, PhoneOTPAdmin)
admin.site.register(Referral, ReferralAdmin)
admin.site.register(Token, TokenAdmin)
admin.site.register(Profile)
admin.site.register(RewardLog, RewardLogAdmin)
