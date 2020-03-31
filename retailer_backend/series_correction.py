from retailer_to_sp.models import *
for m in Invoice.objects.filter(Q(invoice_no__startswith='GB') | Q(invoice_no__startswith='PB')).all():
    m.invoice_no = m.invoice_no[2:]
    print(m.invoice_no)
    m.save()

for m in Order.objects.filter(Q(invoice_no__startswith='GB') | Q(invoice_no__startswith='PB')).all():
    m.order_no = m.order_no[2:]
    print(m.invoice_no)
    m.save()
