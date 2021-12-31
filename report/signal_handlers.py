# -*- coding: utf-8 -*-

from report.tasks import (ReportGenerator,)

def async_report_post_save(sender, instance, created, *args, **kwargs):
    if instance.report_type  == 'AD':
        ReportGenerator.delay(instance.id)
        #ReportGenerator(instance.id)
    else:
        pass
