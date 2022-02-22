from django.db.models import F

from retailer_to_sp.models import Order


def run():
    print('populate_order_app_type_for_existing_data | STARTED')

    # populate order app type for existing data
    type_map = {
        "BASIC": Order.POS_WALKIN,
        "ECOM": Order.POS_ECOMM
    }
    basic_orders = Order.objects.filter(order_app_type__isnull=True, ordered_cart__cart_type='BASIC')
    print(basic_orders.count())
    print(basic_orders)
    basic_orders.update(order_app_type=type_map['BASIC'])
    print("Basic order updation completed")

    ecom_orders = Order.objects.filter(order_app_type__isnull=True, ordered_cart__cart_type='ECOM')
    print(ecom_orders.count())
    print(ecom_orders)
    ecom_orders.update(order_app_type=type_map['ECOM'])
    print("Basic order updation completed")

    print("Task completed")

