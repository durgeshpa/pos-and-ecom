# python imports
import datetime
import logging

# app imports
from .models import ProductCapping

# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def deactivate_capping():
    """
        Cron job for set status False in ProductCapping model if end date is less then current date
        :return:
        """
    try:
        cron_logger.info('cron job for deactivate the capping|started')
        today = datetime.datetime.today()
        capping_obj = ProductCapping.objects.filter(status=True, end_date__lt=today.date())
        if capping_obj:
            capping_obj.update(status=False)
            cron_logger.info('object is successfully updated from Product Capping model for status False')
        else:
            cron_logger.info('no object is getting from Product Capping model for status False')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in capping status deactivated cron')
