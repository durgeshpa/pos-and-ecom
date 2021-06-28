# python imports
import datetime
import logging

# app imports
from coupon.models import Coupon

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