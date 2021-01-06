# python imports
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

# app imports
from retailer_backend import common_function as CommonFunction
from retailer_to_sp.models import Order

# third party imports
from api2pdf import Api2Pdf

logger = logging.getLogger(__name__)


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
        logger.exception(e)


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
        logger.exception(e)


def create_invoice_data(ordered_product):
    """

    :param ordered_product: object of ordered_product
    :return:
    """
    try:
        if ordered_product.order.ordered_cart.cart_type == 'RETAIL':
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
        logger.exception(e)


def barcode_gen(value):
    ean = barcode.get_barcode_class('code128')
    ean = ean(value, writer=ImageWriter())
    image = ean.render()
    output_stream = BytesIO()
    image_resize = image.resize((900, 300))
    image_resize.save(output_stream, format='JPEG', quality=150)
    output_stream.seek(0)
    return output_stream

#
# def barcode_decoder(value):
# 	image = Image.open(value)
# 	image = image.convert('L')
# 	data = decode(image)
# 	return str(data[0][0])


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
    capping_range_orders = Order.objects.filter(buyer_shop=parent_mapping.retailer,
                                                created_at__gte=capping_start_date,
                                                created_at__lte=capping_end_date).exclude(order_status='CANCELLED')
    if capping_range_orders:
        for order in capping_range_orders:
            if order.ordered_cart.rt_cart_list.filter(
                    cart_product=cart_product.cart_product).exists():
                ordered_qty += order.ordered_cart.rt_cart_list.filter(
                    cart_product=cart_product.cart_product).last().qty
    if capping.capping_qty > ordered_qty:
        if (capping.capping_qty - ordered_qty) < product_qty:
            if (capping.capping_qty - ordered_qty) > 0:
                cart_product.capping_error_msg = 'The Purchase Limit of the Product is %s' % (
                        capping.capping_qty - ordered_qty)
            else:
                cart_product.capping_error_msg = 'You have already exceeded the purchase limit of this product'
            cart_product.save()
            return False, cart_product.capping_error_msg
        else:
            cart_product.capping_error_msg = 'Allow to reserve the Product'
            return True, cart_product.capping_error_msg
    else:
        if (capping.capping_qty - ordered_qty) > 0:
            cart_product.capping_error_msg = 'The Purchase Limit of the Product is %s' % (
                    capping.capping_qty - ordered_qty)
        else:
            cart_product.capping_error_msg = 'You have already exceeded the purchase limit of this product'
        cart_product.save()
        return False, cart_product.capping_error_msg


def check_date_range(capping):
    """
    capping object
    return start date and end date
    """
    if capping.capping_type == 0:
        return capping.start_date, capping.end_date
    elif capping.capping_type == 1:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=today.weekday())
        return start_date, end_date
    elif capping.capping_type == 2:
        return capping.start_date, capping.end_date