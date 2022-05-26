from functools import wraps

from rest_framework.response import Response
from rest_framework import status

from shops.models import Shop


def api_response(msg, data=None, status_code=status.HTTP_406_NOT_ACCEPTABLE, success=False, extra_params=None):
    ret = {"is_success": success, "message": msg, "response_data": data}
    if extra_params:
        ret.update(extra_params)
    return Response(ret, status=status_code)

from rest_framework import status
from rest_framework.response import Response


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True, "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": []}

    return Response(result, status=status_code)

def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]


def check_shop(view_func):
    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        try:
            shop = Shop.objects.get(id=request.META.get('HTTP_SHOP_ID', None), status=True, approval_status=2)
            parent_shop = shop.get_shop_parent
        except:
            shop = None
            parent_shop = None
        kwargs['shop'] = shop
        kwargs['parent_shop'] = parent_shop
        kwargs['app_type'] = request.META.get('HTTP_APP_TYPE', None)
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func
