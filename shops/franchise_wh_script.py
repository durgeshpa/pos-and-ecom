# python imports
import datetime
import logging

# app imports
from .models import Shop

# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def warehouse_code_refactor():
    """
        Cron job for refactor warehouse_code for shop_type Franchise
        :return:
    """
    try:
        cron_logger.info('Cron job for refactor warehouse_code for shop_type Franchise|started')
        shop_franchise = Shop.object.filter(shop_type='Franchise')
        if shop_franchise:
            shop_franchise.update(warehouse_code=0+shop_franchise.warehouse_code)
            cron_logger.info('warehouse_code is successfully updated')
        else:
            cron_logger.info('no warehouse_code for shop_type Franchise')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in warehouse_code_refactor cron')