from django.db.models import Q

from gram_to_brand.models import GRNOrder
from retailer_to_sp.models import OrderedProduct
from whc.models import AutoOrderProcessing


def run():
    auto_processing_entries = AutoOrderProcessing.objects.filter(state=14).values('grn_id', 'grn__invoice_no', 'auto_po_id')

    source_dest_map = {}
    for entry in auto_processing_entries:
        print(entry)
        dest_grn_entry = GRNOrder.objects.filter(~Q(id=entry['grn_id']), invoice_no=entry['grn__invoice_no'],
                                                 order__ordered_cart_id=entry['auto_po_id'])
        if dest_grn_entry.count() > 1:
            print("Invoice No {} - Multipe entries found ".format(entry['grn__invoice_no']))
            continue

        if dest_grn_entry.count() == 0:
            print("Invoice No {} - No entry found ".format(entry['grn__invoice_no']))
            continue

        source_dest_map[entry['grn_id']] = dest_grn_entry.last().id
    print(source_dest_map)
    #
    # for source, dest in source_dest_map.items():
    #     AutoOrderProcessing.objects.filter(grn_id=source).update(auto_grn_id=dest)


    auto_processing_entries = AutoOrderProcessing.objects.filter(state=14)
    for entry in auto_processing_entries:
        if entry.auto_grn:
            entry.auto_grn.invoice_no = OrderedProduct.objects.filter(order=entry.order).last().invoice.invoice_no
            entry.auto_grn.save()