import logging
from datetime import datetime, timedelta, timezone

from django.db.models import Q

from accounts.models import User
from global_config.views import get_config
from gram_to_brand.models import GRNOrder
from services.models import CronRunLog
from shops.models import ParentRetailerMapping, Shop
from warehouse_consolidation.models import AutoOrderProcessing, SourceDestinationMapping
from warehouse_consolidation.views import AutoOrderProcessor, process_next

cron_logger = logging.getLogger('cron-log')

def initiate_auto_order_processing():
    cron_name = CronRunLog.CRON_CHOICE.AUTO_ORDER_PROCESSING_CRON
    if CronRunLog.objects.filter(cron_name=cron_name,
                                 status=CronRunLog.CRON_STATUS_CHOICES.STARTED).exists():
        cron_logger.info("{} already running".format(cron_name))
        return

    cron_log_entry = CronRunLog.objects.create(cron_name=cron_name)
    cron_logger.info("{} started, cron log entry-{}"
                     .format(cron_log_entry.cron_name, cron_log_entry.id))
    try:
        procesee_auto_order()
        cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.COMPLETED
        cron_log_entry.completed_at = timezone.now()
        cron_logger.info("{} completed, cron log entry-{}"
                         .format(cron_log_entry.cron_name, cron_log_entry.id))
    except Exception as e:
        cron_log_entry.status = CronRunLog.CRON_STATUS_CHOICES.ABORTED
        cron_logger.info("{} aborted, cron log entry-{}"
                         .format(cron_name, cron_log_entry.id))
        cron_logger.error(e)
    cron_log_entry.save()