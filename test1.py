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


# product = Product.objects.filter(pk=7983).last()
# shop = Shop.objects.filter(pk=32154).last()
# visibility_changes = get_visibility_changes(shop, product)
# print(visibility_changes)

es = Elasticsearch(["https://search-gramsearch-7ks3w6z6mf2uc32p3qc4ihrpwu.ap-south-1.es.amazonaws.com"])
def update_product_es(shop_id, product_id,**kwargs):
	try:
		print("Query is")
		print(kwargs)
		es.update(index=create_es_index(shop_id),id=product_id,body={"doc":kwargs},doc_type='product')
	except Exception as e:
		print("exception %s",e)
		update_shop_product_es(shop_id,product_id)

update_product_es(1393,24499,visible=True)