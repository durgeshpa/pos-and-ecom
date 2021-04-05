# python imports
import logging

# app imports
from shops.models import Shop

# logger configuration
info_logger = logging.getLogger('file-info')


def run():
    """
        refactor warehouse_code when shop_type is Franchise
        :return:
    """
    try:
        info_logger.info('refactor warehouse_code when shop_type is Franchise|started')
        shop_franchise = Shop.objects.filter(shop_type=5)   # shop_type = Franchise
        if shop_franchise:
            for franchise in shop_franchise:
                franchise.warehouse_code = '0'+franchise.warehouse_code
                franchise.save()
            info_logger.info('warehouse_code is successfully updated')
        else:
            info_logger.info('no Shop found with shop_type Franchise')
    except Exception as e:
        info_logger.error(e)
        info_logger.error('Exception in warehouse_code_refactor')