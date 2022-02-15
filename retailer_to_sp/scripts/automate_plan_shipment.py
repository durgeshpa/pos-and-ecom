from retailer_to_sp.models import Order, OrderedProduct
from retailer_to_sp.views import create_order_shipment


def run():
    qc_pending_orders = OrderedProduct.objects.filter(shipment_status__in=["SHIPMENT_CREATED","READY_TO_SHIP"]).values('order')
    orders = Order.objects.filter(order_status=Order.MOVED_TO_QC).exclude(id__in=qc_pending_orders)
    print(f"automate_plan_shipment|Order count {orders.count()}")
    for o in orders:
        create_order_shipment(o)
        print(f"automate_plan_shipment|Order{o.order_no}")
    print(f"automate_plan_shipment|Completed")