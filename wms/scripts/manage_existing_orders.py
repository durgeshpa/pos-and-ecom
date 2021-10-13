from datetime import datetime, timedelta

from django.db import models
from django.db.models.functions import Cast

from retailer_to_sp.models import PickerDashboard, Order
from wms.models import Pickup


def run():
    print('manage_existing_orders | STARTED')
    current_time = datetime.now() - timedelta(minutes=1)
    # current_time = datetime.now() - timedelta(days=90)
    start_time = datetime.now() - timedelta(days=30)

    # Case 1
    picker_qs_1 = PickerDashboard.objects.filter(
        picking_status__in=['picking_complete'],
        order__order_closed=False,
        order__created_at__lt=current_time,
        order__created_at__gt=start_time). \
        exclude(order__order_status__in=['CANCELLED', 'completed'])
    print("PickerDashboard entries having picking_status as 'picking_complete', Count: " + str(picker_qs_1.count()))

    order_qs_1 = Order.objects.filter(
        id__in=picker_qs_1.values_list('order__id', flat=True), order_status='picking_complete',
        order_closed=False, created_at__lt=current_time, created_at__gt=start_time)
    print("Order entries received from PickerDashboard conditions and order_status as 'picking_complete', Count: "
          + str(order_qs_1.count()))

    if picker_qs_1:
        if order_qs_1:
            for order in order_qs_1:
                print(order.order_status)
            # order_qs_1.update(order_status='MOVED_TO_QC')
            print("Set order_status as 'MOVED_TO_QC' for orders "
                  "whose picker entries having picking_status as 'picking_complete'")
        # picker_qs_1.update(picking_status='moved_to_qc')
        print("Set picking_status as 'moved_to_qc' for picker entries having picking_status is 'picking_complete'")

    print("\n\n###########################################################################################\n\n")

    # Case 2
    order_qs_2 = Order.objects.filter(order_status__in=['ordered', 'PICKING_ASSIGNED', 'PICKUP_CREATED'],
                                      order_closed=False, created_at__lt=current_time, created_at__gt=start_time) \
        .exclude(ordered_cart__cart_type__in=['AUTO', 'BASIC', 'ECOM'])
    print("Orders having order_status in ('ordered', 'PICKING_ASSIGNED', 'PICKUP_CREATED'), Count: " + str(
        order_qs_2.count()))

    pickup_qs_2 = Pickup.objects.filter(
        pickup_type='Order', pickup_type_id__in=order_qs_2.values_list(Cast('order_no', models.CharField()), flat=True))

    print("Pickups having Order no received with the applied conditions, Count: " + str(pickup_qs_2.count()))

    if order_qs_2:
        # Delete PickerDashboard entries associated with the Orders received with the applied conditions
        for order in order_qs_2:
            if order.picker_order.exists():
                # order.picker_order.all().delete()
                print("PickerDashboard entries deleted for order no " + str(order) + ", status "
                      + str(order.order_status))

        # Delete Pickup Entries associated with the Orders received with the applied conditions
        if pickup_qs_2:
            for pickup in pickup_qs_2:
                # pickup.bin_inventory.all().delete()
                # pickup.delete()
                print("Pickup entry deleted for order no " + str(pickup.pickup_type_id))

        # Update Orders status to 'ordered'
        # order_qs_2.update(order_status='ordered')
        print("Set order_status as 'ordered' for orders having order_status in "
              "('ordered', 'PICKING_ASSIGNED', 'PICKUP_CREATED')")
