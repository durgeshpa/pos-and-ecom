from django.utils.html import format_html_join, format_html
from django.utils.safestring import mark_safe


def order_invoices(shipments):
    return format_html_join(
    "","<a href='/admin/retailer_to_sp/shipment/{}/change/' target='blank'>{}</a><br><br>",
            ((s.pk,
            s.invoice_no, 
            ) for s in shipments)
    )

def order_shipment_status(shipments):
    return format_html_join(
    "","{}<br><br>",
            ((s.get_shipment_status_display(),
            ) for s in shipments)
    )   

def order_shipment_amount(shipments):
    return format_html_join(
    "","{}<br><br>",
            ((s.invoice_amount,
            ) for s in shipments)
    )
