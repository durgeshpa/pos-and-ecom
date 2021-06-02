import datetime
import json

from django.db.models import Sum

today = datetime.datetime.today()
from django.core.exceptions import ObjectDoesNotExist

from shops.models import ParentRetailerMapping


def getShopMapping(shop_id):
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
        return parent_mapping
    except ObjectDoesNotExist:
        return None


def check_date_range(capping):
    """
    capping object
    return start date and end date
    """
    if capping.capping_type == 0:
        end_date = datetime.datetime.today()
        start_date = datetime.datetime.today()
        return end_date, start_date
    elif capping.capping_type == 1:
        end_date = datetime.datetime.today()
        start_date = end_date - datetime.timedelta(days=today.weekday())
        return start_date, end_date
    elif capping.capping_type == 2:
        end_date = datetime.datetime.today()
        start_date = datetime.datetime.today().replace(day=1)
        return start_date, end_date


def capping_check(capping, parent_mapping, cart_product, product_qty, ordered_qty):
    """
    capping:- Capping object
    parent_mapping :- parent mapping object
    cart_product:- cart products
    product_qty:- quantity of product
    ordered_qty:- quantity of order
    """
    # to get the start and end date according to capping type
    start_date, end_date = check_date_range(capping)
    capping_start_date = start_date
    capping_end_date = end_date
    from .models import Order
    if capping_start_date.date() == capping_end_date.date():
        capping_range_orders = Order.objects.filter(buyer_shop=parent_mapping.retailer,
                                                    created_at__gte=capping_start_date.date(),
                                                    ).exclude(order_status='CANCELLED')

    else:
        capping_range_orders = Order.objects.filter(buyer_shop=parent_mapping.retailer,
                                                    created_at__gte=capping_start_date,
                                                    created_at__lte=capping_end_date).exclude(order_status='CANCELLED')
    if capping_range_orders:
        for order in capping_range_orders:
            if order.ordered_cart.rt_cart_list.filter(
                    cart_product=cart_product).exists():
                ordered_qty += order.ordered_cart.rt_cart_list.filter(
                    cart_product=cart_product).last().qty
    if capping.capping_qty > ordered_qty:
        if (capping.capping_qty - ordered_qty) < product_qty:
            if (capping.capping_qty - ordered_qty) > 0:
                cart_product.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
                        capping.capping_qty - ordered_qty)]
            else:
                cart_product.capping_error_msg = ['You have already exceeded the purchase limit of this product']
            cart_product.save()
            return False, cart_product.capping_error_msg
        else:
            cart_product.capping_error_msg = ['Allow to reserve the Product']
            return True, cart_product.capping_error_msg
    else:
        if (capping.capping_qty - ordered_qty) > 0:
            cart_product.capping_error_msg = ['The Purchase Limit of the Product is %s' % (
                    capping.capping_qty - ordered_qty)]
        else:
            cart_product.capping_error_msg = ['You have already exceeded the purchase limit of this product']
        cart_product.save()
        return False, cart_product.capping_error_msg


def reserved_args_json_data(shop_id, transaction_id, products, transaction_type, order_status):
    reserved_args = json.dumps({
        'shop_id': shop_id,
        'transaction_id': transaction_id,
        'products': products,
        'transaction_type': transaction_type,
        'order_status': order_status
    })
    return reserved_args
