# -*- coding: utf-8 -*-

from report.tasks import (HostReportGenerator, 
                          RedashReportGenerator,
                          ScheduledHostReportGenerator, 
                          ScheduledRedashReportGenerator)

def async_report_post_save(sender, instance, created, *args, **kwargs):
    if instance.report_type  == 'AD':
        if instance.source == 'HT':
            HostReportGenerator.delay(instance.id)
            #HostReportGenerator(instance.id)
        else:
            #RedashReportGenerator.delay(instance.id)
            #RedashReportGenerator(instance.id)
            pass
    else:
        if instance.source == 'HT':
            ScheduledHostReportGenerator.delay(instance.id)
            #ScheduledHostReportGenerator(instance.id)
        else:
            #ScheduledRedashReportGenerator.delay(instance.id)
            #ScheduledRedashReportGenerator(instance.id)
            pass
