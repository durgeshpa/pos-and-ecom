from django.db.models import Q


# search using shop_name & shop_type based on criteria that matches
def fetch_by_id(queryset, obj_id):
    queryset = queryset.filter(id=obj_id)
    return queryset


# search using shop_name & parent shop based on criteria that matches
def shop_search(queryset, search_text):
    queryset = queryset.filter(Q(shop_name__icontains=search_text) | Q(
        retiler_mapping__parent__shop_name__icontains=search_text))
    return queryset
