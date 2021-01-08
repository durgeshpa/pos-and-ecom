from django.contrib import admin
from .models import Referral, MLMUser


class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referral_to', 'referral_by', 'created_at')

admin.site.register(Referral, ReferralAdmin)
admin.site.register(MLMUser)
