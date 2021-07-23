import datetime
import json
import time
import random

from django.db.models import Sum

from addresses.models import Address
from pos.models import RetailerProduct, PosCart, PosCartProductMapping, Vendor
today = datetime.datetime.today()
from django.core.exceptions import ObjectDoesNotExist

from shops.models import ParentRetailerMapping

today = datetime.datetime.today()

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


def generate_credit_note_id(invoice_no, return_id, prefix='FCR'):
    # cr_id = prefix + time.strftime('%Y%m%d') + str(random.randint(1000000, 9999999))
    cr_id = str(invoice_no).replace('FIV', prefix) + str(return_id)
    return cr_id 
    
def create_po_franchise(user, order_no, seller_shop, buyer_shop, products):
    bill_add = Address.objects.filter(shop_name=seller_shop, address_type='billing').last()
    vendor, created = Vendor.objects.get_or_create(company_name=seller_shop.shop_name)
    if created:
        vendor.vendor_name, vendor.address, vendor.pincode = 'PepperTap', bill_add.address_line1, bill_add.pincode
        vendor.city, vendor.state = bill_add.city, bill_add.state
        vendor.save()
    cart, created = PosCart.objects.get_or_create(vendor=vendor, retailer_shop=buyer_shop, gf_order_no=order_no)
    cart.last_modified_by = user
    if created:
        cart.raised_by = user
    cart.save()
    product_ids = []
    for product in products:
        retailer_product = RetailerProduct.objects.filter(linked_product=product.cart_product, shop=buyer_shop).last()
        product_ids += [retailer_product.id]
        mapping, _ = PosCartProductMapping.objects.get_or_create(cart=cart, product=retailer_product)
        mapping.price = product.get_cart_product_price(seller_shop.id, buyer_shop.id).get_per_piece_price(product.qty)
        mapping.qty = product.qty
        mapping.save()
    PosCartProductMapping.objects.filter(cart=cart, is_grn_done=False).exclude(product_id__in=product_ids).delete()
