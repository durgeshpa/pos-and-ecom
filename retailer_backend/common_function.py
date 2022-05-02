import itertools

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage

from common.constants import BULK_CREATE_NO_OF_RECORDS
from global_config.views import get_config
from retailer_to_sp.models import BuyerPurchaseData
from shops.models import Shop, ParentRetailerMapping, ShopDocument
from addresses.models import Address
from rest_framework import status
from addresses.models import InvoiceCityMapping
from rest_framework.response import Response
from django.conf import settings
import datetime
from django.core.cache import cache
from retailer_to_sp import models as RetailerToSPModels
from celery.task import task


# get shop
def checkShop(shop_id):
    try:
        shop = Shop.objects.get(id=shop_id, status=True)
        return True
    except ObjectDoesNotExist:
        return False


def checkShopMapping(shop_id):
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
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
        shop = Shop.objects.get(id=shop_id, status=True)
        return shop
    except ObjectDoesNotExist:
        return None


def getShopMapping(shop_id):
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id, status=True)
        return parent_mapping
    except ObjectDoesNotExist:
        return None


def get_financial_year(year_format='%y'):
    current_month = datetime.date.today().strftime('%m')
    current_year = datetime.date.today().strftime(year_format)

    if int(current_month) < 4:
        current_year = str(int(datetime.date.today().strftime(year_format)) - 1)
    return current_year


def get_shop_warehouse_code(shop):
    return str(shop.shop_code), str(shop.shop_code_bulk), str(shop.shop_code_discounted), str(shop.warehouse_code)


def get_shop_warehouse_state_code(address):
    address = Address.objects.select_related('state',
                                             'shop_name').get(pk=address)
    state_code = format(int(address.state.state_code), '02d')
    shop_code, shop_code_bulk, shop_code_discounted, warehouse_code = get_shop_warehouse_code(address.shop_name)
    return state_code, shop_code, shop_code_bulk, shop_code_discounted, warehouse_code


def get_last_no_to_increment(model, field, instance_id, starts_with):
    prefix = "{}_{}_{}"
    instance_with_current_pattern = model.objects.filter(
        **{field + '__icontains': starts_with})
    if instance_with_current_pattern.exists():
        last_instance_no = model.objects.filter(**{field + '__icontains': starts_with}).latest(field)
        return int(getattr(last_instance_no, field)[-7:])

    else:
        return 0


def get_last_model_invoice(starts_with, field):
    shipment_instance = RetailerToSPModels.Invoice.objects.filter(invoice_no__icontains=starts_with)
    if shipment_instance.exists():
        last_instance_no = shipment_instance.latest('invoice_no')
        return int(getattr(last_instance_no, 'invoice_no')[-7:])
    else:
        return 0


def common_pattern(model, field, instance_id, address, invoice_type, is_invoice=False, year=None):
    state_code, shop_code, shop_code_bulk, shop_code_discounted, warehouse_code = get_shop_warehouse_state_code(
        address)
    financial_year = year if year else get_financial_year()
    starts_with = "%s%s%s%s%s" % (
        shop_code, invoice_type, financial_year,
        state_code, warehouse_code)
    try:
        last_number = cache.incr(starts_with)
    except:
        if is_invoice:
            last_number = get_last_model_invoice(starts_with, field)
        else:
            last_number = get_last_no_to_increment(model, field, instance_id, starts_with)
        last_number += 1
        cache.set(starts_with, last_number)
        cache.persist(starts_with)

    if len(warehouse_code) == 3 and shop_code == 'F':
        ends_with = str(format(last_number, '06d'))
    else:
        ends_with = str(format(last_number, '07d'))
    return "%s%s" % (starts_with, ends_with)


def common_pattern_bulk(model, field, instance_id, address, invoice_type, is_invoice=False, year=None):
    state_code, shop_code, shop_code_bulk, shop_code_discounted, warehouse_code = get_shop_warehouse_state_code(
        address)
    financial_year = year if year else get_financial_year()
    starts_with = "%s%s%s%s%s" % (
        shop_code_bulk, invoice_type, financial_year,
        state_code, warehouse_code)
    try:
        last_number = cache.incr(starts_with)
    except:
        if is_invoice:
            last_number = get_last_model_invoice(starts_with, field)
        else:
            last_number = get_last_no_to_increment(model, field, instance_id, starts_with)
        last_number += 1
        cache.set(starts_with, last_number)
        cache.persist(starts_with)
    ends_with = str(format(last_number, '07d'))
    return "%s%s" % (starts_with, ends_with)


