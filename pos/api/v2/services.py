from django.db.models import Q, Sum, F
# search using user name & phone number based on criteria that matches
"""
@Durgesh patel
"""
def shop_owner_search(queryset, search_string):
    sts_list = search_string.split(' ')
    for search_text in sts_list:
        queryset = queryset.filter(
            Q(shop_owner__phone_number__icontains=search_text) | Q(shop_owner__first_name__icontains=search_text)
            | Q(shop_owner__last_name__icontains=search_text))
    return queryset

# search shop by the the shop name
def shop_name_search(queryset, search_string):
    sts_list = search_string.split(' ')
    for search_text in sts_list:
        queryset = queryset.filter(Q(shop_name__icontains=search_text))
    return queryset

# serach fofo and foco type
def shop_type_search(queryset, search_text):
    queryset = queryset.filter(Q(shop_type__icontains=search_text) |
                               Q(shop_min_amount__icontains=search_text) |
                               Q(shop_sub_type__retailer_type_name__icontains=search_text))
    return queryset

def shop_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(Q(shop__shop_name__icontains=search_text) |
                               Q(shop__retiler_mapping__parent__shop_name__icontains=search_text))
    return queryset

def shop_reward_config_key_search(queryset, search_text):
    """shop_reward_config_key_search"""
    queryset = queryset.filter(Q(key__icontains=search_text))
    return  queryset