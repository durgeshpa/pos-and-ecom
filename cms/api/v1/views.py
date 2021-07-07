import logging
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from .serializers import CardDataSerializer, CardSerializer, ApplicationSerializer, ApplicationDataSerializer, PageSerializer, PageDetailSerializer, CardItemSerializer
from ...choices import CARD_TYPE_CHOICES
from ...models import Application, Card, CardVersion, Page, PageVersion, CardItem

from .pagination import PaginationHandlerMixin
from rest_framework.pagination import LimitOffsetPagination

from django.core.cache import cache

from cms.permissions import ( has_cards_create_permission,
                              has_apps_create_permission,
                              has_pages_create_permission,
                              has_pages_status_change_permission,
                              has_apps_status_change_permission
                              )

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
        if cache.get('cards'):
            info_logger.info("----------USING CACHED CARDS @GET cards/--------")
            queryset = cache.get('cards')
        else:
            queryset = Card.objects.all()
            info_logger.info("-----CACHING CARDS  @GET cards/----------")
            cache.set('cards', queryset)

        if query_params.get('name'):
            name = query_params.get('name')
            queryset = queryset.filter(name__icontains=name)

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
        has_cards_create_permission(request.user)
        info_logger.info("CardView POST API called.")
        data = request.data
        card_data = data.pop("card_data")
        serializer = CardDataSerializer(data=card_data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()

            cache.delete('cards')
            info_logger.info("-----------CARDS CACHE INVALIDATED  @POST cards/-----------")

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
        
    
    def patch(self, request):

        data = request.data
        
        try:
            card_id = data.pop("card_id")
        except:
            raise ValidationError("field card_id is required")

        card_data_data = data.get("card_data")


        card_details_data = data.get("card_details")


        try:
            card = Card.objects.get(id=card_id)
        except:
            raise ValidationError("Card with id {id} not found")


        card_version = CardVersion.objects.filter(card=card).last()
        card_data = card_version.card_data

        old_card_items = card_data.items.all()



        # cloning model instance
        card_data.pk = None
        card_data.save()

        message = {
            "is_success": True,
            "error": []
        }


        if(card_data_data):

            card_data_serializer = CardDataSerializer(card_data, data=card_data_data, partial=True)

            if(card_data_serializer.is_valid()):
                        card_data_serializer.save()
            else:
                message["is_success"]=False
                message["error"].append(card_data_serializer.errors)


        if(card_details_data):
            card_serializer = CardSerializer(card, data=card_details_data, partial=True)
            if(card_serializer.is_valid()):
                card_serializer.save()
            else:
                message["is_success"]=False
                message["error"].append(card_serializer.errors)
        

        # copy all items to new card_data
        for item in old_card_items:
            # create a copy of item objectc
            item.pk = None
            item.save()

            item.card_data = card_data
            item.save()

      
        
        # create a new version
        new_version = CardVersion.objects.create(version_number=card_version.version_number+1,
        card=card,
        card_data=card_data)



        cache.delete('cards')
        info_logger.info("-----------CARDS CACHE INVALIDATED  @PATCH cards/-----------")

       
        


        return Response(message)


class ItemsView(APIView):


    def post(self, request):

        data = request.data
        try:
            card_id = data.pop("card_id")
        except:
            raise ValidationError("field card_id is required")


        serializer = CardItemSerializer(data=data, context={"card_id": card_id})

        message = {
            "is_success": True,
            "errors": []
        }

        if(serializer.is_valid()):
            serializer.save()
            info_logger.info(f"-----------CARD ITEM CREATED-----------")
            cache.delete('cards')
            info_logger.info("-----------CARDS CACHE INVALIDATED  @POST items/-----------")

        else:
            message["is_success"] = False,
            message["errors"].append(serializer.errors)


        return Response(message)


    def patch(self, request):
        data = request.data
        try:
            item_id = data.pop("item_id")
        except:
            raise ValidationError("field item_id is required")

        try:
            item = CardItem.objects.get(id=item_id)
        except:
            raise ValidationError("CardItem with id {item_id} not found")

        serializer = CardItemSerializer(item, data=data, partial=True)

        message = {
            "is_success": True,
            "errors": []
        }

        if(serializer.is_valid()):
            serializer.save()
            info_logger.info(f"-----------CARD ITEM with id {item_id} updated-----------")
            cache.delete('cards')
            info_logger.info("-----------CARDS CACHE INVALIDATED  @PATCH items/-----------")

        else:
            message["is_success"] = False,
            message["errors"].append(serializer.errors)


        return Response(message)

    def delete(self, request):
        data = request.data
        try:
            item_id = data.pop("item_id")
        except:
            raise ValidationError("field item_id is required")
        
        try:
            item = CardItem.objects.get(id=item_id)
        except:
            raise ValidationError(f"CardItem with id {item_id} not found.")
        
        try:
            item.delete()
            info_logger.info(f"-----------CARD ITEM with id {item_id} deleted-----------")

        except:
            raise ValidationError(f"Error while deleting Item")

        cache.delete('cards')
        info_logger.info("-----------CARDS CACHE INVALIDATED  @DELETE items/-----------")
        
        message = {

            "is_success": True,
            "errors": []
        }
        return Response(message) 

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

        query_params = request.query_params
        if query_params.get('name'):
            apps = apps.filter(name__icontains = query_params.get('name'))
        
        serializer = self.serializer_class(apps, many = True)
        message = {
            "is_success":True,
            "message": "OK",
            "data": serializer.data
        }
        return Response(message, status = status.HTTP_200_OK)

    def post(self, request):
        """POST Application Data"""
        has_apps_create_permission(request.user)

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
    
    def patch(self, request, id):
        """Update an application detail"""

        has_apps_status_change_permission(request.user)

        try:
            app = Application.objects.get(id = id)
        except Exception:
            message = {
                "is_success": False,
                "message": "No application exist for this id."
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = self.serializer_class(data=request.data, instance=app, partial=True)
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
        error_logger.error(serializer.errors)
        return Response(message, status = status.HTTP_400_BAD_REQUEST)


class PageView(APIView):
    """Get and Post Page data"""
    serializer_class = PageSerializer

    def get(self, request, format = None):
        """Get list of all Pages"""

        if cache.get('pages'):
            info_logger.info("----------USING CACHED PAGES @GET pages/--------")
            pages = cache.get('pages')
        else:
            pages = Page.objects.all()
            info_logger.info("-----CACHING PAGES  @GET pages/----------")
            cache.set('pages', pages)

        
        serializer = self.serializer_class(pages, many = True)
        message = {
            "is_success":True,
            "message": "OK",
            "data": serializer.data
        }
        return Response(message, status = status.HTTP_200_OK)

    def post(self, request):
        """ Save Page data"""
        has_pages_create_permission(request.user)
        
        serializer = self.serializer_class(data = request.data,context = {'request':request})
        if serializer.is_valid():
            serializer.save()
            cache.delete('pages')
            info_logger.info("-----------PAGES CACHE INVALIDATED  @POST pages/-----------")

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

    def patch(self, request):
        """Changing Page Card mapping"""
        data = request.data
        page_id = data.get('page_id', None)
        if not page_id:
            raise ValidationError({"message": "page_id is required"})
        try:
            page = Page.objects.get(id = page_id)
        except Exception:
            raise NotFound({"message": f"No pages exists with id {page_id}"})
        serializer = self.serializer_class(data=data, instance=page, context = {'request':request} ,partial=True)
        if serializer.is_valid():
            serializer.save()

            cache.delete('pages')
            info_logger.info("-----------PAGES CACHE INVALIDATED  @PATCH pages/-----------")

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

            page_id = f"page_{id}"
            cached_page = cache.get(page_id, None)

            # cached_page = cached_pages[id]
            if(cached_page):
                page = cached_page
            else:
                page = Page.objects.get(id = id)
                cache.set(page_id, page)

        except Exception:
            message = {
                "is_success": False,
                "message": "No Page Exists for this id",
            }
            info_logger.info("-----USING PAGE FROM CACHE  @GET pages/id----------")
            return Response(message, status = status.HTTP_200_OK)


        page_version = None
        if query_params.get('version'):
            try:
                page_version_key = f"page_version_{id}_{query_params.get('version')}"
                cached_version = cache.get(page_version_key, None)
                if(cached_version):
                    page_version = cached_version
                else:
                    page_version = PageVersion.objects.get(page = page, version_no = query_params.get('version'))
                    
                    cache.set(page_version_key, page_version)

            except Exception:
                message = {
                    "is_success": False,
                    "message": "This version of page does not exist."
                }
                return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = self.serializer_class(page, context = {'page_version': page_version})
        print(serializer.data)
        message = {
            "is_success": True,
            "message": "OK",
            "data": serializer.data
        }

        info_logger.info("-----SET PAGE IN CACHE  @GET pages/id----------")

        return Response(message, status = status.HTTP_200_OK)


    def patch(self, request, id):
        """Update Specific Page Details such as publishing page and change status"""
        has_pages_status_change_permission(request.user)
        try:
            page = Page.objects.get(id = id)
        except Exception:
            message = {
                "is_success": False,
                "message": "No pages exist for this id."
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = PageDetailSerializer(data=request.data, instance=page, partial=True)
        if serializer.is_valid():
            serializer.save()

            page_id = f"page_{id}"
            cache.delete(page_id)

            cache.set(page_id, page)

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