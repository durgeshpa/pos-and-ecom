import logging
from rest_framework import authentication

from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from accounts.models import User
from .serializers import UserProfileSerializers
from products.common_function import get_response

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class UserProfileView(GenericAPIView):
    """
        Get Brand List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = UserProfileSerializers

    def get(self, request):
        try:
            user_id = User.objects.get(id=request.user.id)
        except:
            return Response({"error": "Token is not valid."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.serializer_class(user_id)
        return get_response("", serializer.data)
