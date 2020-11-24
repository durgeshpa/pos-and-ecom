from django.db import transaction
from django.db.models import Sum, Q, Count

from retailer_to_sp.models import Order
from shops.models import Shop
from wms.models import InventoryType, InventoryState, WarehouseInventory, BinInternalInventoryChange, Pickup, \
    BinInventory


inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
warehouse = [Shop.objects.get(pk=32154)]


def run():
    for w in warehouse:
        remove_duplicate_pickup_entry(w)
        correct_ordered_data(w)


def get_bin_transaction_id(batch_id, bin_id, transaction_id):
    last = BinInternalInventoryChange.objects.filter(batch_id=batch_id, final_bin=bin_id,
                                                     transaction_id=transaction_id).last()
    if last:
        return last.id
    return None

def stock_correction_entry_exists_after(bin_internal_entry_id):
    return BinInternalInventoryChange.objects.filter(transaction_type__in=['stock_correction_in_type',
                                                                           'stock_correction_out_type'],
                                                     id__gt=bin_internal_entry_id).exists()


@transaction.atomic
def remove_duplicate_pickup_entry(warehouse):
    pickup_ids_list = list(Pickup.objects.values_list('pk', flat=True))
    invalid_pickup_entry_list = BinInternalInventoryChange.objects.filter(~Q(transaction_id__in=pickup_ids_list),
                                                                          warehouse=warehouse,
                                                                          transaction_type='pickup_created')\
                                                                  .values('id', 'final_bin_id',
                                                                          'batch_id', 'transaction_id', 'quantity')
    print('invalid_pickup_entry_list')

    duplicate_pickup_entry_list = BinInternalInventoryChange.objects.filter(transaction_type='pickup_created',
                                                                            warehouse=warehouse)\
                                                                    .values('final_bin_id',
                                                                            'batch_id', 'transaction_id', 'quantity')\
                                                                    .annotate(count=Count('id')).filter(count__gt=1)
    print('duplicate_pickup_entry_list')

    bin_inventory_data = {}
    for entry in invalid_pickup_entry_list:
        print('Batch ID {}, Bin {}, transaction ID {}, quantity {}'
              .format(entry['batch_id'], entry['final_bin_id'], entry['transaction_id'],
                      entry['quantity']))
        if stock_correction_entry_exists_after(entry['id']):
            print('Batch ID {}, Bin {}, transaction ID {}, quantity {} STOCK CORRECTION ENTRY EXISTS'
                  .format(entry['batch_id'], entry['final_bin_id'], entry['transaction_id'],
                          entry['quantity']))
            continue
        bin_inv = BinInventory.objects.filter(warehouse=warehouse, inventory_type=inventory_type,
                                              batch_id=entry['batch_id'], bin=entry['final_bin_id'])
        if bin_inv.count() == 1:
            bi = bin_inv.last()
            if bin_inventory_data.get(bi.bin) is None:
                bin_inventory_data[bi.bin] = 0
            bin_inventory_data[bi.bin] += entry['quantity']
            # biic = BinInternalInventoryChange.objects.filter(warehouse=warehouse, transaction_type='pickup_created',
            #                                                  batch_id=entry['batch_id'],
            #                                                  final_bin=entry['final_bin_id'],
            #                                                  transaction_id=entry['transaction_id']).last()
            # biic.transaction_type = 'pickup_created_deleted'
            # biic.save()
    print('bin_inventory_data - 1')
    print(bin_inventory_data)
    for entry in duplicate_pickup_entry_list:
        print('Batch ID {}, Bin {}, transaction ID {}, quantity {} '
              .format(entry['batch_id'], entry['final_bin_id'], entry['transaction_id'],
                      entry['quantity']))
        bin_tr_id = get_bin_transaction_id(entry['batch_id'], entry['final_bin_id'], entry['transaction_id'])

        print('Batch ID {}, Bin {}, transaction ID {}, quantity {} ID {}'
              .format(entry['batch_id'], entry['final_bin_id'], entry['transaction_id'],
                      entry['quantity'], bin_tr_id))
        if not bin_tr_id:
            continue
        if stock_correction_entry_exists_after(bin_tr_id):
            print('Batch ID {}, Bin {}, transaction ID {}, quantity {} STOCK CORRECTION ENTRY EXISTS'
                  .format(entry['batch_id'], entry['final_bin_id'], entry['transaction_id'],
                          entry['quantity']))
            continue
        bin_inv = BinInventory.objects.filter(warehouse=warehouse, inventory_type=inventory_type,
                                              batch_id=entry['batch_id'], bin=entry['final_bin_id'])
        if bin_inv.count() == 1:
            bi = bin_inv.last()
            if bin_inventory_data.get(bi.bin) is None:
                bin_inventory_data[bi.bin] = 0
            bin_inventory_data[bi.bin] += entry['quantity']
            # biic = BinInternalInventoryChange.objects.filter(warehouse=warehouse, transaction_type='pickup_created',
            #                                                  batch_id=entry['batch_id'],
            #                                                  final_bin=entry['final_bin_id'],
            #                                                  transaction_id=entry['transaction_id']).last()
            # biic.transaction_type = 'pickup_created_deleted'
            # biic.save()
    print('bin_inventory_data - 2')
    print(bin_inventory_data)

    for bin, qty in bin_inventory_data.items():

        print('Bin {}, quantity {}'
              .format(bin, qty))
        # bi = BinInventory.objects.get(id=bi_id)
        # bi.quantity = bi.quantity + qty
        # bi.save()


def correct_ordered_data(warehouse):
    start_time = '2020-08-29 01:01:06.067349'
    inventory_calculated = {}

    type_normal = InventoryType.objects.only('id').get(inventory_type='normal').id
    stage_ordered = InventoryState.objects.only('id').get(inventory_state='ordered').id

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
            WarehouseInventory.objects.filter(warehouse_id=item['warehouse_id'],
                                              sku_id=item['sku_id'],
                                              inventory_type=type_normal,
                                              inventory_state=stage_ordered)\
                                      .update(quantity=inventory_calculated[item['sku_id']])

