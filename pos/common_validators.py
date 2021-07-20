from shops.models import PosShopUserMapping

def validate_user_type_for_pos_shop(shop_id, user):
    """
    Fetch User type of the user for the Shop
    """
    qs = PosShopUserMapping.objects.filter(shop=shop_id, user=user, status=True)
    if not qs:
        return {'error': 'User not mapped with the Shop.'}
    user_type = qs.last().user_type
    if user_type == 'cashier':
        return {'error': 'Unauthorised user.'}
    else:
        return {'data': user_type}