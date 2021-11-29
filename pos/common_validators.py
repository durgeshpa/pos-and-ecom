from shops.models import CASHIER, PosShopUserMapping
from .models import PosGRNOrder, Vendor


def validate_user_type_for_pos_shop(shop_id, user):
    """
    Fetch User type of the user for the Shop
    """
    qs = PosShopUserMapping.objects.filter(shop=shop_id, user=user, status=True)
    if not qs:
        return {'error': 'User not mapped with the Shop.'}
    user_type = qs.last().user_type
    if user_type == CASHIER:
        return {'error': 'Unauthorised user.'}
    else:
        return {'data': user_type}


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def compareList(lst1,lst2):
    lst1.sort()
    lst2.sort()
    return True if lst1 == lst2 else False


def get_validate_grn_order(grn_ordered_id, shop):
    """ validate id that belong to a PosGRNOrder model if not through error """
    try:
        grn_ordered_obj = PosGRNOrder.objects.get(id=grn_ordered_id, order__ordered_cart__retailer_shop=shop)
    except Exception as e:
        return {'error': "GRN Order doesn't exist"}
    return {'grn_ordered_id': grn_ordered_obj}


def get_validate_vendor(vendor_id, shop):
    """ validate id that belong to a Vendor model if not through error """
    try:
        vendor_obj = Vendor.objects.filter(id=vendor_id, retailer_shop=shop)
    except Exception as e:
        return {'error': "Vendor doesn't exist"}
    return {'vendor_id': vendor_obj}


def validate_id(queryset, s_id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=s_id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=s_id)}