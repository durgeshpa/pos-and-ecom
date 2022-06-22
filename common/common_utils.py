# python imports
import requests
import json
import datetime
import hmac
import hashlib
import logging
from functools import reduce
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from decouple import config

# django imports
from django.utils.http import urlencode
from django.http import HttpResponse
from celery.task import task

# app imports
from retailer_backend import common_function as CommonFunction
from retailer_backend.settings import WHATSAPP_API_ENDPOINT, WHATSAPP_API_USERID, WHATSAPP_API_PASSWORD

# third party imports
from api2pdf import Api2Pdf
from marketing.sms import SendSms

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def convert_date_format_ddmmmyyyy(scheduled_date):
    # This function converts %Y-%m-%d datetime format to a DD/MMM/YYYY

    # logging.info("converting date format from %d/%m/%Y to %Y-%m-%d")
    return datetime.datetime.strptime(scheduled_date, '%Y-%m-%d').strftime("%d/%b/%Y").__str__()


def concatenate_values(x1, x2):
    return str(x1) + "|" + str(x2)


def generate_message(values):
    reduce(concatenate_values, values)


def convert_hash_using_hmac_sha256(payload):
    # generate message by concatenating the value of all request parameters
    # in ascending
    # order with separator as |

    message = sorted(payload.iteritems(), key=lambda x: x[1])
    message = generate_message(message.values())
    signature = hmac.new(bytes(API_SECRET, 'latin-1'), msg=bytes(message, 'latin-1'),
                         digestmod=hashlib.sha256).hexdigest().upper()
    return signature


def merge_pdf_files(file_path_list, merge_pdf_name):
    """

    :param file_path_list: list of pdf file path
    :param merge_pdf_name: name of merged file name
    :return:
    """
    try:
        info_logger.info("API2PDF_KEY :: {}".format(config('API2PDF_KEY')))
        a2p_client = Api2Pdf(config('API2PDF_KEY'))
        merge_result = a2p_client.merge(file_path_list, file_name=merge_pdf_name)
        return merge_result.result['pdf']
    except Exception as e:
        error_logger.exception(e)


def create_file_name(file_prefix, unique_id, **kwargs):
    """

        :param file_prefix: append the prefix according to object
        :param unique_id: unique id
        :param file_extention: file type extention without '.'. Default is pdf
        :param with_timestamp: filename to include current timestamp Default is False
        :return: file name
    """
    file_name = file_prefix + str(unique_id)

    file_extention = 'pdf'

    if kwargs.get('file_extention'):
        file_extention = kwargs.get('file_extention')

    if kwargs.get('with_timestamp'):
        file_name = file_name + "_" + str(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))

    file_name = file_name + "." + file_extention

    return file_name


def create_merge_pdf_name(prefix_file_name, pdf_created_date):
    """

    :param prefix_file_name: Prefix of File name
    :param pdf_created_date: list of created date of every pdf files
    :return: merged file name
    """
    # return unique name of pdf file
    if len(pdf_created_date) <= 1:
        file_name = prefix_file_name+'_'+pdf_created_date[0].strftime("%d_%b_%y_%H_%M")+'.pdf'
    else:
        pdf_created_date = sorted(pdf_created_date)
        file_name = prefix_file_name + '_' + pdf_created_date[-1].strftime(
            "%d_%b_%y_%H_%M")+'-'+pdf_created_date[0].strftime("%d_%b_%y_%H_%M")+'.pdf'
    return file_name


