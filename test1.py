import django
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from django.db import transaction
from products.models import Product
from sp_to_gram.tasks import upload_shop_stock
from shops.models import Shop
from wms.common_functions import get_visibility_changes, update_visibility, update_visibility_bulk
from wms.models import WarehouseInventory, InventoryType, InventoryState


# product = Product.objects.filter(pk=7983).last()
# shop = Shop.objects.filter(pk=32154).last()
# visibility_changes = get_visibility_changes(shop, product)
# print(visibility_changes)




update_visibility_bulk(32154)