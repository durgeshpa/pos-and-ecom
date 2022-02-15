# python imports
import datetime
import logging
from decouple import config

# app imports
from wms.models import PosInventory
from services.models import  PosInventoryHistoric
from coupon.models import Coupon
from .models import PaymentReconsile, Payment
from retailer_backend.common_function import bulk_create
import hashlib
import requests
from retailer_to_sp.models import Order
import datetime
# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')


def deactivate_coupon_combo_offer():
    """
        Cron job for set status False in Coupon & RuleSetProductMapping model if expiry date is less then current date
        :return:
    """
    try:
        cron_logger.info('cron job for deactivate the coupon_combo_offer|started')
        today = datetime.datetime.today()
        coupon_obj = Coupon.objects.filter(is_active=True, expiry_date__lt=today.date(),
                                           shop__shop_type__shop_type='f')
        if coupon_obj:
            coupon_obj.update(is_active=False)
            cron_logger.info('object is successfully updated from Coupon model for status False')
        else:
            cron_logger.info('no object is getting from Coupon & RuleSetProductMapping Capping model for status False')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in Coupon/RuleSetProductMapping status deactivated cron')

def pos_archive_inventory_cron():

    try:
        cron_logger.info("POS : Archiving POS inventory data started at {}".format(datetime.datetime.now()))
        pos_inventory_list = PosInventory.objects.all()
        bulk_create(PosInventoryHistoric, pos_inventory_data_generator(pos_inventory_list))
        cron_logger.info("POS : Archiving POS inventory data ended at {}".format(datetime.datetime.now()))
    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception in pos_archive_inventory')


def pos_inventory_data_generator(data):
    for row in data:
        yield PosInventoryHistoric(
                                    product=row.product,
                                    quantity=row.quantity,
                                    inventory_state=row.inventory_state,
                                    created_at=row.created_at,
                                    modified_at=row.modified_at
                                    )

def hash_gen(trxn_id, key, commond):
    """Create hash ........."""
    salt = str(config('PAYU_SALT'))
    hash_string = "{}|{}|{}|{}".format(key, commond, trxn_id, salt)
    return hashlib.sha512(hash_string.encode()).hexdigest().lower()

def send_request_payu_api(trxn_id):
    """Send post request for very thr tranjection......."""
    key = str(config('PAYU_KEY'))
    commond = 'verify_payment'
    url = "https://info.payu.in/merchant/postservice?form=2"
    headers = { "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded" }
    hash_value = hash_gen(trxn_id, key, commond)
    payload = "key={}&command={}&var1={}&hash={}".format(key,commond ,trxn_id,hash_value)
    return requests.request("POST", url, data=payload, headers=headers).json().get('transaction_details')

def payment_reconsilations(trxn_id):
    """payment reconciliation status update ......"""
    try:
        response = send_request_payu_api(trxn_id)
        obj , created = PaymentReconsile.objects.get_or_create(tranjection_id=trxn_id)
        if created:
            pass
            #obj.order_id=199905
        if response[trxn_id].get('status') == 'failure' and obj.reconcile_status !=  "payment_failed":
            obj.reconcile_status = 'payment_failed'
            obj.payment_id = response[trxn_id].get('mihpayid',None)
            obj.amount = response[trxn_id].get('transaction_amount',None)
            obj.count +=1
        elif response[trxn_id].get('status') == 'success' and obj.reconcile_status !=  "payment_success":
            obj.reconcile_status = 'payment_success'
            obj.payment_id = response[trxn_id].get('mihpayid',None)
            obj.amount = response[trxn_id].get('transaction_amount',None)
            obj.payment_mode = response[trxn_id].get('mode',None)
            obj.count +=1
        elif response[trxn_id].get('status') == 'Not Found' and obj.reconcile_status !=  "payment_not_found":
            obj.reconcile_status = "payment_not_found"
            obj.payment_id = response[trxn_id].get('mihpayid',None)
            obj.amount = response[trxn_id].get('transaction_amount',None)
            obj.count +=1
        obj.save()


    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception during order payment_reconsilation .........')


def payment_reconsilation():
    cron_logger.info('cron_perminutes payment_reconsilation start..........................')
    try:
        time_threshold = datetime.datetime.now() - datetime.timedelta(minutes=1)
        objects = Payment.objects.filter(payment_type__type="online" , created_at__gt=time_threshold).values("order__ordered_cart_id")
        for obj in objects:
            try:
               payment_reconsilations(str(obj['order__ordered_cart_id']))
            except Exception as e:
                cron_logger.error(e)
                cron_logger.error('Exception during getting trnjection id .........')
    except Exception as e:
        cron_logger.error(e)


def payment_reconsilation_per_ten_minutes():
    cron_logger.info('cron_per 10 minutes payment_reconsilation start..........................')
    time_threshold = datetime.datetime.now() - datetime.timedelta(minutes=10)
    objects = Payment.objects.filter(payment_type__type="online" , created_at__gt=time_threshold).values("order__ordered_cart_id")
    for obj in objects:
        try:
           payment_reconsilations(str(obj['order__ordered_cart_id']))
        except Exception as e:
            cron_logger.error(e)
            cron_logger.error('Exception during getting trnjection id .........')


def payment_reconsilation_per_24_hours():
    cron_logger.info('cron_per 24 minutes payment_reconsilation start..........................')
    time_threshold = datetime.datetime.now() - datetime.timedelta(hours=24)
    objects = Payment.objects.filter(payment_type__type="online" , created_at__gt=time_threshold).values("order__ordered_cart_id")
    for obj in objects:
        try:
           payment_reconsilations(str(obj['order__ordered_cart_id']))
        except Exception as e:
            cron_logger.error(e)
            cron_logger.error('Exception during getting trnjection id .........')
