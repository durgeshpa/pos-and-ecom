import logging

from rest_framework import authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from retailer_backend.utils import SmallOffsetPagination
from .serializers import CategoryCrudSerializers

from products.common_function import get_response, serializer_error
from categories.common_validators import validate_data_format
from products.common_validators import validate_id
from categories.services import category_search
from categories.models import Category

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class CategoryView(GenericAPIView):
    """
        Get Brand
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Category.objects.filter(category_parent=None).select_related('updated_by').prefetch_related(
        'sub_category',).only('id', 'category_name', 'category_desc', 'category_image', 'category_sku_part',
                              'updated_by', 'status', 'category_slug')
    serializer_class = CategoryCrudSerializers

    def get(self, request):
        if request.GET.get('id'):
            """ Get Category for specific ID with SubCategory"""
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            category = id_validation['data']
        else:
            self.queryset = self.search_filter_category()
            category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        return get_response('category list!', serializer.data)

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

        if not modified_data['id']:
            return get_response('please provide id to update category', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        parent_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=parent_product_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Parent Product Updated Successfully.")
            return get_response('parent product updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_category(self):

        cat_status = self.request.GET.get('status')
        child_category_name = self.request.GET.get('child_category_name')
        search_text = self.request.GET.get('search_text')

        # search based on status
        if search_text:
            self.queryset = category_search(self.queryset, search_text)

        # filter based on status
        if cat_status is not None:
            self.queryset = self.queryset.filter(status=cat_status)
        if child_category_name is not None:
            self.queryset = self.queryset.filter(cat_parent=child_category_name)

        return self.queryset
