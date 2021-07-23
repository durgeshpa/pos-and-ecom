

from django.db.models.query_utils import Q


def pos_shop_user_mapping_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(Q(shop__shop_name__icontains=search_text) | Q(
        user__first_name__icontains=search_text) | Q(user__phone_number__icontains=search_text))
    return queryset
