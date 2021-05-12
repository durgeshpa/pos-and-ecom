from django.contrib import admin
from otp.models import PhoneOTP


class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'otp', 'is_verified', 'attempts', 'expires_in', 'created_at', 'last_otp',
                    'resend_in', 'blocked')
    search_fields = ('phone_number',)
    ordering = ['-created_at']

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(PhoneOTP, PhoneOTPAdmin)
