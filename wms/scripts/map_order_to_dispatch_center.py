import logging
from datetime import datetime, timedelta

from retailer_to_sp.models import Order

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run():
    map_order_to_dispatch_center_by_cron()


def map_order_to_dispatch_center_by_cron():
    print('map_order_to_dispatch_center | STARTED')
    cron_logger.info('map_order_to_dispatch_center | STARTED')
    current_time = datetime.now() - timedelta(minutes=1)
    start_time = datetime.now() - timedelta(days=1)

    query = f"""
    SELECT od.* 
        FROM retailer_to_sp_order as od
        LEFT join addresses_address as ad
            ON od.shipping_address_id = ad.id
        LEFT JOIN addresses_pincode as pin
            ON ad.pincode_link_id = pin.id
        INNER JOIN shops_parentretailermapping prm on prm.retailer_id=od.seller_shop_id
        WHERE dispatch_center_id is NULL
            AND od.order_status NOT IN ('ordered', 'CANCELLED', 'completed')
            AND ad.address_type = 'shipping'
            AND od.created_at > '{str(start_time)}' AND od.created_at < '{str(current_time)}'
            AND prm.retailer_id = 53627
            AND pin.pincode IN (
                SELECT DISTINCT(pin.pincode)
                FROM public.addresses_dispatchcenterpincodemapping as dp
                INNER JOIN addresses_pincode as pin
                ON dp.pincode_id = pin.id
                WHERE dp.dispatch_center_id=53627)
        ORDER BY od.created_at DESC
    """

    orders = Order.objects.raw(query)
    print(f"Map Dispatch Center against orders, Count {len(orders)}")
    cron_logger.info(f"Map Dispatch Center against orders, Count {len(orders)}")
    order_nos = [x.order_no for x in orders]
    if order_nos:
        Order.objects.filter(order_no__in=order_nos).update(dispatch_center_id=53627, dispatch_delivery=True)
        print(f"Dispatch Center mapped against orders, Count {len(order_nos)}, List {order_nos}")
        cron_logger.info(f"Dispatch Center mapped against orders, Count {len(order_nos)}, List {order_nos}")
    else:
        cron_logger.info(f"No order found to map dispatch center")
    print('map_order_to_dispatch_center| ENDED')
    cron_logger.info('map_order_to_dispatch_center| ENDED')
