import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from wms.models import Bin
from gram_to_brand.models import GRNOrderProductMapping
from sp_to_gram.tasks import get_warehouse_stock
from products.models import Product

product = Product.objects.filter(product_sku='DBEVBEVMDE00000012').last()
print(product)
print(product.id)
# all_products = get_warehouse_stock(600,product)
# for product1 in all_products:
#     print(product1)