from functools import wraps

from rest_framework.response import Response
from rest_framework import status

from shops.models import Shop
from wms.models import PosInventory, PosInventoryState

from .models import Address


def api_response(msg, data=None, status_code=status.HTTP_406_NOT_ACCEPTABLE, success=False, extra_params=None):
    ret = {"is_success": success, "message": msg, "response_data": data}
    if extra_params:
        ret.update(extra_params)
    return Response(ret, status=status_code)


def check_ecom_user(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        if not request.user.is_ecom_user:
            return api_response("User Not Registered For E-commerce!")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def check_ecom_user_shop(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        if not request.user.is_ecom_user:
            return api_response("User Not Registered For E-commerce!")
        try:
            shop = Shop.objects.get(id=request.META.get('HTTP_SHOP_ID', None), shop_type__shop_type='f', status=True,
                                    approval_status=2, pos_enabled=1)
        except:
            return api_response("Shop not available!")
        kwargs['shop'] = shop
        kwargs['app_type'] = request.META.get('HTTP_APP_TYPE', None)
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func


def nearby_shops(lat, lng, radius=10, limit=1):
    """
    Returns shop(s) within radius from lat,lng point
    lat: latitude
    lng: longitude
    radius: distance in km from latitude,longitude point
    """

    query = """SELECT * from (
               SELECT shops_shop.id, (6367*acos(cos(radians(%2f))
               *cos(radians(latitude))*cos(radians(longitude)-radians(%2f))
               +sin(radians(%2f))*sin(radians(latitude))))
               AS distance FROM shops_shop 
               left join shops_shoptype on shops_shoptype.id=shops_shop.shop_type_id
               where shops_shoptype.shop_type='f' and shops_shop.status=True and shops_shop.approval_status=2
               and shops_shop.pos_enabled=True) as shop_loc
               where distance < %2f ORDER BY distance LIMIT %d OFFSET 0""" % (float(lat), float(lng), float(lat),
                                                                              radius, limit)

    queryset = Shop.objects.raw(query)
    return queryset[0] if queryset else None


def validate_address_id(func):
    @wraps(func)
    def _wrapped_view_func(self, request, pk):
        user_address = Address.objects.filter(user=request.user, id=pk).last()
        if not user_address:
            return api_response("Invalid Address Id")
        return func(self, request, pk)

    return _wrapped_view_func


def get_categories_with_products(shop):
    query_set = PosInventory.objects.filter(product__shop=shop, product__status='active', quantity__gt=0,
                                            inventory_state=PosInventoryState.objects.filter(
                                                inventory_state='available').last())
    return query_set.values_list(
        'product__linked_product__parent_product__parent_product_pro_category__category', flat=True).distinct()