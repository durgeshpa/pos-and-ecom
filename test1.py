
import django
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from elasticsearch import Elasticsearch

from django.db import transaction
from products.models import Product
from sp_to_gram.tasks import upload_shop_stock, create_es_index, update_shop_product_es
from shops.models import Shop
from wms.common_functions import get_visibility_changes, update_visibility, update_visibility_bulk
from wms.models import WarehouseInventory, InventoryType, InventoryState


import urllib.parse
import requests
import re
from retailer_to_sp.api.v1.views import resend_invoice
from datetime import datetime

resend_invoice(370354,7092)