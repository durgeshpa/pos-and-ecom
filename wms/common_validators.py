import logging
import json
from django.contrib.auth import get_user_model
from shops.models import Shop
logger = logging.getLogger(__name__)

User = get_user_model()


def validate_ledger_request(request):
    sku = request.GET.get('sku')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not sku:
        return {"error": "please select sku"}

    if not start_date:
        return {"error": "please select start_date"}

    if not end_date:
        return {"error": "please select end_date"}
    return {"data": {"sku": sku, "start_date": start_date, "end_date": end_date}}


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def validate_id_and_warehouse(queryset, id, warehouse):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id, warehouse=warehouse).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id, warehouse=warehouse)}


def validate_warehouse(id):
    """ validation only ids that belong to a selected related model """
    if not Shop.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': Shop.filter(id=id).last()}


def validate_data_format(request):
    """ Validate shop data  """
    try:
        # data = json.loads(request.data["data"])
        data = request.data["data"]
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


def get_validate_putaway_users(putaway_users):
    """
    validate ids that belong to a User model also
    checking putaway_user shouldn't repeat else through error
    """
    putaway_users_list = []
    putaway_users_obj = []
    for putaway_users_data in putaway_users:
        try:
            putaway_user = get_user_model().objects.get(
                id=int(putaway_users_data['id']))
            if not putaway_user.groups.filter(name='Putaway').exists():
                return {'error': '{} putaway_user does not have required permission.'.format(putaway_users_data['id'])}
        except Exception as e:
            logger.error(e)
            return {'error': '{} putaway_user not found'.format(putaway_users_data['id'])}
        putaway_users_obj.append(putaway_user)
        if putaway_user in putaway_users_list:
            return {'error': '{} do not repeat same putaway_user for one Zone'.format(putaway_user)}
        putaway_users_list.append(putaway_user)
    return {'putaway_users': putaway_users_obj}
