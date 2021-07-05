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
    queryset = queryset.only('pincode_link__id', 'pincode_link__pincode').distinct('pincode_link__id')
    return queryset

def get_distinct_cities(queryset):
    '''
    Fetch unique cities from the queryset
    '''
    queryset = queryset.only('city__id', 'city__city_name').distinct('city__id')
    return queryset

def get_distinct_states(queryset):
    '''
    Fetch unique states from the queryset
    '''
    queryset = queryset.only('state_id', 'state__state_name').distinct('state_id')
    return queryset
