import datetime
import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from shops.models import ParentRetailerMapping
from global_config.views import get_config

today = datetime.datetime.today()

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


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


def getShopPANNumber(shop_name):
    pan_number = None
    if 'gfdn' in shop_name.lower():
        pan_number = get_config('gfdn_pan_no', None)
    if 'addistro' in shop_name.lower():
        pan_number = get_config('addistro_pan_no', None)
    return pan_number


def getGSTINNumber(shop_name):
    gstin_number = None
    if 'gfdn' in shop_name.lower():
        gstin_number = get_config('gfdn_gstin_no', None)
    if 'addistro' in shop_name.lower():
        gstin_number = get_config('addistro_gstin_no', None)
    return gstin_number


# def getShopLicenseNumber(shop_id):
#     if shop_id == 32154:
#         return get_config('addistro_license_no', None)
#     if shop_id == 600:
#         return get_config('gfdn_license_no', None)
#     return get_config('addistro_license_no', None)


def dispatch_trip_search(queryset, search_text):
    '''
    search using seller_shop, source_shop, destination_shop, dispatch_no & delivery_boy based on criteria that matches
    '''
    queryset = queryset.filter(Q(dispatch_no__icontains=search_text) | Q(
        delivery_boy__first_name__icontains=search_text) | Q(source_shop__shop_name__icontains=search_text) | Q(
        destination_shop__shop_name__icontains=search_text) | Q(seller_shop__shop_name__icontains=search_text))
    return queryset


def trip_search(queryset, search_text):
    '''
    search using seller_shop, dispatch_no & delivery_boy based on criteria that matches
    '''
    queryset = queryset.filter(Q(seller_shop__shop_name__icontains=search_text) | Q(
        dispatch_no__icontains=search_text) | Q(delivery_boy__first_name__icontains=search_text))
    return queryset


def get_logged_user_wise_query_set_for_trip_invoices(user, queryset):
    '''
        GET Logged-in user wise queryset for shipment based on criteria that matches
    '''
    if user.has_perm('retailer_to_sp.can_plan_trip'):
        queryset = queryset.filter(order__seller_shop__id=user.shop_employee.last().shop_id)
    else:
        queryset = queryset.none()
    return queryset

