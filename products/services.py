from django.db.models import Q


# search using parent_id, name & category_name based on criteria that matches
def parent_product_search(queryset, search_text):
    queryset = queryset.filter(Q(name__icontains=search_text) | Q(parent_id__icontains=search_text)
                               | Q(product_parent_product__product_name__icontains=search_text)
                               | Q(product_parent_product__product_sku__icontains=search_text)
                               )
    return queryset


# search using product_name & product_sku based on criteria that matches
def child_product_search(queryset, search_text):
    queryset = queryset.filter(Q(product_name__icontains=search_text) | Q(product_sku__icontains=search_text))
    return queryset


# search using product_hsn_code based on criteria that matches
def product_hsn_search(queryset, search_text):
    queryset = queryset.filter(product_hsn_code__icontains=search_text)
    return queryset


# search using tax_name & tax_type based on criteria that matches
def tax_search(queryset, search_text):
    queryset = queryset.filter(Q(tax_name__icontains=search_text) | Q(tax_type__icontains=search_text))
    return queryset


# search using category_name
def category_search(queryset, search_text):
    queryset = queryset.filter(Q(category_name__icontains=search_text))
    return queryset


# search using brand name
def brand_search(queryset, search_text):
    queryset = queryset.filter(Q(brand_name__icontains=search_text))
    return queryset


# search using name
def parent_product__name_search(queryset, search_text):
    queryset = queryset.filter(Q(name__icontains=search_text))

    return queryset