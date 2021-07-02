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

def get_distinct_pin_codes(queryset):
    queryset = queryset.only('pincode_link__id', 'pincode_link__pincode').distinct('pincode_link__id')
    return queryset

def get_distinct_cities(queryset):
    queryset = queryset.only('city__id', 'city__city_name').distinct('city__id')
    return queryset

def get_distinct_states(queryset):
    queryset = queryset.only('state_id', 'state__state_name').distinct('state_id')
    print(queryset)
    return queryset
