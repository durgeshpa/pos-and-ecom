from django.db.models import Count, Sum

from shops.models import Shop
from wms.models import WarehouseInventory, InventoryType, InventoryState, BinInventory

type_normal = InventoryType.objects.filter(inventory_type='normal').last()
state_available = InventoryState.objects.filter(inventory_state='available').last()
state_ordered = InventoryState.objects.filter(inventory_state='ordered').last()
state_reserved = InventoryState.objects.filter(inventory_state='reserved').last()

w_query_set = WarehouseInventory.objects.filter(inventory_type=type_normal)
warehouse = [Shop.objects.get(pk=32154), Shop.objects.get(pk=600)]
inventory_state_list = [state_available, state_reserved, state_ordered]

def run():
    for w in warehouse:
        for i in inventory_state_list:
            fix_duplicate_entry(w, i)


def fix_duplicate_entry(warehouse, inventory_state):
    warehouse_entries = w_query_set.filter(warehouse=warehouse, inventory_state=inventory_state)\
                                 .values('sku')\
                                 .annotate(count=Count('id')).filter(count__gt=1)

    print('warehouse{},  inventory type {}, inventory state {}, count {}'
          .format(warehouse, type_normal, inventory_state, warehouse_entries.count()))

    for entry in warehouse_entries:
        print('SKU {}, count {}' .format(entry['sku'], entry['count']))

        if inventory_state == state_available:
            fix_duplicate_available(warehouse, entry['sku'])

        if inventory_state == state_reserved:
            fix_duplicate_reserved(warehouse, entry['sku'])


def fix_duplicate_reserved(warehouse, sku):
    duplicate_reserved_entries = w_query_set.filter(warehouse=warehouse, sku=sku, inventory_state=state_reserved)

    print('SKU {}, inventory state {}, {} entries found'.format(sku, state_reserved, duplicate_reserved_entries.count()))

    if duplicate_reserved_entries.count() == 1:
        return
    available_entries = w_query_set.filter(warehouse=warehouse, sku=sku, inventory_state=state_available)
    print('SKU {}, inventory state {}, {} entries found'.format(sku, state_available, available_entries.count()))

    if available_entries.exists():
        # duplicate_reserved_entries.first().delete()
        return
    else:
        mark_one_reserved_as_available(warehouse, sku, duplicate_reserved_entries)


def fix_duplicate_available(warehouse, sku):
    duplicate_available_entries = w_query_set.filter(warehouse=warehouse, sku=sku, inventory_state=state_available)

    print('SKU {}, inventory state {}, {} entries found'.format(sku, state_available, duplicate_available_entries.count()))

    if duplicate_available_entries.count() == 1:
        return
    reserved_entries = w_query_set.filter(warehouse=warehouse, sku=sku, inventory_state=state_reserved)
    print('SKU {}, inventory state {}, {} entries found'.format(sku, state_reserved, reserved_entries.count()))

    if reserved_entries.exists():
        remove_one_available(warehouse, sku, duplicate_available_entries)
    else:
        mark_one_available_as_reserved(warehouse, sku, duplicate_available_entries)


def remove_one_available(warehouse, sku, duplicate_available_entries):
    total_available = get_available_quantity(warehouse, sku, type_normal)
    print('SKU {}, total available {}'.format(sku, total_available))
    available_entry_to_keep = None
    available_entry_to_remove = None

    for entry in duplicate_available_entries:
        if entry.quantity == total_available:
            if available_entry_to_keep is None:
                available_entry_to_keep = entry
                break

    if available_entry_to_keep is None:
        available_entry_to_remove = duplicate_available_entries.first()
    else:
        for entry in duplicate_available_entries:
            if entry == available_entry_to_keep:
                continue
            available_entry_to_remove = entry

    print('available entry to remove {} '.format(available_entry_to_remove.id))
    # available_entry_to_remove.delete()



def mark_one_available_as_reserved(warehouse, sku, duplicate_available_entries):
    total_available_quantity = get_available_quantity(warehouse, sku, type_normal)
    print('SKU {}, total available {}'.format(sku, state_available, total_available_quantity))
    available_entry_to_keep = None
    available_entry_to_reserve = None

    for entry in duplicate_available_entries:
        if entry['quantity'] == total_available_quantity:
            if available_entry_to_keep is None:
                available_entry_to_keep = entry
                break

    if available_entry_to_keep is None:
        available_entry_to_reserve = duplicate_available_entries.first()
    else:
        for entry in duplicate_available_entries:
            if entry == available_entry_to_keep:
                continue
            available_entry_to_reserve = entry

    print('available entry to reserve {} '.format(available_entry_to_reserve.id))
    available_entry_to_reserve.inventory_state = state_reserved
    # available_entry_to_reserve.save()



def mark_one_reserved_as_available(warehouse, sku, duplicate_reserved_entries):
    total_available_quantity = get_available_quantity(warehouse, sku, type_normal)
    print('SKU {}, total available {}'.format(sku, state_available, total_available_quantity))
    reserve_entry_to_make_available = None

    for entry in duplicate_reserved_entries:
        if entry.quantity == total_available_quantity:
            if reserve_entry_to_make_available is None:
                reserve_entry_to_make_available = entry
                break

    if not reserve_entry_to_make_available:
        reserve_entry_to_make_available = duplicate_reserved_entries.first()

    print('reserved entry to make available {} '.format(reserve_entry_to_make_available.id))
    reserve_entry_to_make_available.inventory_state = state_available
    # reserve_entry_to_make_available.save()

def get_available_quantity(warehouse, sku, inventory_type):
    return BinInventory.objects.filter(warehouse=warehouse, sku=sku, inventory_type=inventory_type)\
                        .aggregate(total=Sum('quantity')).get('total')
