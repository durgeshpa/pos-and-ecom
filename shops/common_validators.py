from django.contrib.auth import get_user_model
from shops.models import PosShopUserMapping, Shop, USER_TYPE_CHOICES


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def validate_psu_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    try:
        return {'data': queryset.get(id=id)}
    except:
        return {'error': 'please provide a valid id'}


def validate_data_format(request):
    """ Validate shop data  """
    try:
        data = request.data["data"]
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


def get_validate_user(user_id):
    try:
        user = get_user_model().objects.get(id=user_id)
    except Exception as e:
        return {'error': '{} user not found'.format(user_id)}
    return {'data': user}


def get_validate_shop(shop_id):
    try:
        shop = Shop.objects.get(id=shop_id)
    except Exception as e:
        return {'error': '{} shop not found'.format(shop_id)}
    return {'data': shop}


def get_validate_user_type(user_type):
    """validate shop user type"""
    if not (any(user_type in i for i in USER_TYPE_CHOICES)):
        return {'error': 'please provide a valid User Type'}
    return {'data': user_type}
