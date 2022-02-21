# python imports
import datetime
import logging
from decouple import config

# app imports
from wms.models import PosInventory
from services.models import  PosInventoryHistoric
from coupon.models import Coupon
from pos.models import Payment, PaymentStatusUpdateByCron
from retailer_backend.common_function import bulk_create
import hashlib
import requests
from retailer_to_sp.models import Order
import datetime
from pos.payU_payment import *
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

def payment_reconsilations(trxn_id, payment_type='online', obj = None):
    """payment reconciliation status update ......"""
    try:
        response = send_request_payu_api(trxn_id)
        if response[trxn_id].get('status') == 'success' and payment_type != 'online':
            try:
                log_obj,created =  PaymentStatusUpdateByCron.objects.get_or_create(order=obj.order, payment_type=obj.payment_type)
                log_obj.payment_status = 'double_payment'
                log_obj.transaction_id = trxn_id
                log_obj.payment_id = response[trxn_id].get('mihpayid',None)
                log_obj.save()
            except Exception as e:
                cron_logger.error(e)
            obj.payment_status = 'double_payment'
            obj.transaction_id = trxn_id
            obj.payment_id = response[trxn_id].get('mihpayid',None)
            obj.save()
            return
        if response[trxn_id].get('mihpayid',None) == 'Not Found' and payment_type != 'online':
            return

        if response[trxn_id].get('status') == 'failure' and obj.payment_status !=  "payment_failed":
            try:
                log_obj,created =  PaymentStatusUpdateByCron.objects.get_or_create(order=obj.order, payment_type=obj.payment_type)
                log_obj.payment_status = 'payment_failed'
                log_obj.transaction_id = trxn_id
                log_obj.payment_id = response[trxn_id].get('mihpayid',None)
                log_obj.save()
            except Exception as e:
                cron_logger.error(e)

            obj.payment_status = 'payment_failed'
            obj.transaction_id = trxn_id
            obj.payment_id = response[trxn_id].get('mihpayid',None)

        elif response[trxn_id].get('status') == 'success' and (not obj.transaction_id or not obj.payment_id or obj.payment_id == 'Not Found'):
            log_obj = None
            if obj.payment_status != "payment_approved":
                try:
                    log_obj,created =  PaymentStatusUpdateByCron.objects.get_or_create(order=obj.order, payment_type=obj.payment_type)
                    log_obj.payment_status = "payment_approved"
                    log_obj.transaction_id = trxn_id
                    log_obj.payment_id = response[trxn_id].get('mihpayid',None)
                except Exception as e:
                    cron_logger.error(e)


            obj.payment_status = "payment_approved"
            if response[trxn_id].get('mode') == 'CC':
                obj.payment_mode = 'CREDIT_CARD'
            elif response[trxn_id].get('mode') == 'DC':
                obj.payment_mode = 'DEBIT_CARD'
            elif response[trxn_id].get('mode') == 'UPI':
                 obj.payment_mode = 'UPI'
            else:
                obj.payment_mode = 'Net Banking'

            if obj.order.order_status in [Order.PAYMENT_PENDING, Order.PAYMENT_FAILED]:
                objs = Order.objects.filter(id=obj.order.id).last()
                objs.order_status = 'ordered'
                objs.save()
            obj.transaction_id = trxn_id
            obj.payment_id = response[trxn_id].get('mihpayid',None)
            if log_obj:
                log_obj.payment_mode = obj.payment_mode
                log_obj.save()

        elif response[trxn_id].get('status') == 'Not Found' and obj.payment_status !=  "payment_not_found":
            obj.payment_status = "payment_not_found"
            obj.transaction_id = trxn_id
            obj.payment_id = response[trxn_id].get('mihpayid',None)
            try:
                log_obj,created =  PaymentStatusUpdateByCron.objects.get_or_create(order=obj.order, payment_type=obj.payment_type)
                log_obj.payment_status = "payment_not_found"
                log_obj.transaction_id = trxn_id
                log_obj.payment_id = response[trxn_id].get('mihpayid',None)
                log_obj.save()
            except Exception as e:
                cron_logger.error(e)

        obj.save()


    except Exception as e:
        cron_logger.error(e)
        cron_logger.error('Exception during order payment_reconsilation .........')


def payment_reconsilation_():
    cron_logger.info('cron_perminutes payment_reconsilation start..........................')
    try:
        time_threshold = datetime.datetime.now() - datetime.timedelta(minutes=15)
        objects = Payment.objects.filter(order__ordered_cart__cart_type='ECOM', created_at__gt=time_threshold)
        for obj in objects:
            try:
               payment_reconsilations(str(obj.order.ordered_cart_id), obj.payment_type.type, obj)
            except Exception as e:
                cron_logger.error(e)
                cron_logger.error('Exception during getting trnsection id .........')
    except Exception as e:
        cron_logger.error(e)


def payment_reconsilation_per_ten_minutes():
    cron_logger.info('cron_per 10 minutes payment_reconsilation start..........................')
    time_threshold = datetime.datetime.now() - datetime.timedelta(minutes=60)
    objects = Payment.objects.filter(order__ordered_cart__cart_type='ECOM', created_at__gt=time_threshold)
    for obj in objects:
        try:
           payment_reconsilations(str(obj.order.ordered_cart_id), obj.payment_type.type, obj)
        except Exception as e:
            cron_logger.error(e)
            cron_logger.error('Exception during getting trnsection id .........')


def payment_reconsilation_per_24_hours():
    cron_logger.info('cron_per 24 minutes payment_reconsilation start..........................')
    time_threshold = datetime.datetime.now() - datetime.timedelta(hours=24)
    objects = Payment.objects.filter(order__ordered_cart__cart_type='ECOM', created_at__gt=time_threshold)
    for obj in objects:
        try:
           payment_reconsilations(str(obj.order.ordered_cart_id), obj.payment_type.type, obj)
        except Exception as e:
            cron_logger.error(e)
            cron_logger.error('Exception during getting trnsection id .........')


def payment_refund_status_update():
    """payment Refund cron update status crone ........"""
    cron_logger.info('payment_refund_status_update start ..........................')

    objects = Payment.objects.filter(refund_status__in=['queued', 'pending'], is_refund=True)
    for obj in objects:
        request_id = obj.request_id
        try:
            response = track_status_refund(request_id)
            response = response['transaction_details'][str(request_id)][str(request_id)]
            obj.refund_status = response['status']
            obj.save()
            cron_logger.info("refund {} ".format(response['status']))
        except Exception as e:
            cron_logger.error(response)
            cron_logger.info(e)
            cron_logger.error('Exception during getting payment_refund_status_upadte start .........')
