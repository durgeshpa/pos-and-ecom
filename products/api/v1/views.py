from rest_framework.response import Response
from rest_framework import status, authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser

from products.models import  ParentProduct
from .serializers import ParentProductSerializers
from products.utils import MultipartJsonParser
from retailer_backend.utils import SmallOffsetPagination


class ParentProductView(GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parser_classes = [MultipartJsonParser, JSONParser]
    parent_product_list = ParentProduct.objects.all()

    def get(self, request):
        """ GET API to get Parent Product List """
        if request.GET.get('parent_product_id'):
            """
               Get Parent Product when product_id is given in params
            """
            id = request.GET.get('parent_product_id')
            parent_pro_id = self.parent_product_list.filter(id=id).last()
            if parent_pro_id is None:
                msg = {'is_success': False,
                       'message': ['Please Provide a Valid parent_product_id'],
                       'data': None}
                return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

            self.parent_product_list = self.parent_product_list.filter(id=id)
        parent_product = SmallOffsetPagination().paginate_queryset(self.parent_product_list, request)
        serializer = ParentProductSerializers(parent_product, many=True)
        return Response(serializer.data)

    def post(self, request):

        """
           POST API for Parent Product Creation with Image Category & Tax
        """

        serializer = ParentProductSerializers(data=request.data,)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



