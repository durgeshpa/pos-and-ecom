from django.db.models import Q


# search using PO number, GRN invoice number and product name on criteria that matches
def grn_product_search(queryset, search_text):
    queryset = queryset.filter(Q(invoice_no__icontains=search_text) | Q(products__name__icontains=search_text)
                               | Q(order__ordered_cart__po_no__icontains=search_text))
    return queryset
