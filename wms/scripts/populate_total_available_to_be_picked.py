from django.db.models import Sum, F

from shops.models import Shop
from wms.models import BinInventory, WarehouseInventory, InventoryState

warehouse_list = [Shop.objects.get(pk=1393)]
state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()


def run():
    for w in warehouse_list:
        populate_total_available_to_be_picked(w)

def populate_total_available_to_be_picked(warehouse):
    bin_inventory = BinInventory.objects.filter(warehouse=warehouse)\
                                        .values('inventory_type_id', 'sku_id')\
                                        .annotate(available=Sum('quantity'), to_be_picked=Sum('to_be_picked_qty'))
    for item in bin_inventory:
        print(item)
        total_available_qty = item['available'] + item['to_be_picked']

        WarehouseInventory.objects.create(warehouse=warehouse, inventory_type_id=item['inventory_type_id'],
                                          inventory_state=state_total_available, sku_id=item['sku_id'],
                                          quantity=total_available_qty, in_stock=True)

        WarehouseInventory.objects.create(warehouse=warehouse, inventory_type_id=item['inventory_type_id'],
                                          inventory_state=state_to_be_picked, sku_id=item['sku_id'],
                                          quantity=item['to_be_picked'], in_stock=True)

