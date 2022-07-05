import logging
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import RetrieveAPIView, GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, generics
from rest_auth import authentication
from rest_framework.permissions import AllowAny

from categories.models import Category
from brand.models import Brand
from retailer_backend.utils import SmallOffsetPagination, OffsetPaginationDefault50
from .serializers import CardDataSerializer, CardSerializer, ApplicationSerializer, ApplicationDataSerializer, \
    PageSerializer, PageDetailSerializer, CardItemSerializer, PageLatestDetailSerializer, CategorySerializer, \
    SubCategorySerializer, BrandSerializer, SubBrandSerializer, LandingPageSerializer, PageFunctionSerializer, \
    TemplateSerializer
from ...choices import CARD_TYPE_CHOICES, LANDING_PAGE_TYPE_CHOICE, LISTING_SUBTYPE_CHOICE, IMAGE_TYPE_CHOICE
from ...models import Application, Card, CardVersion, Page, PageVersion, CardItem, ApplicationPage, LandingPage, \
    Functions, Template
from ...utils import api_response, get_response, serializer_error, check_shop

from .pagination import PaginationHandlerMixin
from rest_framework.pagination import LimitOffsetPagination

from django.core.cache import cache

from cms.permissions import (has_cards_create_permission,
                             has_apps_create_permission,
                             has_pages_create_permission,
                             has_pages_status_change_permission,
                             has_apps_status_change_permission, IsCMSDesigner
                             )

