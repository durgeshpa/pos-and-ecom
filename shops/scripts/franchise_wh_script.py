# python imports
import logging
import traceback

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
        shop_franchise = Shop.objects.filter(shop_type__shop_type='f', approval_status=2).order_by('created_at')  # shop_type = Franchise
        count = 0
        if shop_franchise:
            for franchise in shop_franchise:
                warehouse_code = str(format(count, '03d'))
                Shop.objects.filter(id=franchise.id).update(warehouse_code=warehouse_code, shop_code='F')
                count += 1
                print("shop updated {} code {}".format(franchise.shop_name, franchise.warehouse_code))
    except Exception as e:
        traceback.print_exc()
