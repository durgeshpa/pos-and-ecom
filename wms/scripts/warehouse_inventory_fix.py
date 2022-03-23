import logging

from django.db.models import Sum, Q

from global_config.views import get_config
from retailer_to_sp.models import Order
from wms.models import InventoryState, InventoryType, Pickup, WarehouseInventory, BinInventory

<<<<<<< HEAD:wms/scripts/warehouse_inventory_fix.py
=======
cron_logger = logging.getLogger('cron_log')
>>>>>>> 35cd336148973ce61e9d7b1bb5a2b4dd9e0d4f15:wms/scripts/warehouse-inventory-fix.py
warehouse_list = get_config('active_wh_list', [600, 50484])

type_normal = InventoryType.objects.only('id').get(inventory_type='normal').id
stage_available = InventoryState.objects.only('id').get(inventory_state='available').id
stage_reserved = InventoryState.objects.only('id').get(inventory_state='reserved').id
stage_ordered = InventoryState.objects.only('id').get(inventory_state='ordered').id
stage_total_available = InventoryState.objects.only('id').get(inventory_state='total_available').id
stage_to_be_picked = InventoryState.objects.only('id').get(inventory_state='to_be_picked').id
stage_picked = InventoryState.objects.only('id').get(inventory_state='picked').id


def run():
    for w in warehouse_list:
        match_total_available_and_to_be_picked(w)
        # fix_ordered_data(w)
        # match_picked_inventory(w)


def warehouse_inventory_fix_by_cron():
    print("Called warehouse_inventory_fix_by_cron")
    for w in warehouse_list:
        match_total_available_and_to_be_picked(w)
    print("Ended warehouse_inventory_fix_by_cron")


def match_picked_inventory(warehouse):
     picked_qty_dict = Pickup.objects.filter(warehouse_id=warehouse, status='picking_complete',
                                             pickup_type_id__in=
                                             Order.objects.filter(order_status__in=['par_ship_created',
                                                                                    'full_ship_created',
                                                                                    'picking_complete',
                                                                                    'ready_to_dispatch'])
                                                          .values_list('order_no', flat=True))\
                                     .values('sku_id').annotate(picked_qty=Sum('pickup_quantity'))
     for item in picked_qty_dict:
        warehouse_inventory = WarehouseInventory.objects.filter(warehouse_id=warehouse, sku_id=item['sku_id'],
                                                                inventory_type=type_normal,
                                                                inventory_state=stage_picked).last()
        if warehouse_inventory is not None and warehouse_inventory.quantity != item['picked_qty']:
            print("{} Picked Qty-{}, warehouse picked Qty-{}"
                  .format(item['sku_id'], item['picked_qty'], warehouse_inventory.quantity))
            warehouse_inventory.quantity = item['picked_qty']
            warehouse_inventory.save()


def match_total_available_and_to_be_picked(warehouse):
    bin_inventory = BinInventory.objects.filter(warehouse_id=warehouse, inventory_type=type_normal,) \
                                        .values('sku_id') \
                                        .annotate(available=Sum('quantity'), to_be_picked=Sum('to_be_picked_qty'))
    for item in bin_inventory:
        warehouse_inventory = WarehouseInventory.objects.filter(warehouse_id=warehouse, sku_id=item['sku_id'],
                                                                inventory_type=type_normal,
                                                                inventory_state__in=[stage_to_be_picked,
                                                                                     stage_total_available])

        for w in warehouse_inventory:
            if w.inventory_state_id == stage_total_available:
                total_available = item['available'] + item['to_be_picked']
                if w.quantity != total_available:
                    print("BinQuantity-{}, Warehouse Inventory --> SKU-{}, total available quantity-{}"
                          .format(total_available, w.sku_id, w.quantity))
                    cron_logger.info("BinQuantity-{}, Warehouse Inventory --> SKU-{}, total available quantity-{}"
                                     .format(total_available, w.sku_id, w.quantity))
                    w.quantity = total_available
                    w.save()
            elif w.inventory_state_id == stage_to_be_picked:
                if w.quantity != item['to_be_picked']:
                    print("BinQuantity-{}, Warehouse Inventory --> SKU-{}, to be picked quantity-{}"
                          .format(item['to_be_picked'], w.sku_id, w.quantity))
                    cron_logger.info("BinQuantity-{}, Warehouse Inventory --> SKU-{}, to be picked quantity-{}"
                                     .format(item['to_be_picked'], w.sku_id, w.quantity))
                    w.quantity = item['to_be_picked']
                    w.save()


def fix_ordered_data(warehouse):
    print('warehouse {}, ordered quantity update started'.format(warehouse))
    start_time = '2020-08-29 01:01:06.067349'
    inventory_calculated = {}
    warehouse_inventory_dict = {}
    warehouse_inventory = WarehouseInventory.objects.filter(warehouse_id=warehouse,
                                                            inventory_type=type_normal,
                                                            inventory_state=stage_ordered)\
                                                    .values('warehouse_id', 'sku_id', 'quantity')

    orders_placed = Order.objects.filter(seller_shop_id=warehouse,
                                         order_status=Order.ORDERED,
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