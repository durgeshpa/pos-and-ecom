import datetime
import os
import sys
import django
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')
django.setup()
from shops.models import Shop
from wms.models import InventoryState, WarehouseInventory

from sp_to_gram.models import OrderedProduct, OrderedProductMapping, StockAdjustment, StockAdjustmentMapping, \
    OrderedProductReserved

mrps = []
products = None
product_list = {}
shop = Shop.objects.filter(pk=1393).last()
# sp_grn_product = shop.get_shop_stock(shop_obj)
# products = sp_grn_product.values('product').distinct()
bin_inventory_state = InventoryState.objects.filter(inventory_state="available").last()
products = WarehouseInventory.objects.filter(warehouse=shop, inventory_state=bin_inventory_state)

for myproduct in products:
    product_temp = {}
    if myproduct.sku.product_sku in product_list:
        product_temp = product_list[myproduct.sku.product_sku]
        product_temp[myproduct.inventory_type.inventory_type] = myproduct.quantity
    else:
        product_mrp = myproduct.sku.product_pro_price.filter(seller_shop=shop, approval_status=2)
        product_temp = {'sku': myproduct.sku.product_sku, 'name': myproduct.sku.product_name,
                        myproduct.inventory_type.inventory_type: myproduct.quantity,
                        'mrp': product_mrp.last().mrp if product_mrp.exists() else ''}

    product_list[myproduct.sku.product_sku] = product_temp

for product_sku in product_list:
    print(product_list[product_sku]['mrp'])

