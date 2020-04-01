from retailer_to_sp.models import *
from django.db.models import Q

def edit_series():
	for m in Invoice.objects.filter(Q(invoice_no__startswith='GD') | Q(invoice_no__startswith='PD')).all():
	    invoice_no = m.invoice_no[2:]
	    Invoice.objects.filter(id = m.id).update(invoice_no = invoice_no)

	for m in Order.objects.filter(Q(order_no__startswith='GD') | Q(order_no__startswith='PD')).all():
	    order_no = m.order_no[2:]
	    Order.objects.filter(id = m.id).update(order_no = order_no)

if __name__=='__main__':
	edit_series()