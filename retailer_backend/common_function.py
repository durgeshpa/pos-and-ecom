
from django.core.exceptions import ObjectDoesNotExist
from shops.models import Shop,ParentRetailerMapping
from rest_framework import status

from rest_framework.response import Response
# get shop
def checkShop(shop_id):
    try:
        shop = Shop.objects.get(id=shop_id,status=True)
        return True
    except ObjectDoesNotExist:
        return False

def checkShopMapping(shop_id):
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
        return True
    except ObjectDoesNotExist:
        return False

def checkNotShopAndMapping(shop_id):
    if checkShop(shop_id) and checkShopMapping(shop_id):
        return False
    else:
        return True


def getShop(shop_id):
    try:
        shop = Shop.objects.get(id=shop_id,status=True)
        return shop
    except ObjectDoesNotExist:
        return None

def getShopMapping(shop_id):
    try:
        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id)
        return parent_mapping
    except ObjectDoesNotExist:
        return None

def getShopMappingType(shop_id):
    pass

