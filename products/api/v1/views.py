from rest_framework.response import Response
from rest_framework import status, authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser

from .serializers import ParentProductSerializers
from products.utils import MultipartJsonParser


class ParentProductView(GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parser_classes = [MultipartJsonParser, JSONParser]

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request):

        """
           POST API for Product Creation
        """

        serializer = ParentProductSerializers(data=request.data,)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