from cms.messages import VALIDATION_ERROR_MESSAGES, SUCCESS_MESSAGES, ERROR_MESSAGES
from ...validators import validate_data_format, validate_id

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
            queryset = Card.objects.order_by('-id')
            info_logger.info("-----CACHING CARDS  @GET cards/----------")
            cache.set('cards', queryset)

        if query_params.get('name'):
            name = query_params.get('name')
            queryset = queryset.filter(name__icontains=name)

        if query_params.get('id'):
            card_id = query_params.get('id')
            queryset = queryset.filter(id=card_id)
            if len(queryset) == 0:
                raise NotFound(ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(card_id))

        if query_params.get('app_id'):
            try:
                app_id = query_params.get('app_id')
                app = get_object_or_404(Application, id=app_id)
                queryset = queryset.filter(app=app)
            except:
                raise NotFound(ERROR_MESSAGES["APP_ID_NOT_FOUND"].format(app_id))
        
        if query_params.get('card_type'):
            card_type = query_params.get('card_type')
            if card_type not in [ x[0] for x in CARD_TYPE_CHOICES] :
                raise ValidationError(VALIDATION_ERROR_MESSAGES["CARD_ITEM_NOT_VALID"].format([ x[0] for x in CARD_TYPE_CHOICES]))
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
            "message": SUCCESS_MESSAGES["CARDS_RETRIEVE_SUCCESS"],
            "data": cards.data
        }
        return Response(message)

    def post(self, request):
        """Create a new card"""
        has_cards_create_permission(request.user)
        info_logger.info("CardView POST API called.")

        request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
        data = request.data
        card_data = data.pop("card_data")
        serializer = CardDataSerializer(data=card_data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()

            cache.delete('cards')
            info_logger.info("-----------CARDS CACHE INVALIDATED  @POST cards/-----------")

            message = {
                "is_success": "true",
                "message": SUCCESS_MESSAGES["CARD_CREATE_SUCCESS"],
                "data": serializer.data
            }
            return Response(message, status=status.HTTP_201_CREATED)

        else:
            message = {
                "is_success": "false",
                "message": VALIDATION_ERROR_MESSAGES["CARD_POST_DETAILS_NOT_VALID"],
            }
            error_logger.error(serializer.errors)
            info_logger.error(f"Failed To Create New Card")
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
        
    
    def patch(self, request):

        data = request.data
        
        try:
            card_id = data.pop("card_id")
        except:
            raise ValidationError(VALIDATION_ERROR_MESSAGES["CARD_ID_REQUIRED"])

        card_data_data = data.get("card_data")


        card_details_data = data.get("card_details")


        try:
            card = Card.objects.get(id=card_id)
        except:
            raise ValidationError(ERROR_MESSAGES["CARD_ID_NOT_FOUND"].format(id))


        card_version = CardVersion.objects.filter(card=card).last()
        card_data = card_version.card_data

        old_card_items = card_data.items.all()



        # cloning model instance
        card_data.pk = None
        card_data.save()

        message = {
            "is_success": True,
            "message": SUCCESS_MESSAGES["CARD_PATCH_SUCCESS"],
            "error": []
        }


        if(card_data_data):

            card_data_serializer = CardDataSerializer(card_data, data=card_data_data, partial=True)

            if(card_data_serializer.is_valid()):
                        card_data_serializer.save()
            else:
                message["is_success"]=False
                message["message"] = ERROR_MESSAGES["CARD_PATCH_FAIL"]
                message["error"].append(card_data_serializer.errors)


        if(card_details_data):
            card_serializer = CardSerializer(card, data=card_details_data, partial=True)
            if(card_serializer.is_valid()):
                card_serializer.save()
            else:
                message["is_success"]=False
                message["message"] = ERROR_MESSAGES["CARD_PATCH_FAIL"]
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
            raise ValidationError(VALIDATION_ERROR_MESSAGES["ITEM_CARD_ID_REQUIRD"])


        serializer = CardItemSerializer(data=data, context={"card_id": card_id})

        message = {
            "is_success": True,
            "message": SUCCESS_MESSAGES["ITEM_CREATE_SUCCESS"],
            "errors": []
        }

        if(serializer.is_valid()):
            serializer.save()
            info_logger.info(f"-----------CARD ITEM CREATED-----------")
            cache.delete('cards')
            info_logger.info("-----------CARDS CACHE INVALIDATED  @POST items/-----------")

        else:
            message["is_success"] = False
            message["message"] = ERROR_MESSAGES["ITEM_CREATE_FAIL"]
            message["errors"].append(serializer.errors)


        return Response(message)


    def patch(self, request):
        data = request.data
        try:
            item_id = data.pop("item_id")
        except:
            raise ValidationError(VALIDATION_ERROR_MESSAGES["ITEM_ID_REQUIRED"])

        try:
            item = CardItem.objects.get(id=item_id)
        except:
            raise ValidationError(VALIDATION_ERROR_MESSAGES["ITEM_WITH_ID_NOT_FOUND"].format(item_id))

        serializer = CardItemSerializer(item, data=data, partial=True)

        message = {
            "is_success": True,
            "message": SUCCESS_MESSAGES["ITEM_PATCH_SUCCESS"],
            "errors": []
        }

        if(serializer.is_valid()):
            serializer.save()
            info_logger.info(f"-----------CARD ITEM with id {item_id} updated-----------")
            cache.delete('cards')
            info_logger.info("-----------CARDS CACHE INVALIDATED  @PATCH items/-----------")

        else:
            message["is_success"] = False,
            message["message"] = ERROR_MESSAGES["ITEM_PATCH_FAIL"],
            message["errors"].append(serializer.errors)


        return Response(message)

    def delete(self, request):
        data = request.data
        try:
            item_id = data.pop("item_id")
        except:
            raise ValidationError(VALIDATION_ERROR_MESSAGES["ITEM_ID_REQUIRED"])
        
        try:
            item = CardItem.objects.get(id=item_id)
        except:
            raise ValidationError(VALIDATION_ERROR_MESSAGES["ITEM_WITH_ID_NOT_FOUND"].format(item_id))
        
        try:
            item.delete()
            info_logger.info(f"-----------CARD ITEM with id {item_id} deleted-----------")

        except:
            raise ValidationError(ERROR_MESSAGES["ITEM_DELEATE_FAIL"])

        cache.delete('cards')
        info_logger.info("-----------CARDS CACHE INVALIDATED  @DELETE items/-----------")
        
        message = {

            "is_success": True,
            "message": SUCCESS_MESSAGES["ITEM_DELETE_SUCCESS"],
            "errors": []
        }
        return Response(message) 

class CardDetailView(RetrieveAPIView):
    """Get card by id"""
    lookup_field = "id"
    queryset = Card.objects.order_by('-id')
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
            "message": SUCCESS_MESSAGES["APP_RETRIEVE_SUCCESS"],
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
                "message": SUCCESS_MESSAGES["APP_CREATE_SUCCESS"],
                "data": serializer.data
            }
            return Response(message, status = status.HTTP_201_CREATED)
        message = {
            "is_success": False,
            "message": ERROR_MESSAGES["APP_CREATE_FAIL"],
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
                "message": ERROR_MESSAGES["APP_ID_NOT_FOUND"].format(id)
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = self.serializer_class(app)
        message = {
            "is_success": True,
            "message": SUCCESS_MESSAGES["APP_RETRIEVE_SUCCESS"],
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
                "message": ERROR_MESSAGES["APP_ID_NOT_FOUND"].format(id)
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = self.serializer_class(data=request.data, instance=app, partial=True)
        if serializer.is_valid():
            serializer.save()
            message = {
                "is_success": True,
                "message": SUCCESS_MESSAGES["APP_PATCH_SUCCESS"],
                "data": serializer.data
            }
            return Response(message, status = status.HTTP_201_CREATED)
        message = {
            "is_success": False,
            "message": ERROR_MESSAGES["APP_PATCH_FAIL"],
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
            pages = Page.objects.order_by('-id')
            info_logger.info("-----CACHING PAGES  @GET pages/----------")
            cache.set('pages', pages)

        serializer = self.serializer_class(pages, many = True)

        query_params = request.query_params
        if query_params.get('app_name') and query_params.get('page_name'):
            app = Application.objects.filter(name = query_params.get('app_name')).last()
            app_page = ApplicationPage.objects.filter(app = app, page__name__contains=query_params.get('page_name'))
            page = app_page.last().page
            serializer = PageDetailSerializer(page)

        message = {
            "is_success":True,
            "message": SUCCESS_MESSAGES["PAGE_RETRIEVE_SUCCESS"],
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
                "message": SUCCESS_MESSAGES["PAGE_CREATE_SUCCESS"],
                "data": serializer.data
            }
            return Response(message, status = status.HTTP_201_CREATED)
        message = {
            "is_success": False,
            "message": ERROR_MESSAGES["PAGE_CREATE_FAIL"],
            "error": serializer.errors
        }
        return Response(message, status = status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """Changing Page Card mapping"""
        data = request.data
        page_id = data.get('page_id', None)
        if not page_id:
            raise ValidationError(VALIDATION_ERROR_MESSAGES["PAGE_ID_REQUIRED"])
        try:
            page = Page.objects.get(id = page_id)
        except Exception:
            raise NotFound(ERROR_MESSAGES["PAGE_ID_NOT_FOUND"].format(page_id))
        serializer = self.serializer_class(data=data, instance=page, context = {'request':request} ,partial=True)
        if serializer.is_valid():
            serializer.save()

            cache.delete('pages')
            info_logger.info("-----------PAGES CACHE INVALIDATED  @PATCH pages/-----------")

            message = {
                "is_success": True,
                "message": SUCCESS_MESSAGES["PAGE_PATCH_SUCCESS"],
                "data": serializer.data
            }
            return Response(message, status = status.HTTP_201_CREATED)
        message = {
            "is_success": False,
            "message": ERROR_MESSAGES["PAGE_PATCH_FAIL"],
            "error": serializer.errors
        }
        return Response(message, status = status.HTTP_400_BAD_REQUEST)


class PageDetailView(APIView):
    """Specific Page Details"""
    serializer_class = PageDetailSerializer

    def get(self, request, id, format = None):
        """Get page specific details"""

        request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
        query_params = request.query_params
        try:
            page = Page.objects.get(id = id)
        except Exception:
            message = {
                "is_success": False,
                "message": ERROR_MESSAGES["PAGE_ID_NOT_FOUND"].format(id)
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        page_version = None
        if query_params.get('version'):
            try:
                page_version = PageVersion.objects.get(page = page, version_no = query_params.get('version'))
            except Exception:
                message = {
                    "is_success": False,
                    "message": ERROR_MESSAGES["PAGE_VERSION_NOT_FOUND"].format(query_params.get('version'))
                }
                return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = self.serializer_class(page, context = {'page_version': page_version})
        message = {
            "is_success": True,
            "message": SUCCESS_MESSAGES["PAGE_RETRIEVE_SUCCESS"],
            "data": serializer.data
        }
        return Response(message, status = status.HTTP_200_OK) 


    def patch(self, request, id):
        """Update Specific Page Details such as publishing page and change status"""
        has_pages_status_change_permission(request.user)
        try:
            page = Page.objects.get(id = id)
        except Exception:
            message = {
                "is_success": False,
                "message": ERROR_MESSAGES["PAGE_ID_NOT_FOUND"].format(id)
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        serializer = PageDetailSerializer(data=request.data, instance=page, partial=True)
        if serializer.is_valid():
            serializer.save()

            # page_id = f"page_{id}"
            latest_page_key = f"latest_page_{id}"

            # cache.delete(page_id)
            cache.delete(latest_page_key)


            message = {
                "is_success": True,
                "message": SUCCESS_MESSAGES["PAGE_PATCH_SUCCESS"],
                "data": serializer.data
            }

            latest_page_version_no = page.active_version_no
            if latest_page_version_no == None:
                message_to_cache = {
                "is_success": False,
                "message": ERROR_MESSAGES["PAGE_NOT_PUBLISHED"],
                }
            else: 
                latest_page_version = PageVersion.objects.get(version_no = latest_page_version_no, page = page)
                data = PageLatestDetailSerializer(page, context = {'version': latest_page_version}).data

                message_to_cache = {
                    "is_success": True,
                    "message": "OK",
                    "data": data
                }

            # custom_message = dict(message)
            # custom_message["message"] = SUCCESS_MESSAGES["PAGE_RETRIEVE_SUCCESS"]
            # cache.set(page_id, custom_message)

            cache.set(latest_page_key, message_to_cache)

            return Response(message, status = status.HTTP_201_CREATED)
        message = {
            "is_success": False,
            "message": ERROR_MESSAGES["PAGE_PATCH_FAIL"],
            "error": serializer.errors
        }
        return Response(message, status = status.HTTP_400_BAD_REQUEST)


class PageVersionDetailView(APIView):
    """For Latest Version of Page"""

    serializer_class = PageLatestDetailSerializer
    permission_classes = (AllowAny,)

    @check_shop
    def get(self, request, id, *args, **kwargs):
        """Get Data of Latest Version"""
        request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
        shop_id = kwargs.get('shop', None)
        parent_shop = kwargs.get('parent_shop', None)
        try:
            page_key = f"latest_page_{id}"
            # cached_page = cache.get(page_key, None)
            # if(cached_page):
            #     return Response(cached_page, status=status.HTTP_200_OK)
            # else:
            page = Page.objects.get(id = id)
        except Exception:
            message = {
                "is_success": False,
                "message": ERROR_MESSAGES["PAGE_ID_NOT_FOUND"].format(id)
            }
            return Response(message, status = status.HTTP_204_NO_CONTENT)
        
        latest_page_version_no = page.active_version_no
        if latest_page_version_no == None:
            message = {
            "is_success": False,
            "message": ERROR_MESSAGES["PAGE_NOT_PUBLISHED"],
            }
            return Response(message)
        latest_page_version = PageVersion.objects.get(version_no = latest_page_version_no, page = page)
        serializer = self.serializer_class(page, context = {'version': latest_page_version, 'shop_id': shop_id,
                                                            'parent_shop': parent_shop})
        message = {
            "is_success": True,
            "message": "OK",
            "data": serializer.data
        }
        #cache.set(page_key, message)
        return Response(message)


class CategoryListView(APIView):
    """
    View to get list of all categories
    """
    
    def get(self, request, format = None):
        is_success = False
        message = "Category Not Found"
        category = Category.objects.filter(category_parent = None, status = True)
        serializer = CategorySerializer(category, many = True)
        if category:
            is_success = True
            message = "Category Found"
        return api_response(message, serializer.data, status.HTTP_200_OK,  is_success)

class SubCategoryListView(APIView):
    """
    Get List of Subcategory having banner
    """

    def get(self, request, format = None):
        is_success = False
        message = "No Subcategory"
        try:
            category = Category.objects.get(id = request.GET.get('category_id'))
        except Exception:
            raise ValidationError('No such category')
        subcategory = category.cat_parent.filter(status = True).prefetch_related('banner_subcategory')
        serializer = SubCategorySerializer(subcategory, many = True)
        if subcategory.exists():
            is_success = True
            message = "Subcategory Found"
        return api_response(message, serializer.data, status.HTTP_200_OK,  is_success)        


class BrandListView(APIView):
    """
    View to get list of all brands
    """
    
    def get(self, request, format = None):
        is_success = False
        message = "Brand Not Found"
        brand = Brand.objects.filter(brand_parent = None)
        serializer = BrandSerializer(brand, many = True)
        if brand:
            is_success = True
            message = "Brand Found"
        return api_response(message, serializer.data, status.HTTP_200_OK,  is_success)

class SubBrandListView(APIView):
    """
    Get List of SubBrand 
    """

    def get(self, request, format = None):
        is_success = False
        message = "No SubBrand"
        try:
            brand = Brand.objects.get(id = request.GET.get('brand_id'))
        except Exception:
            raise ValidationError('No such brand')
        subbrands = brand.brand_child.all().prefetch_related('banner_subbrand')
        serializer = SubBrandSerializer(subbrands, many = True)
        if subbrands.exists():
            is_success = True
            message = "SubBrand Found"
        return api_response(message, serializer.data, status.HTTP_200_OK,  is_success)        


class PageFunctionView(generics.GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsCMSDesigner)
    queryset = Functions.objects.order_by('-id')
    serializer_class = PageFunctionSerializer

    def get(self, request):

        if request.GET.get('id'):
            page_functions = Functions.objects.filter(type=request.GET.get('type'), id=request.GET.get('id'))
        else:
            self.queryset = self.filter_page_functions()
            page_functions = OffsetPaginationDefault50().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(page_functions, many=True)
        msg = "" if page_functions else "no page function found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data, context={'request':request})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('function created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def filter_page_functions(self):
        type = self.request.GET.get('type')

        if type:
            self.queryset = self.queryset.filter(type=type)
        return self.queryset


class LandingPageView(generics.GenericAPIView):

    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, )
    queryset = LandingPage.objects.order_by('-id')
    serializer_class = LandingPageSerializer

    @check_shop
    def get(self, request, *args, **kwargs):
        if request.GET.get('id'):
            landing_pages = LandingPage.objects.filter(id=request.GET.get('id'))
        else:
            self.queryset = self.filter_landing_pages()
            landing_pages = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        shop_id = kwargs.get('shop', None)
        app_id = kwargs.get('app_type', None)
        parent_shop = kwargs.get('parent_shop', None)
        serializer = self.serializer_class(landing_pages, many=True, context={'request':request, 'shop_id': shop_id,
                                                                              'app_id':app_id, 'parent_shop':parent_shop})
        msg = "" if landing_pages else "no landing page found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        modified_data = self.validate_request()
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('landing page created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


    def put(self, request):
        if 'id' not in request.data:
            return get_response('please provide id to update Landing page', False)

        # validations for input id
        id_validation = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_validation:
            return get_response(id_validation['error'])
        instance = id_validation['data'].last()

        serializer = self.serializer_class(instance=instance, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('landing page updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def filter_landing_pages(self):
        type = self.request.GET.get('type')
        sub_type = self.request.GET.get('sub_type')
        app = self.request.GET.get('app')
        name = self.request.GET.get('name')

        if type:
            self.queryset = self.queryset.filter(type=type)

        if sub_type:
            self.queryset = self.queryset.filter(sub_type=sub_type)

        if app:
            self.queryset = self.queryset.filter(app_id=app)

        if name:
            self.queryset = self.queryset.filter(name__icontains=name)

        return self.queryset


    def validate_request(self):
        return self.request.data



class CardTypeList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in CARD_TYPE_CHOICES]
        return get_response('', data, True)


class LandingPageTypeList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in LANDING_PAGE_TYPE_CHOICE]
        return get_response('', data, True)


class LandingPageSubTypeList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in LISTING_SUBTYPE_CHOICE]
        return get_response('', data, True)


class ImageTypeList(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        fields = ['id', 'value']
        data = [dict(zip(fields, d)) for d in IMAGE_TYPE_CHOICE]
        return get_response('', data, True)


class TemplateCRUDView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = TemplateSerializer
    queryset = Template.objects.order_by('-id')

    def get(self, request, *args, **kwargs):
        if request.GET.get('id'):
            templates = self.queryset.filter(id=request.GET.get('id'))
        else:
            self.queryset = self.filter_templates()
            templates = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(templates, many=True)
        msg = "" if templates else "no template found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        modified_data = self.validate_request()
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('Template created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def filter_templates(self):
        app = self.request.GET.get('app')
        name = self.request.GET.get('name')

        if app:
            self.queryset = self.queryset.filter(app_id=app)

        if name:
            self.queryset = self.queryset.filter(name__icontains=name)

        return self.queryset

    def validate_request(self):
        return self.request.data

