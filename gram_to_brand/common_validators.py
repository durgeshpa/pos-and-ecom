import logging

from django.contrib.auth import get_user_model

from products.models import Product
from shops.models import Shop
from wms.models import WarehouseAssortment

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


def validate_assortment_against_warehouse_and_product(warehouse_id, sku):
    """validation warehouse assortment for the selected warehouse and product"""
    product = Product.objects.filter(product_sku=sku).last()
    if not product:
        return {'error': 'please provide a valid sku.'}
    if not WarehouseAssortment.objects.filter(warehouse_id=warehouse_id, product=product.parent_product).exists():
        return {'error': 'please provide a valid warehouse_id.'}
    return {'data': WarehouseAssortment.objects.filter(warehouse_id=warehouse_id, product=product.parent_product).last()}


