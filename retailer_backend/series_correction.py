from retailer_to_sp.models import *
for m in Invoice.objects.filter(invoice_no__startswith='GB').all():
    m.invoice_no = m.invoice_no[1:]
    print(m.invoice_no)
    m.save()

for m in Order.objects.filter(order_no__startswith = 'GB').all():
    m.order_no = m.order_no[1:]
    print(m.invoice_no)
    m.save()
