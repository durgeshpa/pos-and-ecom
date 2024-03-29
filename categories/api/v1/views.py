import logging
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
from ecom.utils import api_response

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_auth import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView

from retailer_backend.utils import SmallOffsetPagination

from shops.models import Shop, ParentRetailerMapping
from wms.common_functions import get_stock_available_category_list
from .serializers import CategorySerializer, CategoryDataSerializer, BrandSerializer, AllCategorySerializer, \
    SubCategorySerializer, CategoryCrudSerializers, CategoryExportAsCSVSerializers, B2cCategoryCrudSerializers,\
        B2cCategoryExportAsCSVSerializers, B2cCategorySerializer, B2cParentCategorySerializers, B2cSubCategorySerializer,\
            B2cSubCategorySerializers, AllB2cCategorySerializer, B2cCategoryDataSerializer
from categories.models import Category, CategoryData, CategoryPosation, B2cCategory,B2cCategoryData
from rest_framework import viewsets, status
from rest_framework.decorators import list_route
from rest_framework.permissions import (AllowAny, IsAuthenticated)
from brand.models import Brand
from products.common_function import get_response, serializer_error
from categories.common_validators import validate_data_format
from products.common_validators import validate_id
from categories.services import category_search
from categories.models import Category
from cms.models import Card, CardVersion
from brand.api.v1.serializers import BannerImageSerializer

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class GetAllSubCategoryListView(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Category.objects.filter(category_parent=None)
    serializer_class = CategorySerializer

    @list_route
    def roots(self, request):
        queryset = Category.objects.filter(category_parent=None)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class GetAllB2cSubCategoryListView(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = B2cCategory.objects.filter(category_parent=None)
    serializer_class = B2cCategorySerializer

    @list_route
    def roots(self, request):
        queryset = B2cCategory.objects.filter(category_parent=None)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class GetCategoryListBySlot(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        slot_name = self.kwargs.get("slot_name")
        if slot_name:
            category_data = CategoryData.objects.filter(category_pos__posation_name=slot_name)
        else:
            category_data = CategoryData.objects.all()
        category_data_serializer = CategoryDataSerializer(category_data, many=True)
        is_success = True if category_data else False
        return Response({"message": [""], "response_data": category_data_serializer.data, "is_success": is_success})


class GetB2cCategoryListBySlot(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        slot_name = self.kwargs.get("slot_name")
        if slot_name:
            category_data = B2cCategoryData.objects.filter(category_pos__posation_name=slot_name)
        else:
            category_data = B2cCategoryData.objects.all()
        category_data_serializer = B2cCategoryDataSerializer(category_data, many=True)
        is_success = True if category_data else False
        return Response({"message": [""], "response_data": category_data_serializer.data, "is_success": is_success})


class GetcategoryBrandListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        category_id = kwargs.get('category')
        category = Category.objects.get(pk=category_id)
        brands = Brand.objects.filter(categories=category_id)
        category_brand_serializer = BrandSerializer(brands, many=True)
        is_success = True if brands else False
        return Response({"message": [""], "response_data": category_brand_serializer.data, "is_success": is_success})


class GetSubCategoriesListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        category_id = kwargs.get('category')
        shop_id = self.request.GET.get('shop_id')
        if Shop.objects.filter(id=shop_id).exists() and ParentRetailerMapping.objects.filter(retailer=shop_id, status=True).exists():
            shop = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
            # get list of category ids with available inventory for this shop
            categories_with_products = get_stock_available_category_list(shop)
        else:
            # get list of category ids with available inventory
            categories_with_products = get_stock_available_category_list()
        category = Category.objects.get(pk=category_id)
        sub_categories = category.cat_parent.filter(status=True, id__in=categories_with_products)
        sub_category_data_serializer = SubCategorySerializer(sub_categories, many=True)
        banner_image = []
        card = Card.objects.filter(type='category',category_subtype = category).last()
        if card:
            latest_card_version = CardVersion.objects.filter(card = card).last()
            card_items = latest_card_version.card_data.items.all()
            banner_image = BannerImageSerializer(card_items, many=True).data
        is_success = True if sub_categories else False
        data = {}
        if is_success:
            data = {
                "sub_category": sub_category_data_serializer.data,
                "banner_image": banner_image
            }
        return Response({"message": [""],"response_data": data, "is_success": is_success})


class GetAllCategoryListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        categories = Category.objects.filter(category_parent=None, status=True)
        category_subcategory_serializer = AllCategorySerializer(categories, many=True)

        is_success = True if categories else False
        return Response(
            {"message": [""], "response_data": category_subcategory_serializer.data, "is_success": is_success})


class GetAllB2cCategoryListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        categories = B2cCategory.objects.filter(category_parent=None, status=True)
        category_subcategory_serializer = AllB2cCategorySerializer(categories, many=True)

        is_success = True if categories else False
        return Response(
            {"message": [""], "response_data": category_subcategory_serializer.data, "is_success": is_success})


class CategoryView(GenericAPIView):
    """
        Category View
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Category.objects.select_related('updated_by', 'category_parent').prefetch_related('category_log',
                                                                                                 'category_log__updated_by',
                                                                                                 'cat_parent'). \
        only('id', 'category_name', 'category_desc', 'category_image', 'category_sku_part', 'category_type','updated_by',
             'category_parent', 'status', 'category_slug').order_by('-id')
    serializer_class = CategoryCrudSerializers

    def get(self, request):

        category_total_count = self.queryset.count()
        info_logger.info("Category GET api called.")
        if request.GET.get('id'):
            """ Get Category for specific ID with SubCategory"""
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            category = id_validation['data']
        else:
            print('here')
            """ GET API for Category LIST with SubCategory """
            self.queryset = self.search_filter_category()
            category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
            category_total_count = self.queryset.count()
        serializer = self.serializer_class(category, many=True)
        msg = f"total count {category_total_count}" if category else "no category found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Category Creation """

        info_logger.info("Category POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('category created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Category Updation  """

        info_logger.info("Category PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update category', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        category_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=category_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("category Updated Successfully.")
            return get_response('category updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Category """

        info_logger.info("Category DELETE api called.")
        if not request.data.get('category_ids'):
            return get_response('please select category', False)
        try:
            for id in request.data.get('category_ids'):
                category_id = self.queryset.get(id=int(id))
                try:
                    category_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'brand_id': category_id}
                    info_logger.info("category deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete category {category_id.category_name}, '
                                        f'because this category is mapped with product', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid category {id}', False)
        return get_response('category were deleted successfully!', True)

    def search_filter_category(self):

        cat_status = self.request.GET.get('status')
        search_text = self.request.GET.get('search_text')
        cat_type = self.request.GET.get('category_type')
        
        # search based on category name
        if search_text:
            self.queryset = category_search(self.queryset, search_text.strip())

        # filter based on status
        if cat_status is not None:
            self.queryset = self.queryset.filter(status=cat_status)
        
        if cat_type:
            self.queryset = self.queryset.filter(category_type=cat_type)
        
        return self.queryset


class B2cCategoryView(GenericAPIView):
    """
       B2c Category View
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = B2cCategory.objects.select_related('updated_by', 'category_parent').prefetch_related('b2c_category_log',
                                                                                                 'b2c_category_log__updated_by',
                                                                                                 'b2c_cat_parent'). \
        only('id', 'category_name', 'category_desc', 'category_image', 'category_sku_part', 'updated_by',
             'category_parent', 'status', 'category_slug').order_by('-id')
    serializer_class = B2cCategoryCrudSerializers

    def get(self, request):

        category_total_count = self.queryset.count()
        info_logger.info("Category GET api called.")
        if request.GET.get('id'):
            """ Get Category for specific ID with SubCategory"""
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            category = id_validation['data']
        else:
            """ GET API for Category LIST with SubCategory """
            self.queryset = self.search_filter_category()
            category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
            category_total_count = self.queryset.count()
        serializer = self.serializer_class(category, many=True)
        msg = f"total count {category_total_count}" if category else "no category found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Category Creation """

        info_logger.info("Category POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('category created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Category Updation  """

        info_logger.info("Category PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update category', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        category_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=category_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("category Updated Successfully.")
            return get_response('category updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Category """

        info_logger.info("Category DELETE api called.")
        if not request.data.get('category_ids'):
            return get_response('please select category', False)
        try:
            for id in request.data.get('category_ids'):
                category_id = self.queryset.get(id=int(id))
                try:
                    category_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'brand_id': category_id}
                    info_logger.info("category deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete category {category_id.category_name}, '
                                        f'because this category is mapped with product', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid category {id}', False)
        return get_response('category were deleted successfully!', True)

    def search_filter_category(self):

        cat_status = self.request.GET.get('status')
        search_text = self.request.GET.get('search_text')

        # search based on category name
        if search_text:
            self.queryset = category_search(self.queryset, search_text.strip())

        # filter based on status
        if cat_status is not None:
            self.queryset = self.queryset.filter(status=cat_status)
        
        return self.queryset


class CategoryExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = CategoryExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Category CSV """

        info_logger.info("Category ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Category CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class B2cCategoryExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = B2cCategoryExportAsCSVSerializers
    
    def post(self, request):
        ''' Api to download selected b2c type category in csv '''
        
        serializer= self.serializer_class(data=request.data)
        if serializer.is_valid():
            csv_response = serializer.save()
            return HttpResponse(csv_response, content_type='text/csv')
        else:
            return get_response(serializer_error(serializer), False)
        

class ActivateDeactivateCategories(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    
    def post(self, request):
        categories = request.data.get('category_ids')
        active_status = request.data.get('is_active')
        if not categories:
            return api_response("Please select atleast one category.")
        else:
            ct = Category.objects.filter(id__in=categories).update(status=active_status)
            msg = 'Activated' if active_status else 'Deactivated'
            return api_response(f"Categories {msg} successfully.", '', status.HTTP_200_OK, True)