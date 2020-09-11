import datetime
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from retailer_to_sp.models import OrderedProduct

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from products.models import Product
from sp_to_gram.tasks import upload_shop_stock
from shops.models import Shop
from wms.common_functions import get_product_stock
import logging

logger = logging.getLogger('django')
info_logger = logging.getLogger('file-info')
logger.info("abcabcabcbbcbbbiuerwuiiwruiwuirui")
info_logger.info("abcabcabc")