def single_pdf_file(obj, result, file_prefix):
    """

    :param obj: object of order/ordered product
    :param result: pdf data
    :param file_prefix: prefix of file name for single file
    :return: pdf file object
    """
    try:
        filename = create_file_name(file_prefix, obj)
        response = HttpResponse(result.content, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response
    except Exception as e:
        error_logger.exception(e)


def create_invoice_data(ordered_product):
    """

    :param ordered_product: object of ordered_product
    :return:
    """
    try:
        if ordered_product.order.ordered_cart.cart_type == 'AUTO':
            if ordered_product.shipment_status == "MOVED_TO_DISPATCH":
                CommonFunction.generate_invoice_number(ordered_product,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        elif ordered_product.order.ordered_cart.cart_type == 'BASIC':
            if ordered_product.shipment_status == "FULLY_DELIVERED_AND_VERIFIED":
                CommonFunction.generate_invoice_number(ordered_product,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        elif ordered_product.order.ordered_cart.cart_type in ['ECOM', 'SUPERSTORE']:
            if ordered_product.shipment_status == "MOVED_TO_DISPATCH":
                CommonFunction.generate_invoice_number(ordered_product,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk,
                                                       "EV")
        elif ordered_product.order.ordered_cart.cart_type in ['RETAIL', 'SUPERSTORE_RETAIL']:
            if ordered_product.shipment_status == "MOVED_TO_DISPATCH":
                CommonFunction.generate_invoice_number(ordered_product,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        elif ordered_product.order.ordered_cart.cart_type == 'DISCOUNTED':
            if ordered_product.shipment_status == "MOVED_TO_DISPATCH":
                CommonFunction.generate_invoice_number_discounted_order(ordered_product,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)
        elif ordered_product.order.ordered_cart.cart_type == 'BULK':
            if ordered_product.shipment_status == "MOVED_TO_DISPATCH":
                CommonFunction.generate_invoice_number_bulk_order(ordered_product,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk)

        if ordered_product.no_of_crates is None:
            ordered_product.no_of_crates = 0
        if ordered_product.no_of_packets is None:
            ordered_product.no_of_packets = 0
        if ordered_product.no_of_sacks is None:
            ordered_product.no_of_sacks = 0
    except Exception as e:
        error_logger.exception(e)


def barcode_gen(value):
    ean = barcode.get_barcode_class('code128')
    ean = ean(value, writer=ImageWriter())
    image = ean.render()
    output_stream = BytesIO()
    image_resize = image.resize((900, 300))
    image_resize.save(output_stream, format='JPEG', quality=150)
    output_stream.seek(0)
    return output_stream

@task()
def whatsapp_opt_in(phone_number, shop_name, media_url, file_name):
    """
    request param:- phone number
    return :- Ture if success else False
    """
    try:
        if phone_number == '9999999999':
            return False
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        data_string = "method=OPT_IN&format=json&password=" + whatsapp_user_password + "&phone_number=" + phone_number +" +&v=1.1&auth_scheme=plain&channel=whatsapp"
        opt_in_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        # response = requests.get(opt_in_api)
        if requests.get(opt_in_api).status_code == 200:
            if whatsapp_invoice_send(phone_number, shop_name, media_url, file_name):
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


@task()
def whatsapp_invoice_send(phone_number, shop_name, media_url, file_name):
    """
    request param:- phone_number
    request param:- shop_name
    request param:- media_url
    request param:- file_name
    return :- Ture if success else False
    """
    try:
        if phone_number == '9999999999':
            return False
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = urlencode({"caption": "Thank you for shopping at " +shop_name+"! Please find your invoice."})
        data_string = "method=SendMediaMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&isHSM=true&msg_type=Document&media_url="+media_url + "&filename=" + file_name + "&" + caption
        invoice_send_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(invoice_send_api)
        if json.loads(response.text)['response']['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


@task()
def whatsapp_order_cancel(order_number, shop_name, phone_number, points_credit, points_debit, net_points):
    """
    request param:- order number
    request param:- shop_name
    request param:- phone_number
    return :- Ture if success else False
    """
    try:
        if phone_number == '9999999999':
            return False
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = urlencode({"msg":"Hi! Your Order " +order_number+" has been cancelled. Please shop again at "+shop_name+"."})
        data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&" + caption
        cancel_order_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(cancel_order_api)
        if json.loads(response.text)['response']['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


# @task()
# def whatsapp_order_refund(order_number, order_status, phone_number, refund_amount, points_credit, points_debit,
#                           net_points, shop_name, media_url, file_name):
#     """
#     request param:- order number, order_status, phone_number, refund_amount
#     request param:- points_credit, points_debit, net_points
#     request param:- shop_name, media_url, file_name
#     return :- Ture if success else False
#     """
#     try:
#         api_end_point = WHATSAPP_API_ENDPOINT
#         whatsapp_user_id = WHATSAPP_API_USERID
#         whatsapp_user_password = WHATSAPP_API_PASSWORD
#         caption = "Hi! Your Order " +order_number+" has been "+order_status+". Your refund amount is "+str(refund_amount)+" INR."
#         data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&msg=" + caption
#         refund_order_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
#         response = requests.get(refund_order_api)
#         if json.loads(response.text)['response']['status'] == 'success':
#             whatsapp_credit_note_send.delay(phone_number, shop_name, media_url, file_name)
#             return True
#         else:
#             return False
#     except Exception as e:
#         error_logger.error(e)
#         return False


@task()
def whatsapp_order_refund(order_number, order_status, phone_number, refund_amount, media_url, file_name):
    """
    request param:- phone_number
    request param:- shop_name
    request param:- media_url
    request param:- file_name
    return :- Ture if success else False
    """
    try:
        if phone_number == '9999999999':
            return False
        order_status = order_status.replace('_', ' ')
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = "Hi! Your Order " +order_number+" has been "+order_status+". Your refund amount is "+str(refund_amount)+" INR! Please find your credit note."
        data_string = "method=SendMediaMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&isHSM=true&msg_type=Document&media_url="+media_url + "&filename=" + file_name + "&caption=" + caption
        credit_note_send_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(credit_note_send_api)
        if json.loads(response.text)['response']['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


@task()
def whatsapp_order_delivered(order_number, shop_name, phone_number, points, credit):
    try:
        if phone_number == '9999999999':
            return False
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        if credit:
            msg = urlencode({"msg":"Hi! Your Order no "+order_number+" is successfully delivered, "+str(points)+" pep coins are credited in your account. Please shop again at "+shop_name+"."})
        else:
            msg = urlencode({"msg":"Hi! Your Order no "+order_number+" is successfully delivered. Please shop again at "+shop_name+"."})
        data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&" + msg
        order_delivered_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(order_delivered_api)
        if json.loads(response.text)['response']['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False
@task
def sms_order_placed(name, number):
    '''Send sms affter order_created ...'''
    try:
        body = f"Hey {name}! Your PepperTap order has been confirmed! We will update you once your order is dispatched. In case of any query, contact us on care@peppertap.in"
        message = SendSms(phone=number, body=body, mask="PEPTAB")
        message.send()
    except Exception as e:
        error_logger.error(e)
@task
def sms_order_dispatch(name, number):
    '''Send sms affter order_dispatch ...'''
    try:
        body = f"Dear {name}, Your order has been dispatched & will be delivered to you soon. Team PepperTap"
        message = SendSms(phone=number, body=body, mask="PEPTAB")
        message.send()
    except Exception as e:
        error_logger.error(e)

@task
def sms_out_for_delivery(name, number):
    '''Send sms affter out_for_delivery order...'''
    try:
        body = f"Wait is almost Over! Your PepperTap order is out for delivery. Our delivery partner will reach out to you soon."
        message = SendSms(phone=number, body=body, mask="PEPTAB")
        message.send()
    except Exception as e:
        error_logger.error(e)

@task
def sms_order_delivered(name, number):
    '''Send sms affter delivered order...'''
    try:
        url = "shorturl.at/lsBFI"
        body = f"YAY! Your PepperTap order has been successfully delivered. Please click here - {url} to rate us on PlayStore."
        message = SendSms(phone=number, body=body, mask="PEPTAB")
        message.send()
    except Exception as e:
        error_logger.error(e)


@task
def return_item_drop(name, number, address, time="5 pm"):
    '''
        Send sms for return method drop at store
    '''
    try:
        body = f"Hi {name}, Your return request has been accepted. Please drop your package at the {address} address - {time} by tomorrow. Team PepperTap."
        message = SendSms(phone=number, body=body, mask="PEPTAB")
        message.send()
    except Exception as e:
        error_logger.error(e)


@task
def return_item_home_pickup(name, number):
    '''
        Send sms for return method home pick up
    '''
    try:
        body = f"Hi {name}, Your return request has been accepted. Please keep the package ready, our delivery partner will reach out to you soon. Team PepperTap."
        message = SendSms(phone=number, body=body, mask="PEPTAB")
        message.send()
    except Exception as e:
        error_logger.error(e)