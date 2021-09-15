# django imports
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from ...models import Discount, DiscountValue
from products.common_validators import validate_id
from .serializers import DiscountSerializer
from retailer_backend.utils import SmallOffsetPagination
from pos.common_functions import serializer_error


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True,
                      "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": []}

    return Response(result, status=status_code)


class DiscountView(APIView):
    """
    Get Coupon
    Post Coupon
    Put Coupon
    """
    permission_classes = (AllowAny,)
    serializer_class = DiscountSerializer
    queryset = Discount.objects.all()

    def get(self, request, format=None):
        """
        Get API for Discount
        """
        discount_total_count = self.queryset.count() 
        if request.GET.get('id'):
            """ Get Discount for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            discount_page = id_validation['data']
            discount_total_count = discount_page.count()
        else:
            """ GET Coupon List """
            discount_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(discount_page, many=True)
        msg = f"total count {discount_total_count}" if discount_total_count else "no coupon found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """
        POST API for Discount
        """
        discount_percentage = request.data.pop('discount_percentage')
        serializer = self.serializer_class(data = request.data, context = {'discount_percentage': discount_percentage})
        if serializer.is_valid():
            serializer.save()
            return get_response("Discount Created Successfully", serializer.data, True)
        return get_response(serializer_error(serializer))

    def patch(self, request):
        """
        Update Discount
        """
        try:
            discount = Discount.objects.get(id=request.data['id'])
        except ObjectDoesNotExist:
            return get_response("Provide a valid id")
        discount_percentage = None
        if 'discount_percentage' in request.data:
            discount_percentage = request.data.pop('discount_percentage')
        serializer = self.serializer_class(data=request.data, instance=discount, context={'discount_percentage':discount_percentage}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return get_response("Discount Updated Successfully", serializer.data, True)
        return get_response(serializer_error(serializer))