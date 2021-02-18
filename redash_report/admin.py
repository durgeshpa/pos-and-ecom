from django.contrib import admin
from .forms import RedashForm
from .models import RedashScheduledReport,MailRecipient
# Register your models here.


class RedashReportAdmin(admin.ModelAdmin):
    """
        List display for Scheduled reports in Django admin
    """
    model = RedashScheduledReport
    # list_display = ('id', 'recipients_list__mail_address')
    form = RedashForm


admin.site.register(RedashScheduledReport, RedashReportAdmin)