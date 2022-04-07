import csv
import logging
from datetime import datetime, timedelta
from io import StringIO

from django.core.mail import EmailMessage

from gram_to_brand.models import CartProductMappingTaxLog
from gram_to_brand.views import mail_warehouse_for_approved_po
from global_config.models import GlobalConfig
from global_config.views import get_config

# logger configuration
info_logger = logging.getLogger('file-info')
cron_logger = logging.getLogger('cron_log')

def daily_approved_po_mail():
    mail_warehouse_for_approved_po()


def po_tax_change_csv_report():
    """
        Cron
        Email a report for all the TAX changes in PO.
    """
    try:
        cron_logger.info('cron po tax change csv report | started')
        current_time = datetime.now() - timedelta(minutes=1)
        start_time = datetime.now() - timedelta(days=1)

        cart_product_mapping_tax_logs = CartProductMappingTaxLog.objects.filter(
            created_at__lt=current_time, created_at__gt=start_time,
            cart_product_mapping__cart__order_cart_mapping__order_grn_order__isnull=False).order_by('-id')

        if not cart_product_mapping_tax_logs.exists():
            cron_logger.info('cron po tax change csv report | none Tax changed.')
            return

        if cart_product_mapping_tax_logs.exists():
            f = StringIO()
            writer = csv.writer(f)

            headings = ["GRN Id", "Invoice no", "PO number", "Product name", "HSN code", "Previous GST rate",
                        "Modified Product GST rate", "HSN code Gst rate", "Previous Cess rate", "Modified Cess rate",
                        "HSN code Cess rate", "Modified at", "Modified by"]

            writer.writerow(headings)

            for tax_log in cart_product_mapping_tax_logs:
                cart_product_mapping = tax_log.cart_product_mapping
                product = cart_product_mapping.vendor_product.product
                hsn_gst = ", ".join(map(str, product.parent_product.product_hsn.hsn_gst.values_list('gst', flat=True)))
                hsn_cess = ", ".join(map(str, product.parent_product.product_hsn.hsn_cess.values_list('cess', flat=True)))
                po_no = tax_log.cart_product_mapping.cart.po_no
                grn_order = tax_log.cart_product_mapping.cart.order_cart_mapping.order_grn_order.\
                    filter(modified_at__gte=tax_log.created_at).order_by('modified_at').first()
                if not grn_order:
                    continue
                writer.writerow([grn_order.grn_id, grn_order.invoice_no, po_no, product.product_name,
                                 product.parent_product.product_hsn, tax_log.existing_gst, tax_log.new_gst, hsn_gst,
                                 tax_log.existing_cess, tax_log.new_cess, hsn_cess,
                                 tax_log.created_at, tax_log.created_by])

            curr_date = datetime.now()
            curr_date = curr_date.strftime('%Y-%m-%d %H:%M:%S')

            email = EmailMessage()
            email.subject = 'PO Tax changes Report'
            email.body = 'PFA the list of all the TAX changes in PO. '
            sender = GlobalConfig.objects.get(key='sender')
            email.from_email = sender.value
            receiver = GlobalConfig.objects.get(key='PO_TAX_CHANGES')
            email.to = receiver.value
            email.attach('po_tax_changes_{}'.format(curr_date) + '.csv', f.getvalue(), 'text/csv')
            email.send()
            cron_logger.info('cron po tax change csv report | mailed')
        else:
            cron_logger.info('cron po tax change csv report | none below threshold')
    except Exception as e:
        cron_logger.error(e)
        cron_logger.info('cron po tax change csv report | exception')
