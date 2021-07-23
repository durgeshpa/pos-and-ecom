import logging
from operator import itemgetter
from django.core.files.base import ContentFile
from barCodeGenerator import barcodeGen

from wkhtmltopdf.views import PDFTemplateResponse
from num2words import num2words

from common.common_utils import create_file_name, whatsapp_order_refund
from common.constants import PREFIX_CREDIT_NOTE_FILE_NAME

logger = logging.getLogger('pdf_gen')


def pdf_generation_return_retailer(request, order, ordered_product, order_return, return_items, return_qty, \
                                    total, total_amount, points_credit, points_debit, net_points, credit_note_instance):
    """
    :param request: request object
    :param order_id: Order id
    :return: pdf instance
    """
    file_prefix = PREFIX_CREDIT_NOTE_FILE_NAME
    template_name = 'admin/credit_note/credit_note_retailer.html'

    if credit_note_instance:
        filename = create_file_name(file_prefix, credit_note_instance.credit_note_id)
        barcode = barcodeGen(credit_note_instance.credit_note_id)
        # Total Items
        return_item_listing = []
        # Total Returned Amount
        total = 0

        for item in return_items:
            return_p = {
                "id": item.id,
                "product_short_description": item.ordered_product.retailer_product.product_short_description,
                "mrp": item.ordered_product.retailer_product.mrp,
                "qty": item.return_qty,
                "rate": float(item.ordered_product.selling_price),
                "product_sub_total": float(item.return_qty) * float(item.ordered_product.selling_price)
            }
            total += return_p['product_sub_total']
            return_item_listing.append(return_p)

        return_item_listing = sorted(return_item_listing, key=itemgetter('id'))
        # redeem value
        redeem_value = order_return.refund_points if order_return.refund_points > 0 else 0
        print(order_return.refund_points, redeem_value)
        # Total discount
        discount = order_return.discount_adjusted if order_return.discount_adjusted > 0 else 0
        # Total payable amount in words
        
        
        # Total payable amount
        total_amount = order_return.refund_amount if order_return.refund_amount > 0 else 0
        total_amount_int = round(total_amount)
        # Total payable amount in words
        amt = [num2words(i) for i in str(total_amount_int).split('.')]
        rupees = amt[0]


        # Shop Details
        nick_name = '-'
        address_line1 = '-'
        city = '-'
        state = '-'
        pincode = '-'
        address_contact_number = ''
        for z in ordered_product.order.seller_shop.shop_name_address_mapping.all():
            nick_name, address_line1 = z.nick_name, z.address_line1
            city, state, pincode = z.city, z.state, z.pincode
            address_contact_number = z.address_contact_number

        data = {
            "url": request.get_host(),
            "scheme": request.is_secure()and"https"or"http",
            "credit_note": credit_note_instance,
            "shipment": ordered_product,
            "order": ordered_product.order,
            "total_amount": total_amount,
            "discount": discount,
            "reward_value": redeem_value,
            'total': total,
            "barcode": barcode,
            "return_item_listing": return_item_listing,
            "rupees": rupees,
            "sum_qty": return_qty,
            "nick_name": nick_name,
            "address_line1": address_line1,
            "city": city,
            "state": state,
            "pincode": pincode,
            "address_contact_number": address_contact_number
        }

        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=template_name, filename=filename,
                                       context=data, show_content_in_browser=False, cmd_options=cmd_option)
        try:
            # create_invoice_data(ordered_product)
            credit_note_instance.credit_note_pdf.save("{}".format(filename), ContentFile(response.rendered_content),
                                                     save=True)
            order_number = order.order_no
            order_status = order.order_status
            phone_number = order.buyer.phone_number
            refund_amount = order_return.refund_amount if order_return.refund_amount > 0 else 0
            media_url = credit_note_instance.credit_note_pdf.url
            file_name = ordered_product.invoice_no
            shop_name = ordered_product.order.seller_shop.shop_name
            whatsapp_order_refund(order_number, order_status, phone_number, refund_amount, points_credit,
                                        points_debit, net_points, shop_name, media_url, file_name)
        except Exception as e:
            logger.exception(e)


