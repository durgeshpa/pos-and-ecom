from django.db.models import Q


# search using category_name, category_sku_part & sub_category_name based on criteria that matches
def category_search(queryset, search_text):
    queryset = queryset.filter(Q(category_name__icontains=search_text) |
                               Q(cat_parent__category_name__icontains=search_text) |
                               Q(category_sku_part__icontains=search_text))
    return queryset