def common_pattern_discounted(model, field, instance_id, address, invoice_type, is_invoice=False, year=None):
    state_code, shop_code, shop_code_bulk, shop_code_discounted, warehouse_code = get_shop_warehouse_state_code(
        address)
    financial_year = year if year else get_financial_year()
    starts_with = "%s%s%s%s%s" % (
        shop_code_discounted, invoice_type, financial_year,
        state_code, warehouse_code)
    try:
        last_number = cache.incr(starts_with)
    except:
        if is_invoice:
            last_number = get_last_model_invoice(starts_with, field)
        else:
            last_number = get_last_no_to_increment(model, field, instance_id, starts_with)
        last_number += 1
        cache.set(starts_with, last_number)
        cache.persist(starts_with)
    ends_with = str(format(last_number, '07d'))
    return "%s%s" % (starts_with, ends_with)


def po_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "PO")


def order_id_pattern(model, field, instance_id, address, const="OR"):
    return common_pattern(model, field, instance_id, address, const)


def order_id_pattern_discounted(model, field, instance_id, address):
    return common_pattern_discounted(model, field, instance_id, address, "OR")


def order_id_pattern_bulk(model, field, instance_id, address):
    return common_pattern_bulk(model, field, instance_id, address, "OR")


def payment_id_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "PA")


def order_id_pattern_r_gram(order_id):
    """ Order ID pattern

    Using 07 as the default city code for the pattern.
    order id is the id of created instance.
    """

    starts_with = getattr(settings, 'INVOICE_STARTS_WITH', 'ADT')
    default_city_code = getattr(settings, 'DEFAULT_CITY_CODE', '07')
    city_code = default_city_code
    ends_with = str(order_id).rjust(5, '0')
    return "%s/%s/%s" % (starts_with, city_code, ends_with)


def grn_pattern(id):
    """GRN patternbrand_note_id

    GRN year changes on 1st April(4th month).
    Getting id as instance id for auto increment.
    """

    current_month = datetime.date.today().strftime('%m')
    current_year = datetime.date.today().strftime('%y')
    next_year = str(int(current_year) + 1)

    if int(current_month) < 4:
        current_year = str(int(datetime.date.today().strftime('%y')) - 1)
        next_year = datetime.date.today().strftime('%y')
    starts_with = "%s-%s" % (current_year, next_year)
    ends_with = str(id)
    return "%s/%s" % (starts_with, ends_with)


def brand_debit_note_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "DN")


def brand_credit_note_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "CN")


def discounted_credit_note_pattern(model, field, instance_id, address):
    return common_pattern_discounted(model, field, instance_id, address, "CN")


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
        return "%s/%s" % (starts_with, ends_with)

    elif note_type == 'credit_note':
        starts_with = getattr(settings, 'CN_STARTS_WITH', 'ADT/CN')
        ends_with = str(id).rjust(5, '0')
        return "%s/%s" % (starts_with, ends_with)


def invoice_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "IV")


def retailer_sp_invoice(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "IV")


def required_fields(form, fields_list):
    for field in fields_list:
        form.fields[field].required = True


def repackaging_no_pattern(model, field, instance_id, address):
    return common_pattern(model, field, instance_id, address, "RP")


def create_invoice(shipment_instance):
    '''
    Creates the invoice for the given OrderedProduct instance
    '''
    invoice_sub_total = shipment_instance.invoice_amount

    is_tcs_applicable, tcs_amount, tcs_percent = get_tcs_data(shipment_instance)
    invoice_total = invoice_sub_total + tcs_amount
    return RetailerToSPModels.Invoice.objects.get_or_create(shipment_id=shipment_instance.id,
                                                            defaults={'invoice_sub_total': invoice_sub_total,
                                                                      'is_tcs_applicable': is_tcs_applicable,
                                                                      'tcs_percent': tcs_percent,
                                                                      'tcs_amount': tcs_amount,
                                                                      'invoice_total': invoice_total})


