import logging
from django.core.checks import messages
from django.db.models import query
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, serializers
from django.shortcuts import get_object_or_404
from rest_framework import status
from .serializers import CardDataSerializer, CardSerializer, ApplicationSerializer, ApplicationDataSerializer, PageSerializer, PageDetailSerializer
from ...choices import CARD_TYPE_CHOICES
from ...models import Application, Card, Page, PageVersion

from .pagination import PaginationHandlerMixin
from rest_framework.pagination import LimitOffsetPagination



info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')

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
            "data": cards.data
        }
        return Response(message)

    def post(self, request):
        """Create a new card"""
        info_logger.info("CardView POST API called.")
        data = request.data
        card_data = data.pop("card_data")
        serializer = CardDataSerializer(data=card_data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            message = {
                "is_success": "true",
                "message": "OK",
                "data": serializer.data
            }
            return Response(message, status=status.HTTP_201_CREATED)

        else:
            message = {
                "is_success": "false",
                "message": "please check the fields",
            }
            error_logger.error(serializer.errors)
            info_logger.error(f"Failed To Create New Card")
            return Response(message, status=status.HTTP_400_BAD_REQUEST)


class CardDetailView(RetrieveAPIView):
    """Get card by id"""
    lookup_field = "id"
    queryset = Card.objects.all()
    serializer_class = CardSerializer


class ApplicationView(APIView):
    """Application view for get and post"""

    serializer_class = ApplicationSerializer

    def get(self, request, format = None):
        """GET Application data"""
        apps = Application.objects.all()
        serializer = self.serializer_class(apps, many = True)
        message = {
            "is_success":True,
            "message": "OK",
            "data": serializer.data
        }
        return Response(message, status = status.HTTP_200_OK)

    def post(self, request):
        """POST Application Data"""

        info_logger.info("ApplicationView POST API called.")
        serializer = self.serializer_class(data = request.data)
        if serializer.is_valid():
            serializer.save(created_by = request.user)
            message = {
                "is_success": True,
                "message": "OK",
                "data": serializer.data
            }
            return Response(message, status = status.HTTP_201_CREATED)
        message = {
            "is_success": False,
            "message": "Data is not valid",
            "error": serializer.errors
        }
        error_logger.error(serializer.errors)
        return Response(message, status = status.HTTP_400_BAD_REQUEST)


class ApplicationDetailView(APIView):
    """Get application details by id"""

    serializer_class = ApplicationDataSerializer

    def get(self, request, id, format = None):
        """Get details of specific application"""
        try:
            app = Application.objects.get(id = id)
        except Exception:
            message = {
                "is_success": False,
                "message": "No application exist for this id."
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = self.serializer_class(app)
        message = {
            "is_success": True,
            "message": "OK",
            "data": serializer.data
        }
        return Response(message, status = status.HTTP_200_OK)


class PageView(APIView):
    """Get and Post Page data"""
    serializer_class = PageSerializer

    def get(self, request, format = None):
        """Get list of all Pages"""

        pages = Page.objects.all()
        serializer = self.serializer_class(pages, many = True)
        message = {
            "is_success":True,
            "message": "OK",
            "data": serializer.data
        }
        return Response(message, status = status.HTTP_200_OK)

    def post(self, request):
        """ Save Page data"""
        
        serializer = self.serializer_class(data = request.data,context = {'request':request})
        if serializer.is_valid():
            serializer.save()
            message = {
                "is_success": True,
                "message": "OK",
                "data": serializer.data
            }
            return Response(message, status = status.HTTP_201_CREATED)
        message = {
            "is_success": False,
            "message": "Data is not valid",
            "error": serializer.errors
        }
        return Response(message, status = status.HTTP_400_BAD_REQUEST)


class PageDetailView(APIView):
    """Specific Page Details"""
    serializer_class = PageDetailSerializer

    def get(self, request, id, format = None):
        """Get page specific details"""
        
        query_params = request.query_params
        try:
            page = Page.objects.get(id = id)
        except Exception:
            message = {
                "is_success": False,
                "message": "No pages exist for this id."
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        page_version = None
        if query_params.get('version'):
            try:
                page_version = PageVersion.objects.get(page = page, version_no = query_params.get('version'))
            except Exception:
                message = {
                    "is_success": False,
                    "message": "This version of page doesnot exist."
                }
                return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = self.serializer_class(page, context = {'page_version': page_version})
        message = {
            "is_success": True,
            "message": "OK",
            "data": serializer.data
        }
        return Response(message, status = status.HTTP_200_OK)
        
