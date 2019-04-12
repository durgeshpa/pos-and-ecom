
from django.core.exceptions import ObjectDoesNotExist
from shops.models import Shop,ParentRetailerMapping
from addresses.models import Address
from rest_framework import status
from addresses.models import InvoiceCityMapping
from rest_framework.response import Response
from django.conf import settings
import datetime

# get shop
def checkShop(shop_id):
    try:
        shop = Shop.objects.get(id=shop_id,status=True)
        return True
    except ObjectDoesNotExist:
        return False

def checkShopMapping(shop_id):
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id,status=True)
        return True
    except ObjectDoesNotExist:
        return False

def checkNotShopAndMapping(shop_id):
    if checkShop(shop_id) and checkShopMapping(shop_id):
        return False
    else:
        return True

def getShop(shop_id):
    try:
        shop = Shop.objects.get(id=shop_id,status=True)
        return shop
    except ObjectDoesNotExist:
        return None

def getShopMapping(shop_id):
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id,status=True)
        return parent_mapping
    except ObjectDoesNotExist:
        return None


def get_financial_year():
    current_month = datetime.date.today().strftime('%m')
    current_year = datetime.date.today().strftime('%y')

    if int(current_month) < 4:
        current_year = str(int(datetime.date.today().strftime('%y'))-1)
    return current_year


def get_shop_warehouse_code(shop):
    return str(shop.shop_code), str(shop.warehouse_code)


def get_shop_warehouse_state_code(address):
    address = Address.objects.select_related('state',
                                             'shop_name').get(pk=address)
    state_code = format(address.state_id, '02d')
    shop_code, warehouse_code = get_shop_warehouse_code(address.shop_name)
    return state_code, shop_code, warehouse_code


def get_last_no_to_increment(model, field, instance_id, starts_with):
    instance_with_current_pattern = model.objects.filter(
                                        **{field+'__icontains': starts_with})

    if instance_with_current_pattern:
        last_instance_no = instance_with_current_pattern.last()
        return int(getattr(last_instance_no, field)[-7:])

    else:
        return 0


def common_pattern(model, field, instance_id, address, invoice_type):
    state_code, shop_code, warehouse_code = get_shop_warehouse_state_code(
                                            address)
    financial_year = get_financial_year()
    starts_with = "%s%s%s%s%s" % (
                                shop_code, invoice_type, financial_year,
                                state_code, warehouse_code)
    last_number = get_last_no_to_increment(model, field, instance_id, starts_with)
    last_number += 1
    ends_with = str(format(last_number, '07d'))
    return "%s%s" % (starts_with, ends_with)


def po_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "PO")


def order_id_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "OR")


def order_id_pattern_r_gram(order_id):

    """ Order ID pattern

    Using 07 as the default city code for the pattern.
    order id is the id of created instance.
    """

    starts_with = getattr(settings, 'INVOICE_STARTS_WITH', 'ADT')
    default_city_code = getattr(settings, 'DEFAULT_CITY_CODE', '07')
    city_code = default_city_code
    ends_with = str(order_id).rjust(5, '0')
    return "%s/%s/%s" % (starts_with,city_code,ends_with)


def grn_pattern(id):

    """GRN patternbrand_note_id

    GRN year changes on 1st April(4th month).
    Getting id as instance id for auto increment.
    """

    current_month = datetime.date.today().strftime('%m')
    current_year = datetime.date.today().strftime('%y')
    next_year = str(int(current_year) + 1)

    if int(current_month)<4:
        current_year = str(int(datetime.date.today().strftime('%y'))-1)
        next_year = datetime.date.today().strftime('%y')
    starts_with = "%s-%s"%(current_year,next_year)
    ends_with = str(id)
    return "%s/%s" % (starts_with,ends_with)


def brand_debit_note_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "DN")


def brand_credit_note_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "CN")


def getcredit_note_id(c_num, invoice_pattern):
    starts_with = invoice_pattern
    return int(c_num.split(starts_with)[1])

def brand_note_pattern(note_type, id):

    """Brand Note pattern

    Getting note_type to return pattern as per note_typeself,
    id is used as auto increment.
    """

    if note_type == 'debit_note':
        starts_with = datetime.date.today().strftime('%d%m%y')
        ends_with = str(id)
        return "%s/%s"%(starts_with,ends_with)

    elif note_type == 'credit_note':
        starts_with = getattr(settings, 'CN_STARTS_WITH', 'ADT/CN')
        ends_with = str(id).rjust(5, '0')
        return "%s/%s"%(starts_with,ends_with)


def invoice_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "IV")


def retailer_sp_invoice(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "IV")


def required_fields(form, fields_list):
    for field in fields_list:
        form.fields[field].required = True
