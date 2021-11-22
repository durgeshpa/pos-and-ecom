# python imports
import datetime
import logging

# app imports
from wms.models import PosInventory
from services.models import  PosInventoryHistoric
from coupon.models import Coupon
from retailer_backend.common_function import bulk_create
# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def deactivate_coupon_combo_offer():
    """
        Cron job for set status False in Coupon & RuleSetProductMapping model if expiry date is less then current date
        :return:
    """
    try:
        cron_logger.info('cron job for deactivate the coupon_combo_offer|started')
        today = datetime.datetime.today()
        coupon_obj = Coupon.objects.filter(is_active=True, expiry_date__lt=today.date(),
                                           shop__shop_type__shop_type='f')
        if coupon_obj:
            coupon_obj.update(is_active=False)
            cron_logger.info('object is successfully updated from Coupon model for status False')
        else:
            cron_logger.info('no object is getting from Coupon & RuleSetProductMapping Capping model for status False')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in Coupon/RuleSetProductMapping status deactivated cron')

def pos_archive_inventory_cron():

    try:
        cron_logger.info("POS : Archiving POS inventory data started at {}".format(datetime.datetime.now()))
        pos_inventory_list = PosInventory.objects.all()
        bulk_create(PosInventoryHistoric, pos_inventory_data_generator(pos_inventory_list))
        cron_logger.info("POS : Archiving POS inventory data ended at {}".format(datetime.datetime.now()))
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in pos_archive_inventory')


def pos_inventory_data_generator(data):
    for row in data:
        yield PosInventoryHistoric(
                                    product=row.product,
                                    quantity=row.quantity,
                                    inventory_state=row.inventory_state,
                                    created_at=row.created_at,
                                    modified_at=row.modified_at
                                    )
