from django.db.models import Q


def fetch_by_id(queryset, obj_id):
    '''
    Fetch data from queryset by filtering pk
    '''
    queryset = queryset.filter(id=obj_id)
    return queryset


def shop_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(Q(shop_name__icontains=search_text) |
                               Q(retiler_mapping__parent__shop_name__icontains=search_text))
    return queryset


def shop_list_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(shop_name__icontains=search_text)
    return queryset


def parent_shop_search(queryset, search_string):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    sts_list = search_string.split(' ')
    for search_text in sts_list:
        queryset = queryset.filter(Q(parent__shop_name__icontains=search_text) | Q(
            parent__shop_owner__phone_number__icontains=search_text))
    return queryset


def related_user_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(Q(first_name__icontains=search_text) | Q(phone_number__icontains=search_text))
    return queryset


def get_distinct_pin_codes(queryset):
    '''
    Fetch unique pincodes from the queryset
    '''
    queryset = queryset.only(
        'pincode_link__id', 'pincode_link__pincode').distinct('pincode_link__id')
    return queryset


def get_distinct_cities(queryset):
    '''
    Fetch unique cities from the queryset
    '''
    queryset = queryset.only(
        'city__id', 'city__city_name').distinct('city__id')
    return queryset


def get_distinct_states(queryset):
    '''
    Fetch unique states from the queryset
    '''
    queryset = queryset.only(
        'state_id', 'state__state_name').distinct('state_id')
    return queryset


def shop_user_mapping_search(queryset, search_text):
    '''
    search using shop name, employee group, employee's phone number based on criteria that matches
    '''
    queryset = queryset.filter(Q(shop__shop_name__icontains=search_text) |
                               Q(employee_group__permissions__codename__icontains=search_text) |
                               Q(employee__phone_number__icontains=search_text))
    return queryset


# search using user name & phone number based on criteria that matches
def shop_manager_search(queryset, search_string):
    sts_list = search_string.split(' ')
    for search_text in sts_list:
        queryset = queryset.filter(
            Q(employee__phone_number__icontains=search_text) | Q(employee__first_name__icontains=search_text)
            | Q(employee__last_name__icontains=search_text))
    return queryset


# search using user name & phone number based on criteria that matches
def shop_employee_search(queryset, search_string):
    sts_list = search_string.split(' ')
    for search_text in sts_list:
        queryset = queryset.filter(Q(phone_number__icontains=search_text) | Q(first_name__icontains=search_text)
                                   | Q(last_name__icontains=search_text))
    return queryset


# search using user name & phone number based on criteria that matches
def shop_owner_search(queryset, search_string):
    sts_list = search_string.split(' ')
    for search_text in sts_list:
        queryset = queryset.filter(
            Q(shop_owner__phone_number__icontains=search_text) | Q(shop_owner__first_name__icontains=search_text)
            | Q(shop_owner__last_name__icontains=search_text))
    return queryset


def retailer_type_search(queryset, search_text):
    queryset = queryset.filter(retailer_type_name__icontains=search_text)
    return queryset


def shop_type_search(queryset, search_text):
    queryset = queryset.filter(Q(shop_type__icontains=search_text) |
                               Q(shop_min_amount__icontains=search_text) |
                               Q(shop_sub_type__retailer_type_name__icontains=search_text))
    return queryset


def search_state(queryset, search_text):
    queryset = queryset.filter(state_name__icontains=search_text)
    return queryset


def search_pincode(queryset, search_text):
    queryset = queryset.filter(pincode__icontains=search_text)
    return queryset


def search_city(queryset, search_text):
    queryset = queryset.filter(city_name__icontains=search_text)
    return queryset


def search_beat_planning_data(queryset, search_text):
    '''
    search using shop name, employee group, employee's phone number based on criteria that matches
    '''
    queryset = queryset.filter(Q(manager__phone_number__icontains=search_text) |
                               Q(executive__phone_number__icontains=search_text) |
                               Q(manager__first_name__icontains=search_text) |
                               Q(executive__first_name__icontains=search_text))


from django.db.models.query_utils import Q


def pos_shop_user_mapping_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(Q(shop__shop_name__icontains=search_text) | Q(
        user__first_name__icontains=search_text) | Q(user__phone_number__icontains=search_text))
    return queryset


def shop_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(Q(shop_name__icontains=search_text) | Q(
        retiler_mapping__parent__shop_name__icontains=search_text))
    return queryset
