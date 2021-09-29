import datetime
import json
import time
import random

from django.db.models import Sum, Q
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

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

def generate_credit_note_id(invoice_no, return_count, prefix='FCR'):
    # cr_id = prefix + time.strftime('%Y%m%d') + str(random.randint(1000000, 9999999))
    cr_id = str(invoice_no).replace('FIV', prefix) + str(return_count).zfill(3)
    return cr_id


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True,
                      "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": []}

    return Response(result, status=status_code)


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]


def validate_data_format(request):
    """ Validate Picker Dashboard data  """
    try:
        data = request.data["data"]
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def picker_dashboard_search(queryset, search_text):
    '''
    search using warehouse shop_name & product name & supervisor name & coordinator name based on criteria that matches
    '''
    queryset = queryset.filter(
        Q(zone__warehouse__shop_name__icontains=search_text) | Q(picking_status__icontains=search_text) |
        Q(picker_boy__first_name__icontains=search_text) | Q(picker_boy__phone_number__icontains=search_text))
    return queryset
