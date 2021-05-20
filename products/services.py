from django.db.models import Q


# search using parent_id, name & category_name based on criteria that matches
def parent_product_search(queryset, search_text):
    queryset = queryset.filter(Q(name__icontains=search_text) | Q(parent_id__icontains=search_text)
                               | Q(parent_product_pro_category__category__category_name__icontains=search_text))
    return queryset
