from django.contrib import admin
from .models import MLMUser, Referral


class ReferralAdmin(admin.ModelAdmin):
    model = Referral
    list_display = ('referral_to', 'referral_by', 'created_at')
    fields = ('referral_to', 'referral_by')

admin.site.register(Referral, ReferralAdmin)
admin.site.register(MLMUser)
