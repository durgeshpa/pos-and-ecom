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

product_id=792
shop_id= 1393
product= Product.objects.filter(id=product_id).last()
shop = Shop.objects.get(id=shop_id)
stock=upload_shop_stock(shop_id,product)
print(stock)
