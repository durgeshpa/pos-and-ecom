# python imports
import logging

from retailer_to_sp.views import generate_e_invoice
from sp_to_gram.tasks import upload_all_products_in_es

info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def all_products_es_refresh():
    cron_logger.info('RefreshEs| Started for index named all_products')
    try:
        upload_all_products_in_es()
        cron_logger.info_logger('RefreshEs has been done for index named all_products')
    except Exception as e:
        cron_logger.error('Exception during ES refresh .........', e)


def generate_e_invoice_cron():
    generate_e_invoice()


