from django.contrib import admin
from .forms import ScheduledRedashForm
from .models import RedashScheduledReport
# Register your models here.


class RedashReportAdmin(admin.ModelAdmin):
    """
        List display for Scheduled reports in Django admin
    """
    model = RedashScheduledReport
    form = ScheduledRedashForm
    list_display = ['recipients', 'schedule', ]


admin.site.register(RedashScheduledReport, RedashReportAdmin)