from datetime import datetime, timedelta

from retailer_to_sp.models import Order


def run():
    print('manage_existing_orders | STARTED')
    current_time = datetime.now() - timedelta(minutes=1)
    start_time = datetime.now() - timedelta(days=30)

    order_qs = Order.objects.filter(order_status='PARTIAL_MOVED_TO_QC', picker_order__qc_area__isnull=True) \
        .exclude(ordered_cart__cart_type__in=['AUTO', 'BASIC', 'ECOM'])
    print("Orders having order_status 'PARTIAL_MOVED_TO_QC', Count: " + str(order_qs.count()))

    if order_qs:
        # Update PickerDashboard entries associated with the Orders received with the applied conditions
        for order in order_qs:
            picker_ins = order.picker_order.filter(qc_area__isnull=False).last()
            if picker_ins:
                qc_area = picker_ins.qc_area
                order.picker_order.update(qc_area=qc_area)
                print("PickerDashboard entries updated for order no " + str(order) + ", qc_area " + str(qc_area))
