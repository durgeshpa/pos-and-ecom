import logging

from django.utils import timezone

from ars.views import initiate_ars, create_po, mail_category_manager_for_po_approval, populate_daily_average
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


def generate_po_cron():
    """
    Cron to create the PurchaseOrders from the demand generated in the system.
    """
    cron_name = CronRunLog.CRON_CHOICE.PO_CREATION_CRON
    if CronRunLog.objects.filter(cron_name=cron_name,
                                 status=CronRunLog.CRON_STATUS_CHOICES.STARTED).exists():
        cron_logger.info("{} already running".format(cron_name))
        return

    cron_log_entry = CronRunLog.objects.create(cron_name=cron_name)
    cron_logger.info('{} | started. Cron log entry-{}'.format(cron_name, cron_log_entry.id))
    try:
        create_po()
        mail_category_manager_for_po_approval()
    except Exception as e:
        cron_logger.info("Exception in {}, cron log entry-{}, {}".format(cron_name, cron_log_entry.id, e))
        cron_logger.error(e)
    cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.COMPLETED
    cron_log_entry.completed_at = timezone.now()
    cron_logger.info("{} completed, cron log entry-{}".format(cron_name, cron_log_entry.id))
    cron_log_entry.save()


def daily_average_sales_cron():
    populate_daily_average()

