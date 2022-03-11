# python imports
import logging

# logger configuration
from sp_to_gram.tasks import upload_shop_stock

info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def all_products_es_refresh():
    cron_logger.info('RefreshEs| Started for index named all_products')
    try:
        shop_id = None
        upload_shop_stock(shop_id)
        cron_logger.info_logger('RefreshEs has been done for index named all_products')
    except Exception as e:
        cron_logger.error('Exception during ES refresh .........', e)
