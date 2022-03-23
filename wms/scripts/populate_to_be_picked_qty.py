import datetime
<<<<<<< HEAD
=======
import logging
>>>>>>> 35cd336148973ce61e9d7b1bb5a2b4dd9e0d4f15

from django.db.models import Q, Sum, F

from global_config.views import get_config
from wms.models import PickupBinInventory, BinInventory
from ..scripts.warehouse_inventory_fix import warehouse_inventory_fix_by_cron

<<<<<<< HEAD
=======
cron_logger = logging.getLogger('cron_log')
>>>>>>> 35cd336148973ce61e9d7b1bb5a2b4dd9e0d4f15
warehouse_list = get_config('active_wh_list', [600, 50484])

def run():
    populate_to_be_picked_quantity_by_cron()


def populate_to_be_picked_quantity_by_cron():
    print("Started Cron Inventory Fix | {} | populate_to_be_picked_quantity_by_cron".format(datetime.datetime.now()))
    for w in warehouse_list:
        populate_to_be_picked_quantity(w)
    print("Calling warehouse_inventory_fix_by_cron from populate_to_be_picked_quantity_by_cron")
    warehouse_inventory_fix_by_cron()
    print("Ended Cron Inventory Fix | {} | populate_to_be_picked_quantity_by_cron".format(datetime.datetime.now()))


def populate_to_be_picked_quantity(warehouse):
    print('Warehouse-{}|populate_to_be_picked_quantity|STARTED'.format(warehouse))

    bin_qty_dict = {}
    pbi_qs = PickupBinInventory.objects.filter(~Q(pickup__status__in=['picking_complete', 'picking_cancelled']),
                                               warehouse_id=warehouse)\
                               .values('bin_id').annotate(pickup_qty=Sum('quantity'),
                                                          picked_qty=Sum('pickup_quantity'))
    """
        Case 1 | Set to_be_picked_qty = 0 whose pickup is completed or cancelled
    """
    BinInventory.objects.filter(~Q(id__in=pbi_qs.values_list('bin_id', flat=True)), warehouse_id=warehouse)\
                        .update(to_be_picked_qty=0)

    """
        Case 2 | Set to_be_picked_qty from PickupBinInventory whose pickup status not in [completed and cancelled]
    """
    for pbi in pbi_qs:
        if not pbi['picked_qty']:
            pbi['picked_qty'] = 0
        to_be_picked_qty = pbi['pickup_qty'] - pbi['picked_qty']
        bin_qty_dict[pbi['bin_id']] = to_be_picked_qty

    print(bin_qty_dict)
    cron_logger.info(f"To be picked quantity : {bin_qty_dict}")

    for bin_inv_id, qty in bin_qty_dict.items():
        bin_inv_obj = BinInventory.objects.get(id=bin_inv_id)
        if bin_inv_obj.to_be_picked_qty != qty:
            old_qty = bin_inv_obj.to_be_picked_qty
            bin_inv_obj.to_be_picked_qty = qty
            bin_inv_obj.save()
            print('Bin-{}, Batch-{}, Type-{}, old to be picked quantity-{}, UPDATED old to be picked quantity-{}'
                  .format(bin_inv_obj.bin, bin_inv_obj.batch_id, bin_inv_obj.inventory_type, old_qty, bin_inv_obj.to_be_picked_qty))
<<<<<<< HEAD
=======
            cron_logger.info('Bin-{}, Batch-{}, Type-{}, old to be picked quantity-{}, UPDATED old to be picked quantity-{}'
                  .format(bin_inv_obj.bin, bin_inv_obj.batch_id, bin_inv_obj.inventory_type, old_qty, bin_inv_obj.to_be_picked_qty))
>>>>>>> 35cd336148973ce61e9d7b1bb5a2b4dd9e0d4f15

    print('Warehouse-{}|populate_to_be_picked_quantity|ENDED'.format(warehouse))
