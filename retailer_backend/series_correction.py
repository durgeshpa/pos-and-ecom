from retailer_to_sp.models import *
from django.db.models import Q
for m in Invoice.objects.filter(Q(invoice_no__startswith='GB') | Q(invoice_no__startswith='PB')).all():
    invoice_no = m.invoice_no[2:]
    Invoice.objects.filter(id = m.id).update(invoice_no = invoice_no)

for m in Order.objects.filter(Q(order_no__startswith='GB') | Q(order_no__startswith='PB')).all():
    order_no = m.order_no[2:]
    Order.objects.filter(id = m.id).update(order_no = order_no)
