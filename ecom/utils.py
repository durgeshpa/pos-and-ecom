from functools import wraps

from rest_framework.response import Response
from rest_framework import status


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
