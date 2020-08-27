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
from wms.common_functions import InternalWarehouseChange
from wms.models import StockMovementCSVUpload,InventoryType,InventoryState
print(math.ceil(4/50))
csv_instance = StockMovementCSVUpload.objects.filter(pk=1).last()
type_normal = InventoryType.objects.filter(inventory_type="normal").last()
state_available=InventoryState.objects.filter(inventory_state="available").last()
state_picked=InventoryState.objects.filter(inventory_state="picked").last()
state_ordered=InventoryState.objects.filter(inventory_state="ordered").last()
warehouse = Shop.objects.filter(pk=1339).last()
sku = Product.objects.filter(pk=3885).last()
InternalWarehouseChange.create_warehouse_inventory_change(warehouse,sku,"pickup_complete",123,type_normal,state_ordered,
                                                         type_normal, state_picked,10,None)