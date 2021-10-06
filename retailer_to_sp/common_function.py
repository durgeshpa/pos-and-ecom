import datetime
import json
import time
import random

from django.db.models import Sum
from django.db import transaction

today = datetime.datetime.today()
from django.core.exceptions import ObjectDoesNotExist

from shops.models import ParentRetailerMapping

today = datetime.datetime.today()
from global_config.views import get_config


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


def reserved_args_json_data(shop_id, transaction_id, products, transaction_type, order_status, order_no):
    reserved_args = json.dumps({
        'shop_id': shop_id,
        'transaction_id': transaction_id,
        'products': products,
        'transaction_type': transaction_type,
        'order_status': order_status,
        'order_number': order_no
    })
    return reserved_args


def generate_credit_note_id(invoice_no, return_count, prefix='FCR'):
    # cr_id = prefix + time.strftime('%Y%m%d') + str(random.randint(1000000, 9999999))
    cr_id = str(invoice_no).replace('FIV', prefix) + str(return_count).zfill(3)
    return cr_id


def getShopLicenseNumber(shop_name):
    license_number = None
    if 'gfdn' in shop_name.lower():
        license_number = get_config('gfdn_license_no', None)
    if 'addistro' in shop_name.lower():
        license_number = get_config('addistro_license_no', None)
    return license_number


def getShopCINNumber(shop_name):
    cin_number = None
    if 'gfdn' in shop_name.lower():
        cin_number = get_config('gfdn_cin_no', None)
    if 'addistro' in shop_name.lower():
        cin_number = get_config('addistro_cin_no', None)
    return cin_number


def getGSTINNumber():
    return get_config('gstin_number', None)

# def getShopLicenseNumber(shop_id):
#     if shop_id == 32154:
#         return get_config('addistro_license_no', None)
#     if shop_id == 600:
#         return get_config('gfdn_license_no', None)
#     return get_config('addistro_license_no', None)
