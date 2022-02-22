from django.db import models

class BeatPerformanceReportManager(models.Manager):
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, 
                                             day_beat_plan__executive_feedback__in=[1,2,3]).distinct('id')
