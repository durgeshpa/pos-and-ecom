from django.contrib import admin
from .forms import ScheduledRedashForm
from .models import RedashScheduledReport


class RedashReportAdmin(admin.ModelAdmin):

    model = RedashScheduledReport
    form = ScheduledRedashForm
    """
        List display for Scheduled reports in Django admin
    """
    list_display = ['recipients', 'schedule', ]


admin.site.register(RedashScheduledReport, RedashReportAdmin)