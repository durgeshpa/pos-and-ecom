import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from elasticsearch import Elasticsearch
from global_config.views import get_config
from django.db import transaction
from products.models import Product
from sp_to_gram.tasks import upload_shop_stock, create_es_index, update_shop_product_es
from shops.models import Shop, ExecutiveFeedback
from wms.common_functions import get_visibility_changes, update_visibility, update_visibility_bulk
from wms.models import WarehouseInventory, InventoryType, InventoryState
from shops.cron import distance

import urllib.parse
import requests
import re
from celery.task import task
from datetime import datetime, date, timedelta
from shops.tasks import set_feedbacks


set_feedbacks()
