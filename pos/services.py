from django.db.models import Q


# search using PO number, GRN invoice number and product name on criteria that matches
def grn_product_search(queryset, search_text):
    queryset = queryset.filter(Q(invoice_no__icontains=search_text) | Q(products__name__icontains=search_text)
                               | Q(order__ordered_cart__po_no__icontains=search_text))
    return queryset.distinct()


# search using pos return pr number, debit note number & grn_ordered_id
def grn_return_search(queryset, search_text):
    queryset = queryset.filter(Q(pr_number__icontains=search_text) | Q(debit_note_number__icontains=search_text)
                               | Q(grn_ordered_id__order__ordered_cart__po_no__icontains=search_text)
                               | Q(grn_ordered_id__grn_id__icontains=search_text)
                               )
    return queryset
