
from django.core.exceptions import ObjectDoesNotExist
from shops.models import Shop,ParentRetailerMapping
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

def po_pattern(city_id,invoice_id):

    """ PO pattern

    Getting city code using city_id from InvoiceCityMapping.
    If city mapping not found, default city code is usedself.
    invoice id is the id of created instance.
    """

    starts_with = getattr(settings, 'PO_STARTS_WITH', 'ADT/PO')
    default_city_code = getattr(settings, 'DEFAULT_CITY_CODE', '07')
    city_code_mapping = InvoiceCityMapping.objects.filter(city_id=city_id)
    if city_code_mapping.exists():
        city_code = city_code_mapping.last().city_code
    else:
        city_code = default_city_code
    ends_with = format(invoice_id,'05d')
    return "%s/%s/%s" % (starts_with,city_code,ends_with)

def order_id_pattern(order_id):

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

    """GRN pattern

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

def brand_debit_note_pattern( id):

    starts_with = datetime.date.today().strftime('%d%m%y')
    ends_with = str(id)
    return "%s/%s"%(starts_with,ends_with)

def brand_credit_note_pattern(cid, invoice_pattern):

    starts_with = invoice_pattern
    ends_with = str(cid).rjust(5, '0')
    return "%s%s"%(starts_with,ends_with)

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

def invoice_pattern(invoice_id, **kwargs):

    """ Invoice pattern

    Getting city code using city_id from InvoiceCityMapping.
    If city mapping not found, default city code is used.
    invoice id is the id of created instance.
    """

    starts_with = getattr(settings, 'INVOICE_STARTS_WITH', 'ADT')
    default_city_code = getattr(settings, 'DEFAULT_CITY_CODE', '07')
    city_code = default_city_code
    if 'city_id' in kwargs:
        city_id = kwargs.get('city_id')
        city_code_mapping = InvoiceCityMapping.objects.filter(city_id=city_id)
        if city_code_mapping.exists():
            city_code = city_code_mapping.last().city_code
    ends_with = format(invoice_id,'05d')
    return "%s/%s/%s" % (starts_with,city_code,ends_with)


def retailer_sp_invoice(prefix, invoice_id):
    starts_with = prefix
    ends_with = str(invoice_id).rjust(5, '0')
    return "%s%s" % (starts_with, ends_with)