def get_tcs_data(shipment_instance):
    '''
    Calculates TCS tax if applicable
    Updates Total Buyer purchase in the current financial year
    '''
    if hasattr(shipment_instance, 'invoice'):
        return shipment_instance.invoice.is_tcs_applicable, shipment_instance.invoice.tcs_amount, \
               shipment_instance.invoice.tcs_percent

    elif shipment_instance.order.seller_shop_id not in get_config('active_wh_list'):
        return False, 0, 0
    
    invoice_amount = shipment_instance.invoice_amount
    is_tcs_applicable = False
    tcs_percent = 0
    tcs_amount = 0
    total_purchase = invoice_amount
    purchase_data = BuyerPurchaseData.objects.filter(seller_shop_id=shipment_instance.order.seller_shop_id,
                                                     buyer_shop_id=shipment_instance.order.buyer_shop_id,
                                                     fin_year=get_financial_year('%Y')).last()
    if purchase_data:
        total_purchase += purchase_data.total_purchase
    BuyerPurchaseData.objects.update_or_create(seller_shop_id=shipment_instance.order.seller_shop_id,
                                               buyer_shop_id=shipment_instance.order.buyer_shop_id,
                                               fin_year=get_financial_year('%Y'),
                                               defaults={'total_purchase': total_purchase})
    if total_purchase >= get_config('TCS_B2B_APPLICABLE_AMT', 5000000):
        is_tcs_applicable = True
        buyer_shop_document = ShopDocument.objects.filter(shop_name_id=shipment_instance.order.buyer_shop_id,
                                                          shop_document_type=ShopDocument.GSTIN).last()
        is_buyer_gst_available = True if buyer_shop_document else False
        tcs_percent = 0.75 if is_buyer_gst_available else 1
        tcs_amount = invoice_amount * tcs_percent / 100
    return is_tcs_applicable, tcs_amount, tcs_percent


@task
def generate_invoice_number(shipment_instance, address, const="IV", field='invoice_no'):
    shipment_id = shipment_instance.id
    instance, created = create_invoice(shipment_instance)
    if created:
        invoice_no = common_pattern(RetailerToSPModels.Invoice, field, shipment_id, address, const, is_invoice=True)
        while RetailerToSPModels.Invoice.objects.filter(invoice_no=invoice_no).exists():
            invoice_no = common_pattern(RetailerToSPModels.Invoice, field, shipment_id, address, const, is_invoice=True)
        instance.invoice_no = invoice_no
        instance.save()



@task
def generate_invoice_number_discounted_order(shipment_instance, address, field='invoice_no'):
    shipment_id = shipment_instance.id
    instance, created = create_invoice(shipment_instance)
    if created:
        invoice_no = common_pattern_discounted(RetailerToSPModels.Invoice, field, shipment_id, address, "IV",
                                               is_invoice=True)
        instance.invoice_no = invoice_no
        instance.save()


@task
def generate_invoice_number_bulk_order(shipment_instance, address, field='invoice_no'):
    shipment_id = shipment_instance.id
    instance, created = create_invoice(shipment_instance)
    if created:
        invoice_no = common_pattern_bulk(RetailerToSPModels.Invoice, field, shipment_id, address, "IV", is_invoice=True)
        instance.invoice_no = invoice_no
        instance.save()


def cart_no_pattern(model, field, instance_id, address, const="CR", year=None):
    return common_pattern(model, field, instance_id, address, const, year)


def cart_no_pattern_discounted(model, field, instance_id, address, year=None):
    return common_pattern_discounted(model, field, instance_id, address, "CR", year)


def cart_no_pattern_bulk(model, field, instance_id, address, year=None):
    return common_pattern_bulk(model, field, instance_id, address, "CR", year)


def bulk_create(model, generator, batch_size=BULK_CREATE_NO_OF_RECORDS):
    """
    Uses islice to call bulk_create on batches of
    Model objects from a generator.
    """
    while True:
        items = list(itertools.islice(generator, batch_size))
        if not items:
            break
        model.objects.bulk_create(items)


def send_mail(sender, recipient_list, subject, body, attachment_list=[], **kwargs):
    """
    Parameters:
        sender : valid email address as string
        recipient_list : list of valid email addresses
        subject : email subject as string
        body : email body as string
        attachment_list : list of file attachments
    """
    email = EmailMessage()
    email.subject = subject
    email.body = body
    email.from_email = sender
    email.to = recipient_list
    if kwargs.get('cc') is not None:
        email.cc = kwargs.get('cc')
    if kwargs.get('bcc') is not None:
        email.bcc = kwargs.get('bcc')
    for attachment in attachment_list:
        email.attach(attachment['name'], attachment['value'], attachment['type'])
    email.send()


def purchase_return_number_pattern(instance_id, order_no):
    return "%s%s%s" % ("PR", order_no, instance_id)

def isBlank (string):
    """Checks if string is blank"""
    if string and string.strip():
        return False
    return True
