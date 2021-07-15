from functools import wraps

from rest_framework.response import Response
from rest_framework import status

from shops.models import Shop


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
