from rest_framework import status
from rest_framework.response import Response
from products.models import ParentProduct as ParentProducts, ProductHSN, ProductCapping as ProductCappings


def validate_id(queryset, id):
    if not queryset.filter(id=id).exists():
        return {'error': 'Please Provide a Valid id'}
    return {'data': queryset.filter(id=id)}


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
            result = {"is_success": False, "message": msg, "response_data": None}

    return Response(result, status=status_code)

