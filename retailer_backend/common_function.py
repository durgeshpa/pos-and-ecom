
from django.core.exceptions import ObjectDoesNotExist
from shops.models import Shop,ParentRetailerMapping
from rest_framework import status

from rest_framework.response import Response
# get shop
def getShop(shop_id):
    try:
        Shop.objects.get(id=shop_id)
        return True
    except ObjectDoesNotExist:
        return False

def getShopMapping(shop_id):
    # get parent mapping
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
    except ObjectDoesNotExist:
        msg = {'is_success': False, 'message': ['Shop Mapping Not Found'], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)
