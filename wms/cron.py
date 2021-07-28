import logging
from datetime import datetime
from math import floor

from django.db import transaction
from django.db.models import F, Subquery, OuterRef, Prefetch

from products.models import Product
from wms import common_functions
from wms.common_functions import CommonBinInventoryFunctions, CommonWarehouseInventoryFunctions
from wms.models import BinInventory, In, InventoryType

cron_logger = logging.getLogger('cron_log')

type_normal = InventoryType.objects.get(inventory_type='normal')


def create_move_discounted_products():
    inventory = BinInventory.objects.filter(inventory_type__inventory_type='normal', quantity__gt=0) \
        .prefetch_related('sku__parent_product') \
        .prefetch_related(Prefetch('sku__ins', queryset=In.objects.all().order_by('-created_at'), to_attr='latest_in'))[:100]

    for i in inventory:
        print(i.sku_id)
        discounted_life_percent = i.sku.parent_product.discounted_life_percent
        print(discounted_life_percent)
        expiry_date = i.sku.latest_in[0].expiry_date
        print(expiry_date)
        manufacturing_date = i.sku.latest_in[0].manufacturing_date
        print(manufacturing_date)
        product_life = expiry_date - manufacturing_date
        print (product_life)
        today = datetime.today().date()
        remaining_life = expiry_date - today
        print (remaining_life)
        discounted_life = floor(product_life.days * discounted_life_percent / 100)
        print (discounted_life)
        if discounted_life >= remaining_life.days:
            print("product to be moved to discounted")
            discounted_product_sku = 'D'+i.sku_id
            discounted_product = Product.objects.get_or_create(product_sku=discounted_product_sku,
                                                               product_type=Product.PRODUCT_TYPE_CHOICE.DISCOUNTED,
                                                               parent_product=i.sku.parent_product,
                                                               reason_for_child_sku='near_expiry',
                                                               product_name=i.sku.product_name,
                                                               product_ean_code=i.sku.product_ean_code,
                                                               product_mrp=i.sku.product_mrp,
                                                               weight_value=i.sku.weight_value,
                                                               weight_unit=i.sku.weight_unit,
                                                               repackaging_type=i.sku.repackaging_type
                                                               )
            with transaction.atomic():
                CommonBinInventoryFunctions.update_bin_inventory_with_transaction_log(
                                                i.warehouse, i.bin, i.sku, i.batch_id, i.inventory_type, i.inventory_type,
                                                -1*i.quantity, True, 'moved_to_discounted', 1)
                CommonBinInventoryFunctions.update_bin_inventory_with_transaction_log(
                                                i.warehouse, i.bin, discounted_product, i.batch_id, i.inventory_type, i.inventory_type,
                                                i.quantity, True, 'added_as_discounted', 1)
                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                                i.warehouse, i.sku, i.inventory_type, i.inventory_state, -1*i.quantity,
                                                            'moved_to_discounted', 1)
                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                                i.warehouse, discounted_product, i.inventory_type, i.inventory_state, i.quantity,
                                                            'added_as_discounted', 1)


