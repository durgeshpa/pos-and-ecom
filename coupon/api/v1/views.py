# django imports
import logging
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Q

# apps imports
from .serializers import CouponSerializer, CouponCreateSerializer, CouponUpdateSerializer
from coupon.models import Coupon, CouponRuleSet
from products.common_validators import validate_id
from retailer_backend.utils import SmallOffsetPagination
from pos.common_functions import serializer_error

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


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


class CouponView(APIView):
    """
    Get Coupon
    Post Coupon
    Put Coupon
    """
    permission_classes = (AllowAny,)
    serializer_class = CouponSerializer
    queryset = Coupon.objects.exclude(shop__shop_type__shop_type='f').filter(
        Q(coupon_type='category') | Q(coupon_type='brand')).order_by('-id')

    def get(self, request, format=None):
        """
        Get API for Coupon
        """
        info_logger.info("Coupon api called.")
        coupon_total_count = self.queryset.count() 
        if request.GET.get('id'):
            """ Get Coupon for specific ID """
            id_validation = validate_id(
                self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            coupon_page = id_validation['data']
            coupon_total_count = coupon_page.count()
        else:
            """ GET Coupon List """
            coupon_page = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(coupon_page, many=True)
        msg = f"total count {coupon_total_count}" if coupon_total_count else "no coupon found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """
        POST API for Coupon
        """
        serializer = CouponCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            data.update(request.data)
            return self.create_coupon(data)
        return get_response(serializer_error(serializer))

    def patch(self, request):
        """
        Update Coupon
        """
        serializer = CouponUpdateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            data.update(request.data)
            return self.update_coupon(data)
        return get_response(serializer_error(serializer))
    
    def create_coupon(self, data):
        """
        create coupon
        """
        context = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'brand': data.get('brand', None),
            'category': data.get('category', None),
            'is_percentage': data['is_percentage'],
            'discount_value': data['discount_value'],
            'max_discount': data['max_discount'],
        }
        serializer = CouponSerializer(data=data, context=context)
        if serializer.is_valid():
            serializer.save()
            return get_response("Coupon Created Successfully", serializer.data, True)
        return get_response(serializer_error(serializer))

    def update_coupon(self, data):
        """
        Update Coupon
        """
        try:
            coupon = Coupon.objects.get(id=data['coupon_id'])
        except ObjectDoesNotExist:
            return get_response("Coupon Id Invalid")
        serializer = CouponSerializer(data = data, instance=coupon, context = {'data':data})
        if serializer.is_valid():
            serializer.save()
            return get_response("Coupon updated successfully", serializer.data, True)
        return get_response(serializer_error(serializer))
