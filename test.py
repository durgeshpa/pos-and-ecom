import os
import django
from wkhtmltopdf.views import PDFTemplateResponse
from django.db.models import F,Sum, Q
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from shops.models import Shop
from products.models import Product, ProductPrice
from wms.common_functions import get_stock, CommonWarehouseInventoryFunctions as CWIF
import math
print(math.ceil(4/50))