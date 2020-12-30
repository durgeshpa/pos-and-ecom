from shops.models import Shop
from wms.models import WarehouseInternalInventoryChange, InventoryType, OrderReserveRelease

warehouse_list = [Shop.objects.get(pk=1393)]
type_new = InventoryType.objects.filter(inventory_type='new').last()


def run():
    for w in warehouse_list:
        fix_warehouse_internal_inventory(w)

def fix_warehouse_internal_inventory(warehouse):
    all_transactions = WarehouseInternalInventoryChange.objects.filter(warehouse=warehouse).order_by('pk')
    for tr in all_transactions:
        if tr.initial_type != type_new:
            WarehouseInternalInventoryChange.objects.create(warehouse=warehouse, sku=tr.sku,
                                                            transaction_type=tr.transaction_type,
                                                            transaction_id=tr.transaction_id,
                                                            inventory_type=tr.initial_type,
                                                            inventory_state=tr.initial_stage, quantity=(-1*tr.quantity))

        new_tr = WarehouseInternalInventoryChange.objects.create(warehouse=warehouse, sku=tr.sku,
                                                                 transaction_type=tr.transaction_type,
                                                                 transaction_id=tr.transaction_id,
                                                                 inventory_type=tr.final_type,
                                                                 inventory_state=tr.final_stage, quantity=tr.quantity)
        order_reserve_entry = OrderReserveRelease.objects.filter(warehouse_internal_inventory_reserve=tr)
        order_release_entry = OrderReserveRelease.objects.filter(warehouse_internal_inventory_release=tr)
        if order_reserve_entry.exists():
            order_reserve_entry.update(warehouse_internal_inventory_reserve=new_tr)
        if order_release_entry.exists():
            order_release_entry.update(warehouse_internal_inventory_release=new_tr)
        tr.delete()
