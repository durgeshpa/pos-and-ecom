# python imports
import datetime
import logging

# app imports
from shops.models import Shop

# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def run():
    """
        Cron job for refactor warehouse_code when shop_type is Franchise
        :return:
    """
    try:
        cron_logger.info('Cron job for refactor warehouse_code when shop_type is Franchise|started')
        shop_franchise = Shop.objects.filter(shop_type=5)   # shop_type = Franchise
        if shop_franchise:
            for franchise in shop_franchise:
                franchise.warehouse_code = '0'+franchise.warehouse_code
                franchise.save()
            cron_logger.info('warehouse_code is successfully updated')
        else:
            cron_logger.info('no Shop found with shop_type Franchise')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in warehouse_code_refactor cron')