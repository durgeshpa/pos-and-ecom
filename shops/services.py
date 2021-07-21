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
    queryset = queryset.filter(Q(shop_name__icontains=search_text) | Q(
        retiler_mapping__parent__shop_name__icontains=search_text))
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
def shop_manager_search(queryset, search_text):
    queryset = queryset.filter(
        Q(employee__phone_number__icontains=search_text) | Q(employee__first_name__icontains=search_text)
        | Q(employee__last_name__icontains=search_text))
    return queryset


# search using user name & phone number based on criteria that matches
def shop_employee_search(queryset, search_text):
    queryset = queryset.filter(Q(phone_number__icontains=search_text) | Q(first_name__icontains=search_text)
                               | Q(last_name__icontains=search_text))
    return queryset


def retailer_type_search(queryset, search_text):
    queryset = queryset.filter(retailer_type_name__icontains=search_text)
    return queryset


def shop_type_search(queryset, search_text):
    queryset = queryset.filter(Q(shop_type__icontains=search_text) |
                               Q(shop_min_amount__icontains=search_text))
    return queryset