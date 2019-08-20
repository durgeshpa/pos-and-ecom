from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from rest_framework.pagination import LimitOffsetPagination

from products.models import Product

class SmallOffsetPagination(LimitOffsetPagination):
    """
    Custom LimitOffset
    """
    default_limit = 10
    max_limit = 50