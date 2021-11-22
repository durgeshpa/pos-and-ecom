from django.db.models import Q, Sum

from shops.models import Shop
from wms.models import Pickup, PickupBinInventory, BinInventory

warehouse_list = [Shop.objects.get(pk=1393), Shop.objects.get(pk=600), Shop.objects.get(pk=32154)]


def run():
    for w in warehouse_list:
        populate_to_be_picked_quantity(w)


def populate_to_be_picked_quantity(warehouse):
    print('Warehouse-{}|populate_to_be_picked_quantity|STARTED'.format(warehouse))
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