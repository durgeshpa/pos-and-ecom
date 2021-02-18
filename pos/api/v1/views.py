from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions, authentication
from django.core.exceptions import ObjectDoesNotExist

from .serializers import ProductDetailSerializer
from products.models import Product

class ProductDetail(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    """
        API to get information of existing gramfactory product for POS product creation
    """
    def get(self, *args, **kwargs):
        pk = self.kwargs.get('pk')
        msg = {'is_success': False, 'message':'', 'response_data': None}
        try:
            product = Product.objects.get(id=pk)
        except ObjectDoesNotExist:
            msg['message'] = 'Invalid Product ID'
            return Response(msg, status=status.HTTP_200_OK)

        product_detail_serializer = ProductDetailSerializer(product)
        return Response({"message": 'Success', "response_data": product_detail_serializer.data, "is_success": True})