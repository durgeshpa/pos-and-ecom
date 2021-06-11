from django.db.models import query
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from django.shortcuts import get_object_or_404
from rest_framework import status
from .serializers import CardDataSerializer, CardSerializer, ApplicationSerializer, ApplicationDataSerializer
from ...choices import CARD_TYPE_CHOICES
from ...models import Application, Card

from .pagination import PaginationHandlerMixin
from rest_framework.pagination import LimitOffsetPagination

class BasicPagination(LimitOffsetPagination):
    limit_query_param = "limit"
    offset_query_param = "offset"
    max_limit = 20
    default_limit = 10


class CardView(APIView, PaginationHandlerMixin):
    """CardView to get and post cards"""

    pagination_class = BasicPagination
    serializer_class = CardSerializer

    def get(self, request, format=None):
        """Get all cards"""

        query_params = request.query_params

        queryset = Card.objects.all()

        if query_params.get('id'):
            card_id = query_params.get('id')
            queryset = queryset.filter(id=card_id)
            if len(queryset) == 0:
                raise NotFound(f"card with id {card_id} not found")

        if query_params.get('app_id'):
            try:
                app_id = query_params.get('app_id')
                app = get_object_or_404(Application, id=app_id)
                queryset = queryset.filter(app=app)
            except:
                raise NotFound(f"app with app_id {app_id} not found")
        
        if query_params.get('card_type'):
            card_type = query_params.get('card_type')
            if card_type not in [ x[0] for x in CARD_TYPE_CHOICES] :
                raise ValidationError(f"card_type not valid. card_type must be one of {[ x[0] for x in CARD_TYPE_CHOICES]}")
            else:
                queryset = queryset.filter(type=card_type)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            cards = self.get_paginated_response(self.serializer_class(page,
                                                    many=True).data)
        else:
            cards = self.serializer_class(queryset, many=True)

        message = {
            "is_success": "true",
            "message": "OK",
            "cards": cards.data
        }
        return Response(message)

    def post(self, request):
        """Create a new card"""

        data = request.data
        card_data = data.pop("card_data")
        serializer = CardDataSerializer(data=card_data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            message = {
                "is_success": "true",
                "message": "OK",
                "card_data": serializer.data
            }
            return Response(message, status=status.HTTP_201_CREATED)

        else:
            message = {
                "is_success": "false",
                "message": "please check the fields",
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)


class CardDetailView(RetrieveAPIView):
    """Get card by id"""
    lookup_field = "id"
    queryset = Card.objects.all()
    serializer_class = CardSerializer


class ApplicationView(ListAPIView, CreateAPIView):
    """Application view for get and post"""

    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer


class ApplicationDetailView(RetrieveAPIView):
    """Get application details by id"""

    lookup_field = 'id'
    queryset = Application.objects.all()
    serializer_class = ApplicationDataSerializer
