from django.db.models import Sum

from retailer_to_sp.models import Order
from shops.models import Shop
from wms.models import InventoryType, InventoryState, WarehouseInventory, BinInventory

warehouse_list = [Shop.objects.get(pk=32154), Shop.objects.get(pk=600)]
type_normal = InventoryType.objects.only('id').get(inventory_type='normal').id
stage_available = InventoryState.objects.only('id').get(inventory_state='available').id
stage_reserved = InventoryState.objects.only('id').get(inventory_state='reserved').id
stage_ordered = InventoryState.objects.only('id').get(inventory_state='ordered').id

def run():
    for w in warehouse_list:
        fix_available_quantity(w)
        fix_ordered_data(w)
        fix_reserved_quantity(w)

def fix_reserved_quantity(warehouse):
    print('warehouse {}, reserved quantity update started'.format(warehouse))
    warehouse_inventory_dict = {}
    warehouse_inventory = WarehouseInventory.objects.filter(warehouse=warehouse, inventory_type=type_normal,
                                                            inventory_state=stage_reserved, quantity__gt=0)
    for item in warehouse_inventory:
        warehouse_inventory_dict[item.sku_id] = item.quantity
    warehouse_inventory.update(quantity=0)
    print(warehouse_inventory_dict)
    print('warehouse {}, reserved quantity updated'.format(warehouse))


def fix_available_quantity(warehouse):
    print('warehouse {}, available quantity update started'.format(warehouse))
    warehouse_inventory_dict = {}
    bin_inventory = BinInventory.objects.filter(warehouse=warehouse, inventory_type=type_normal)\
                                        .values('sku_id') \
                                        .filter(warehouse=warehouse) \
                                        .annotate(quantity=Sum('quantity'))
    for item in bin_inventory:
        warehouse_inventory = WarehouseInventory.objects.filter(warehouse=warehouse, inventory_type=type_normal,
                                                                inventory_state=stage_available, sku=item['sku_id'])
        if warehouse_inventory.count() != 1:
            print('warehouse {}, sku {}, {} records found'
                  .format(warehouse, item['sku_id'], warehouse_inventory.count()))
            continue
        warehouse_quantity = warehouse_inventory.last().quantity
        if item['quantity'] != warehouse_quantity:
            warehouse_inventory_dict[item['sku_id']] = {'bin_qty': item['quantity'],
                                                        'warehouse_qty': warehouse_quantity}
            warehouse_inventory.update(quantity=item['quantity'])
    print(warehouse_inventory_dict)
    print('warehouse {}, available quantity updated'.format(warehouse))

def fix_ordered_data(warehouse):
    print('warehouse {}, ordered quantity update started'.format(warehouse))
    start_time = '2020-08-29 01:01:06.067349'
    inventory_calculated = {}
    warehouse_inventory_dict = {}
    warehouse_inventory = WarehouseInventory.objects.filter(warehouse=warehouse,
                                                            inventory_type=type_normal,
                                                            inventory_state=stage_ordered)\
                                                    .values('warehouse_id', 'sku_id', 'quantity')

    orders_placed = Order.objects.filter(seller_shop=warehouse,
                                         order_status__in=[Order.ORDERED,
                                                           Order.PICKUP_CREATED,
                                                           Order.PICKING_ASSIGNED],
                                         created_at__gte=start_time)
    for o in orders_placed:
        ordered_sku = o.ordered_cart.rt_cart_list.values('cart_product__product_sku')\
                                                  .annotate(qty=Sum('no_of_pieces'))
        for item in ordered_sku:
            if inventory_calculated.get(item['cart_product__product_sku']) is None:
                inventory_calculated[item['cart_product__product_sku']] = 0

            inventory_calculated[item['cart_product__product_sku']] += item['qty']

    for item in warehouse_inventory:
        if inventory_calculated.get(item['sku_id']) is None:
            inventory_calculated[item['sku_id']] = 0
        if inventory_calculated[item['sku_id']] != item['quantity']:
            warehouse_inventory_dict[item['sku_id']] = {'order_qty': inventory_calculated[item['sku_id']],
                                                        'warehouse_qty': item['quantity']}
            WarehouseInventory.objects.filter(warehouse_id=item['warehouse_id'],
                                              sku_id=item['sku_id'],
                                              inventory_type=type_normal,
                                              inventory_state=stage_ordered)\
                                      .update(quantity=inventory_calculated[item['sku_id']])
    print(warehouse_inventory_dict)
    print('warehouse {}, ordered quantity updated'.format(warehouse))
