from django.db.models import Q
from functools import wraps
from wms.common_functions import get_response

def zone_search(queryset, search_text):
    '''
    search using shop_name & parent shop based on criteria that matches
    '''
    queryset = queryset.filter(Q(warehouse__shop_name__icontains=search_text) | Q(
        supervisor__first_name__icontains=search_text) | Q(coordinator__first_name__icontains=search_text))
    return queryset


# search using user name & phone number based on criteria that matches
def user_search(queryset, search_string):
    sts_list = search_string.split(' ')
    for search_text in sts_list:
        queryset = queryset.filter(Q(phone_number__icontains=search_text) | Q(first_name__icontains=search_text)
                                   | Q(last_name__icontains=search_text))
    return queryset


def check_warehouse_manager(view_func):
    """
        Decorator to validate warehouse manager request
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if not user.has_perm('wms.can_have_zone_warehouse_permission'):
            return get_response("Logged In user does not have required permission to perform this action.")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func