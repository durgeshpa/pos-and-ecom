import logging
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from shops.models import Shop
from products.models import ParentProduct
from wms.models import Zone, WarehouseAssortment
logger = logging.getLogger(__name__)

User = get_user_model()


def validate_data_format(request):
    """ Validate shop data  """
    try:
        # data = json.loads(request.data["data"])
        data = request.data["data"]
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


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



