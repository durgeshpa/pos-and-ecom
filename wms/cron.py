import logging
from datetime import datetime
from math import floor

from django.db import transaction
from django.db.models import F, Subquery, OuterRef, Prefetch

from products.models import Product
from wms import common_functions
from wms.common_functions import CommonBinInventoryFunctions, CommonWarehouseInventoryFunctions
from wms.models import BinInventory, In, InventoryType

cron_logger = logging.getLogger('cron_log')

type_normal = InventoryType.objects.get(inventory_type='normal')


def create_move_discounted_products():
    cron_logger.info('create_move_discounted_products|started')
    create_move_discounted_products()
    cron_logger.info('create_move_discounted_products|completed')