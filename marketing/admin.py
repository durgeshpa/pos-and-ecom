from django.contrib import admin
from .models import MLMUser, Referral, PhoneOTP, Token, RewardPoint


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


class ReferralAdmin(admin.ModelAdmin):
    model = Referral
    list_display = ('referral_to', 'referral_by', 'created_at')
    fields = ('referral_to', 'referral_by')


class TokenAdmin(admin.ModelAdmin):
    model = Token
    list_display = ('user', 'token')
    fields = ('user', 'token')


@admin.register(RewardPoint)
class RewardPointAdmin(admin.ModelAdmin):
    list_display = ("user", "direct_users", "indirect_users", "direct_earned", "indirect_earned", "points_used")
    pass


admin.site.register(MLMUser, MLMUserAdmin)
admin.site.register(PhoneOTP, PhoneOTPAdmin)
admin.site.register(Referral, ReferralAdmin)
admin.site.register(Token, TokenAdmin)
