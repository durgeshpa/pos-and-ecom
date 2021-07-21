import logging
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist

from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView
from retailer_backend.utils import SmallOffsetPagination

from shops.models import Shop, ParentRetailerMapping
from wms.common_functions import get_stock_available_category_list
from .serializers import CategorySerializer, CategoryDataSerializer, BrandSerializer, AllCategorySerializer, \
    SubCategorySerializer, CategoryCrudSerializers, CategoryExportAsCSVSerializers
from categories.models import Category, CategoryData, CategoryPosation
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.permissions import (AllowAny, IsAuthenticated)
from brand.models import Brand
from products.common_function import get_response, serializer_error
from categories.common_validators import validate_data_format
from products.common_validators import validate_id
from categories.services import category_search
from categories.models import Category

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
        if Shop.objects.filter(id=shop_id).exists():
            shop = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
            # get list of category ids with available inventory for this shop
            categories_with_products = get_stock_available_category_list(shop)
        else:
            # get list of category ids with available inventory
            categories_with_products = get_stock_available_category_list()
        category = Category.objects.get(pk=category_id)
        sub_categories = category.cat_parent.filter(status=True, id__in=categories_with_products)
        sub_category_data_serializer = SubCategorySerializer(sub_categories, many=True)

        is_success = True if sub_categories else False
        return Response({"message": [""], "response_data": sub_category_data_serializer.data, "is_success": is_success})


class GetAllCategoryListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        categories = Category.objects.filter(category_parent=None, status=True)
        category_subcategory_serializer = AllCategorySerializer(categories, many=True)

        is_success = True if categories else False
        return Response(
            {"message": [""], "response_data": category_subcategory_serializer.data, "is_success": is_success})


class CategoryView(GenericAPIView):
    """
        Category View
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Category.objects.select_related('updated_by', 'category_parent').prefetch_related('category_log', 'category_log__updated_by', 'sub_category').\
        only('id', 'category_name', 'category_desc', 'category_image', 'category_sku_part', 'updated_by',
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
            """ GET API for Category LIST with SubCategory """
            self.queryset = self.search_filter_category()
            category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
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