from django.db.models import Manager

class ScheduledReportRequestManager(Manager):
    
    def get_queryset(self):
        return super().get_queryset().filter(report_type='SC')
    
    def create(self, **kwargs):
        kwargs['report_type'] = 'SC'
        return super().create(**kwargs)