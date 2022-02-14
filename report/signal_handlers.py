# -*- coding: utf-8 -*-

from report.tasks import (HostReportGenerator, 
                          RedashReportGenerator,
                          ScheduledHostReportGenerator, 
                          ScheduledRedashReportGenerator)

def async_report_post_save(sender, instance, created, *args, **kwargs):
    if instance.report_type  == 'AD':
        if instance.report_choice.source == 'HT':
            #HostReportGenerator.delay(instance.id)
            HostReportGenerator.delay(instance.id)
        else:
            #RedashReportGenerator.delay(instance.id)
            RedashReportGenerator.delay(instance.id)
            pass
    else:
        if instance.report_choice.source == 'HT':
            #ScheduledHostReportGenerator.delay(instance.id)
            HostReportGenerator.delay(instance.id)
        else:

            #ScheduledRedashReportGenerator.delay(instance.id)
            RedashReportGenerator.delay(instance.id)
            pass
