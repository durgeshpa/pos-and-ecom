from django.db.models import Manager

class AdHocReportRequestManager(Manager):
    
    def get_queryset(self):
        return super().get_queryset().filter(report_type='AD')
    
    def create(self, **kwargs):
        kwargs['report_type'] = 'AD'
        return super().create(**kwargs)


class ScheduledReportRequestManager(Manager):
    
    def get_queryset(self):
        return super().get_queryset().filter(report_type='SC')
    
    def create(self, **kwargs):
        kwargs['report_type'] = 'SC'
        return super().create(**kwargs)