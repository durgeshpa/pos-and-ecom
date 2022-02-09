import datetime

from django.db.models import Q, Sum, F

from shops.models import Shop
from wms.models import Pickup, PickupBinInventory, BinInventory
from ..scripts.warehouse_inventory_fix import warehouse_inventory_fix_by_cron

warehouse_list = [Shop.objects.get(pk=1393), Shop.objects.get(pk=600), Shop.objects.get(pk=32154)]


def run():
    for w in warehouse_list:
        populate_to_be_picked_quantity(w)


def populate_to_be_picked_quantity_by_cron():
    print("Started Cron Inventory Fix | {} | populate_to_be_picked_quantity_by_cron".format(datetime.datetime.now()))
    for w in warehouse_list:
        populate_to_be_picked_quantity(w)
    print("Calling warehouse_inventory_fix_by_cron from populate_to_be_picked_quantity_by_cron")
    warehouse_inventory_fix_by_cron()
    print("Ended Cron Inventory Fix | {} | populate_to_be_picked_quantity_by_cron".format(datetime.datetime.now()))


def populate_to_be_picked_quantity(warehouse):
    print('Warehouse-{}|populate_to_be_picked_quantity|STARTED'.format(warehouse))
    """
        Case 1 | Set to_be_picked_qty = 0 whose pickup is completed or cancelled
    """
    pck_inv_objs = PickupBinInventory.objects.filter(
        pickup__status__in=['picking_complete', 'picking_cancelled'], warehouse=warehouse, bin__to_be_picked_qty__gt=0)\
        .values('bin_id')
    bin_inv_ids = [x['bin_id'] for x in pck_inv_objs]
    print("Updating to_be_picked_qty = 0 for Bin-Inventory-Ids-{}".format(bin_inv_ids))
    BinInventory.objects.filter(id__in=bin_inv_ids).update(to_be_picked_qty=0)
    print('UPDATED BinInventory, set 0 as to_be_picked_qty for Bin-Inventory-Ids-{}'.format(str(bin_inv_ids)))

    """
        Case 2 | Set to_be_picked_qty from PickupBinInventory whose pickup status not in [completed and cancelled]
    """
    bin_qty_dict = {}
    pbi_qs = PickupBinInventory.objects.filter(~Q(pickup__status__in=['picking_complete', 'picking_cancelled']),
                                               warehouse=warehouse)\
                               .values('bin_id').annotate(pickup_qty=Sum('quantity'),
                                                          picked_qty=Sum('pickup_quantity'))
    for pbi in pbi_qs:
        if not pbi['picked_qty']:
            pbi['picked_qty'] = 0
        to_be_picked_qty = pbi['pickup_qty'] - pbi['picked_qty']
        bin_qty_dict[pbi['bin_id']] = to_be_picked_qty

    print(bin_qty_dict)

    for bin_inv_id, qty in bin_qty_dict.items():
        bin_inv_obj = BinInventory.objects.get(id=bin_inv_id)
        bin_inv_obj.to_be_picked_qty = qty
        bin_inv_obj.save()
        print('Bin-{}, Batch-{}, Type-{}, to be picked quantity-{}, UPDATED'
              .format(bin_inv_obj.bin, bin_inv_obj.batch_id, bin_inv_obj.inventory_type, bin_inv_obj.to_be_picked_qty))

    print('Warehouse-{}|populate_to_be_picked_quantity|ENDED'.format(warehouse))
