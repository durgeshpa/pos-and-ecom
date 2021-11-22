from django.db.models import Sum, F

from products.models import Product
from shops.models import Shop
from wms.common_functions import CommonWarehouseInventoryFunctions
from wms.models import BinInventory, WarehouseInventory, InventoryState, InventoryType, WarehouseInternalInventoryChange
warehouse_list = [Shop.objects.get(pk=1393)]
# warehouse_list = [Shop.objects.get(pk=32154), Shop.objects.get(pk=600)]
state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()

type_normal = InventoryType.objects.filter(inventory_type='normal').last()
type_damaged = InventoryType.objects.filter(inventory_type='damaged').last()
type_expired = InventoryType.objects.filter(inventory_type='expired').last()
type_missing = InventoryType.objects.filter(inventory_type='missing').last()

inventory_type_dict = {
    type_normal.id: type_normal,
    type_damaged.id: type_damaged,
    type_expired.id: type_expired,
    type_missing.id: type_missing
}
inventory_types_ids = inventory_type_dict.keys()


def run():
    for w in warehouse_list:
        populate_total_available_to_be_picked(w)


def is_warehouse_entry_exists(warehouse, sku_id, inventory_type, inventory_state):
    return WarehouseInventory.objects.filter(warehouse=warehouse,
                                             sku=sku_id,
                                             inventory_type=inventory_type,
                                             inventory_state=inventory_state).exists()


def populate_total_available_to_be_picked(warehouse):
    bin_inventory = BinInventory.objects.filter(warehouse=warehouse)\
                                        .values('inventory_type_id', 'sku_id')\
                                        .annotate(available=Sum('quantity'), to_be_picked=Sum('to_be_picked_qty'))
    sku_inventory_type_dict = {}
    for item in bin_inventory:
        print(item)
        if sku_inventory_type_dict.get(item['sku_id']) is None:
            sku_inventory_type_dict[item['sku_id']] = list(inventory_types_ids)

        product = Product.objects.filter(product_sku=item['sku_id']).last()
        total_available_qty = item['available'] + item['to_be_picked']
        tr_type = "New Stage"
        tr_id = "New Stage"

        if not is_warehouse_entry_exists(warehouse, item['sku_id'], item['inventory_type_id'], state_total_available):
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                warehouse, product, inventory_type_dict[item['inventory_type_id']], state_total_available,
                total_available_qty, tr_type, tr_id
            )

        if not is_warehouse_entry_exists(warehouse, item['sku_id'], item['inventory_type_id'], state_to_be_picked):
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                warehouse, product, inventory_type_dict[item['inventory_type_id']], state_to_be_picked,
                item['to_be_picked'],  tr_type, tr_id
            )

        sku_inventory_type_dict[item['sku_id']].remove(item['inventory_type_id'])

    for sku_id, inventory_types in sku_inventory_type_dict.items():
        for i in inventory_types:
            print('SKU {}, Inventory Type {} '.format(sku_id, item['inventory_type_id']))
            if not is_warehouse_entry_exists(warehouse, sku_id, i, state_total_available):
                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                    warehouse, product, inventory_type_dict[i], state_total_available,
                    0,  tr_type, tr_id
                )

            if not is_warehouse_entry_exists(warehouse, sku_id, i, state_to_be_picked):
                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                    warehouse, product, inventory_type_dict[i], state_to_be_picked,
                    0,  tr_type, tr_id
                )
