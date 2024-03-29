from django.db.models import Q
from functools import wraps
from wms.common_functions import get_response

def zone_search(queryset, search_text):
    '''
    search using warehouse shop_name & supervisor name & coordinator name based on criteria that matches
    '''
    queryset = queryset.filter(Q(warehouse__shop_name__icontains=search_text) | Q(
        supervisor__first_name__icontains=search_text) | Q(coordinator__first_name__icontains=search_text))
    return queryset


def zone_assignments_search(queryset, search_text):
    """
    search using warehouse shop_name & supervisor name & coordinator name & user name based on criteria that matches
    """
    queryset = queryset.filter(Q(zone__warehouse__shop_name__icontains=search_text) | Q(
        zone__supervisor__first_name__icontains=search_text) | Q(zone__coordinator__first_name__icontains=search_text)
                               | Q(user__first_name__icontains=search_text))
    return queryset


def putaway_search(queryset, search_text):
    '''
    search using warehouse shop_name & product name & supervisor name & coordinator name based on criteria that matches
    '''
    queryset = queryset.filter(Q(warehouse__shop_name__icontains=search_text) | Q(sku__name__icontains=search_text) |
                               Q(putaway_user__first_name__icontains=search_text) |
                               Q(putaway_user__phone_number__icontains=search_text))
    return queryset


def pickup_search(queryset, search_text):
    '''
    search using order no & repackaging no based on criteria that matches
    '''
    queryset = queryset.filter(Q(order__order_no__icontains=search_text) |
                               Q(repackaging__repackaging_no__icontains=search_text))
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


def check_qc_executive(view_func):
    """
        Decorator to validate QC Executive request
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if not user.has_perm('wms.can_have_qc_executive_permission'):
            return get_response("Logged In user does not have required permission to perform this action.")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func



def check_qc_dispatch_executive(view_func):
    """
        Decorator to validate QC Executive request
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.has_perm('wms.can_have_qc_executive_permission') \
                or user.groups.filter(name='Dispatch Executive'):
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")

    return _wrapped_view_func


def check_whc_manager_coordinator_supervisor(view_func):
    """
        Decorator to validate request from warehouse manager / Coordinator / Supervisor
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.has_perm('wms.can_have_zone_warehouse_permission') or \
                user.has_perm('wms.can_have_zone_supervisor_permission') or \
                user.has_perm('wms.can_have_zone_coordinator_permission'):
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")

    return _wrapped_view_func


def check_putaway_user(view_func):
    """
        Decorator to validate putaway user request
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if not user.groups.filter(name='Putaway').exists():
            return get_response("Logged In user does not have required permission to perform this action.")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def check_picker_user(view_func):
    """
        Decorator to validate picker user request
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if not user.groups.filter(name='Picker Boy').exists():
            return get_response("Logged In user does not have required permission to perform this action.")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def whc_assortment_search(queryset, search_text):
    '''
    search using warehouse shop_name & parent product name & Zone mappings based on criteria that matches
    '''
    queryset = queryset.filter(Q(warehouse__shop_name__icontains=search_text) | Q(
        product__name__icontains=search_text) | Q(zone__supervisor__first_name__icontains=search_text) |
                               Q(zone__coordinator__first_name__icontains=search_text))
    return queryset


def qc_desk_search(queryset, search_text):
    '''
    search using warehouse's shop_name & desk_number & name & qc_executive based on criteria that matches
    '''
    queryset = queryset.filter(Q(warehouse__shop_name__icontains=search_text) | Q(desk_number__icontains=search_text) |
                               Q(name__icontains=search_text) | Q(qc_executive__first_name__icontains=search_text) |
                               Q(qc_executive__phone_number__icontains=search_text))
    return queryset


def qc_area_search(queryset, search_text):
    '''
    search using warehouse's shop_name & area_id & area_barcode_txt based on criteria that matches
    '''
    queryset = queryset.filter(Q(warehouse__shop_name__icontains=search_text) | Q(area_id__icontains=search_text) |
                               Q(area_barcode_txt__icontains=search_text))
    return queryset


def bin_search(queryset, search_text):
    '''
    search using warehouse shop_name & bin id & Zone mappings based on criteria that matches
    '''
    queryset = queryset.filter(Q(warehouse__shop_name__icontains=search_text) | Q(
        bin_id__icontains=search_text) | Q(zone__supervisor__first_name__icontains=search_text) |
                               Q(zone__coordinator__first_name__icontains=search_text))
    return queryset

def check_whc_manager_coordinator_supervisor_putaway(view_func):
    """
    Decorator to validate request from warehouse manager / Coordinator / Supervisor
    """
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.has_perm('wms.can_have_zone_warehouse_permission') or \
                user.has_perm('wms.can_have_zone_supervisor_permission') or \
                user.has_perm('wms.can_have_zone_coordinator_permission') or \
                user.groups.filter(name='Putaway').exists():
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")
    return _wrapped_view_func

def check_whc_manager_coordinator_supervisor_picker(view_func):
    """
    Decorator to validate request from warehouse manager / Coordinator / Supervisor
    """
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.has_perm('wms.can_have_zone_warehouse_permission') or \
                user.has_perm('wms.can_have_zone_supervisor_permission') or \
                user.has_perm('wms.can_have_zone_coordinator_permission') or \
                user.groups.filter(name='Picker Boy').exists():
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")
    return _wrapped_view_func


def check_whc_manager_coordinator_supervisor_qc_executive(view_func):
    """
    Decorator to validate request from warehouse manager / Coordinator / Supervisor / QC Executive
    """
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.has_perm('wms.can_have_zone_warehouse_permission') or \
                user.has_perm('wms.can_have_zone_supervisor_permission') or \
                user.has_perm('wms.can_have_zone_coordinator_permission') or \
                user.has_perm('wms.can_have_qc_executive_permission'):
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")
    return _wrapped_view_func


def check_picker(view_func):
    """
        Decorator to validate putaway user request
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if not user.groups.filter(name='Picker Boy').exists():
            return get_response("Logged In user does not have required permission to perform this action.")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def shipment_search(queryset, search_text):
    '''
    search using order no or invoice no
    '''
    queryset = queryset.filter(Q(invoice__invoice_no__icontains=search_text) | Q(order__order_no__icontains=search_text))
    return queryset


def check_whc_manager_qc_executive(view_func):
    """
    Decorator to validate request from warehouse manager / Coordinator / Supervisor / QC Executive
    """
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.has_perm('wms.can_have_zone_warehouse_permission') or \
                user.has_perm('wms.can_have_qc_executive_permission'):
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")
    return _wrapped_view_func


def check_whc_manager_dispatch_executive(view_func):
    """
    Decorator to validate request from warehouse manager / Dispatch Executive
    """
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.has_perm('wms.can_have_zone_warehouse_permission') \
            or user.groups.filter(name='Dispatch Executive'):
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")
    return _wrapped_view_func


def check_dispatch_executive(view_func):
    """
    Decorator to validate request from warehouse manager / Coordinator / Supervisor / QC Executive
    """
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if user.groups.filter(name='Dispatch Executive'):
            return view_func(self, request, *args, **kwargs)
        return get_response("Logged In user does not have required permission to perform this action.")
    return _wrapped_view_func
