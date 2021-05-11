import logging

from django.utils import timezone

from retailer_to_sp.views import initiate_ars
from services.models import CronRunLog

cron_logger = logging.getLogger('cron_log')

def run_ars_cron():
    cron_name = CronRunLog.CRON_CHOICE.ARS_CRON
    if CronRunLog.objects.filter(cron_name=cron_name,
                                 status=CronRunLog.CRON_STATUS_CHOICES.STARTED).exists():
        cron_logger.info("{} already running".format(cron_name))
        return

    cron_log_entry = CronRunLog.objects.create(cron_name=cron_name)
    cron_logger.info('{} | started. Cron log entry-{}'.format(cron_name, cron_log_entry.id))
    try:
        initiate_ars()
    except Exception as e:
        cron_logger.info("Exception in {}, cron log entry-{}, {}".format(cron_name, cron_log_entry.id, e))
        cron_logger.error(e)
    cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.COMPLETED
    cron_log_entry.completed_at = timezone.now()
    cron_logger.info("{} completed, cron log entry-{}".format(cron_name, cron_log_entry.id))
    cron_log_entry.save()