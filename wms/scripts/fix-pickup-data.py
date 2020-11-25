from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from retailer_to_sp.models import Order, PickerDashboard
from wms.models import PickupBinInventory, Pickup
from wms.views import PicklistRefresh


def run():
    order_list = get_ordres_to_cancel_pickup()
    print(order_list)
    for o in order_list:
        PicklistRefresh.cancel_picklist_by_order(o)
        print('Picklist cancelled for order {} '.format(o))

    for o in order_list:
        create_picklist_by_order_no(o)
        print('Picklist Created for order {} '.format(o))


def get_ordres_to_cancel_pickup():
    orders_to_cancel_pickup = []
    orders = Order.objects.filter(order_status__in=[Order.PICKUP_CREATED, Order.PICKING_ASSIGNED],
                                  created_at__gt='2020-11-24').values_list('order_no', flat=True)
    for o in orders:
        pickups = Pickup.objects.filter(pickup_type_id=o).exclude(status='picking_cancelled')
        for p in pickups:
            pickup_bin_inventory = PickupBinInventory.objects.filter(pickup=p)
            for pbi in pickup_bin_inventory:
                if pbi.warehouse != p.warehouse:
                    orders_to_cancel_pickup.append(o)
    order_list = set(orders_to_cancel_pickup)
    print('Total orders to cancel pickup for {}'.format(len(order_list)))
    return order_list



def create_picklist_by_order_no(o):
    order = Order.objects.filter(order_no=o).last()
    try:
        pd_obj = PickerDashboard.objects.filter(order=order,
                                                picking_status__in=['picking_pending', 'picking_assigned'],
                                                is_valid=False).last()
        if pd_obj is None:
            print("Picker Dashboard object does not exists for order {}".format(order.order_no))
            return
        with transaction.atomic():
            PicklistRefresh.create_picklist_by_order(order)
            pd_obj.is_valid = True
            pd_obj.refreshed_at = timezone.now()
            pd_obj.save()
    except Exception as e:
        print(e)
        print('generate_pick_list|Exception while generating picklist for order {}'.format(o))
