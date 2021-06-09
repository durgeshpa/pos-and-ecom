# python imports
import logging

# app imports
from shops.models import Shop, warehouse_code_generator

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run():
    """
        refactor warehouse_code when shop_type is Franchise
        :return:
    """
    set_warehouse_code()


def set_warehouse_code():
    try:
        info_logger.info('refactor warehouse_code when shop_type is Franchise|started')
        shop_franchise = Shop.objects.filter(shop_type__shop_type='f').order_by('-created_at')  # shop_type = Franchise
        count = 0
        if shop_franchise:
            for franchise in shop_franchise:
                warehouse_code = str(format(count, '03d'))
                franchise.warehouse_code = warehouse_code
                franchise.shop_code = 'F'
                franchise.save()
                count += 1
            info_logger.info('warehouse_code is successfully updated')
        else:
            info_logger.info('no Shop found with shop_type Franchise')
    except Exception as e:
        error_logger.error(e)
        error_logger.error('Exception in warehouse_code_refactor')
