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
from django.http import HttpResponse
from celery.task import task

# app imports
from retailer_backend import common_function as CommonFunction
from retailer_backend.settings import WHATSAPP_API_ENDPOINT, WHATSAPP_API_USERID, WHATSAPP_API_PASSWORD

# third party imports
from api2pdf import Api2Pdf

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
        a2p_client = Api2Pdf(config('API2PDF_KEY'))
        merge_result = a2p_client.merge(file_path_list, file_name=merge_pdf_name)
        return merge_result.result['pdf']
    except Exception as e:
        error_logger.exception(e)


def create_file_name(file_prefix, unique_id):
    """

    :param file_prefix: append the prefix according to object
    :param unique_id: unique id
    :return: file name
    """
    # return unique name of pdf file
    return file_prefix + str(unique_id) + '.pdf'


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
            if ordered_product.shipment_status == "READY_TO_SHIP":
                CommonFunction.generate_invoice_number(
                    'invoice_no', ordered_product.pk,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk,
                    ordered_product.invoice_amount)
        elif ordered_product.order.ordered_cart.cart_type == 'BASIC':
            if ordered_product.shipment_status == "FULLY_DELIVERED_AND_VERIFIED":
                CommonFunction.generate_invoice_number(
                    'invoice_no', ordered_product.pk,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk,
                    ordered_product.invoice_amount)
        elif ordered_product.order.ordered_cart.cart_type == 'RETAIL':
            if ordered_product.shipment_status == "READY_TO_SHIP":
                CommonFunction.generate_invoice_number(
                    'invoice_no', ordered_product.pk,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk,
                    ordered_product.invoice_amount)
        elif ordered_product.order.ordered_cart.cart_type == 'DISCOUNTED':
            if ordered_product.shipment_status == "READY_TO_SHIP":
                CommonFunction.generate_invoice_number_discounted_order(
                    'invoice_no', ordered_product.pk,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk,
                    ordered_product.invoice_amount)
        elif ordered_product.order.ordered_cart.cart_type == 'BULK':
            if ordered_product.shipment_status == "READY_TO_SHIP":
                CommonFunction.generate_invoice_number_bulk_order(
                    'invoice_no', ordered_product.pk,
                    ordered_product.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk,
                    ordered_product.invoice_amount)

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
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        data_string = "method=OPT_IN&format=json&password=" + whatsapp_user_password + "&phone_number=" + phone_number +" +&v=1.1&auth_scheme=plain&channel=whatsapp"
        opt_in_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(opt_in_api)
        if json.loads(response.text)['response']['status'] == 'success':
            whatsapp_invoice_send.delay(phone_number, shop_name, media_url, file_name)
            return True
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
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = "Thank you for shopping at " +shop_name+"! Please find your invoice."
        data_string = "method=SendMediaMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&isHSM=true&msg_type=Document&media_url="+media_url + "&filename=" + file_name + "&caption=" + caption
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
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = "Hi! Your Order " +order_number+" has been cancelled. Please shop again at "+shop_name+"."
        data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&msg=" + caption
        cancel_order_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(cancel_order_api)
        if json.loads(response.text)['response']['status'] == 'success':
            if points_credit or points_debit:
                whatsapp_order_cancel_loyalty_points.delay(order_number, phone_number, points_credit, points_debit,
                                                           net_points)
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


@task()
def whatsapp_order_refund(order_number, order_status, phone_number, refund_amount, points_credit, points_debit,
                          net_points):
    """
    request param:- order number
    request param:- order_status
    request param:- phone_number
    request param:- refund_amount
    return :- Ture if success else False
    """
    try:
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = "Hi! Your Order " +order_number+" has been "+order_status+". Your refund amount is "+str(refund_amount)+" INR."
        data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&msg=" + caption
        refund_order_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(refund_order_api)
        if json.loads(response.text)['response']['status'] == 'success':
            if points_credit or points_debit:
                whatsapp_order_return_loyalty_points.delay(order_number, order_status, phone_number, points_credit,
                                                           points_debit, net_points)
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


@task()
def whatsapp_order_cancel_loyalty_points(order_number, phone_number, debit_points, credit_points, net_points):
    try:
        return
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = "Hi! "
        data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&msg=" + caption
        cancel_order_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(cancel_order_api)
        if json.loads(response.text)['response']['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


@task()
def whatsapp_order_return_loyalty_points(order_number, order_status, phone_number, points_credit, points_debit,
                                         net_points):
    try:
        return
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = "Hi! "
        data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&msg=" + caption
        cancel_order_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(cancel_order_api)
        if json.loads(response.text)['response']['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False


@task()
def whatsapp_order_place_loyalty_points(order_number, phone_number, points_credit, points_debit, net_points):
    try:
        return
        api_end_point = WHATSAPP_API_ENDPOINT
        whatsapp_user_id = WHATSAPP_API_USERID
        whatsapp_user_password = WHATSAPP_API_PASSWORD
        caption = "Hi! "
        data_string = "method=SendMessage&format=json&password=" + whatsapp_user_password + "&send_to=" + phone_number +" +&v=1.1&auth_scheme=plain&&msg_type=HSM&msg=" + caption
        cancel_order_api = api_end_point + "userid=" + whatsapp_user_id + '&' + data_string
        response = requests.get(cancel_order_api)
        if json.loads(response.text)['response']['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        error_logger.error(e)
        return False
