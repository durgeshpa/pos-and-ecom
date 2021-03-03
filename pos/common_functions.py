from rest_framework.response import Response
from rest_framework import status

from pos.models import RetailerProduct
from retailer_to_sp.models import CartProductMapping
from retailer_to_gram.models import (CartProductMapping as GramMappedCartProductMapping)


class RetailerProductCls(object):

    @classmethod
    def create_retailer_product(cls, shop_id, name, mrp, selling_price, linked_product_id, sku_type, description):
        RetailerProduct.objects.create(shop_id=shop_id, name=name, linked_product_id=linked_product_id,
                                       mrp=mrp, sku_type=sku_type, selling_price=selling_price, description=description)

    @classmethod
    def get_sku_type(cls, sku_type):
        """
            Get SKU_TYPE
        """
        if sku_type == 1:
            return 'CREATED'
        if sku_type == 2:
            return 'LINKED'
        if sku_type == 3:
            return 'LINKED_EDITED'


def get_response(msg, data=None):
    """
        General Response For API
    """
    if data:
        ret = {"is_success": True, "message": msg, "response_data": data}
    else:
        ret = {"is_success": False, "message": msg, "response_data": None}
    return Response(ret, status=status.HTTP_200_OK)


def delete_cart_mapping(cart, product, cart_type='retail'):
    """
        Delete Cart items
    """
    if cart_type == 'retail':
        if CartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
            CartProductMapping.objects.filter(cart=cart, cart_product=product).delete()
    elif cart_type == 'retail_gf':
        if GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).exists():
            GramMappedCartProductMapping.objects.filter(cart=cart, cart_product=product).delete()