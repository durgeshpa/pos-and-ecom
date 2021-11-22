from retailer_to_sp.models import *
from django.db.models import Q

def edit_series():
	for m in Invoice.objects.filter(Q(invoice_no__startswith='GB') | Q(invoice_no__startswith='PB')).all():
	    invoice_no = m.invoice_no[1:]
	    Invoice.objects.filter(id = m.id).update(invoice_no = invoice_no)

	for m in Order.objects.filter(Q(order_no__startswith='GB') | Q(order_no__startswith='PB')).all():
	    order_no = m.order_no[1:]
	    Order.objects.filter(id = m.id).update(order_no = order_no)

	for m in Cart.objects.filter(Q(order_id__startswith='GB') | Q(order_id__startswith='PB')).all():
	    order_id = m.order_id[1:]
	    Cart.objects.filter(id = m.id).update(order_id = order_id)

if __name__=='__main__':
	edit_series()
