from django.db.models import Q

from gram_to_brand.models import GRNOrder
from retailer_backend.common_function import generate_invoice_number
from retailer_to_sp.models import OrderedProduct
from whc.models import AutoOrderProcessing


def run():

    # auto_processing_entries = AutoOrderProcessing.objects.filter(state=14).values('grn_id', 'grn__invoice_no', 'auto_po_id')
    #
    # source_dest_map = {}
    # for entry in auto_processing_entries:
    #     print(entry)
    #     dest_grn_entry = GRNOrder.objects.filter(~Q(id=entry['grn_id']), invoice_no=entry['grn__invoice_no'],
    #                                              order__ordered_cart_id=entry['auto_po_id'])
    #     if dest_grn_entry.count() > 1:
    #         print("Invoice No {} - Multipe entries found ".format(entry['grn__invoice_no']))
    #         continue
    #
    #     if dest_grn_entry.count() == 0:
    #         print("Invoice No {} - No entry found ".format(entry['grn__invoice_no']))
    #         continue
    #
    #     source_dest_map[entry['grn_id']] = dest_grn_entry.last().id
    # print(source_dest_map)
    #
    # for source, dest in source_dest_map.items():
    #     AutoOrderProcessing.objects.filter(grn_id=source).update(auto_grn_id=dest)
    #
    # print("Auto GRN Updated")
    #
    # auto_processing_entries = AutoOrderProcessing.objects.filter(state=14)
    # for entry in auto_processing_entries:
    #     if entry.auto_grn:
    #         entry.auto_grn.invoice_no = OrderedProduct.objects.filter(order=entry.order).last().invoice.invoice_no
    #         entry.auto_grn.save()

    # print("Invoice No Updated")
    populate_invoice_no()

def populate_invoice_no():
    auto_processing_entries = AutoOrderProcessing.objects.filter(created_at__gt='2022-01-17',
                                                                 auto_grn__invoice_no='-',
                                                                 order__rt_order_order_product__invoice__isnull=True)
    for entry in auto_processing_entries:
        generate_invoice_number(
            'invoice_no', entry.order.rt_order_order_product.last().pk,
            entry.order.seller_shop.shop_name_address_mapping.filter(address_type='billing').last().pk,
            entry.order.rt_order_order_product.last().invoice_amount)
        entry.auto_grn.invoice_no = entry.order.rt_order_order_product.last().invoice.invoice_no
        entry.auto_grn.save()
    print(auto_processing_entries.count())