import logging

from rest_framework import authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from retailer_backend.utils import SmallOffsetPagination
from .serializers import CategoryCrudSerializers

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format
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
    queryset = Category.objects.all()
    serializer_class = CategoryCrudSerializers

    def get(self, request):
        if request.GET.get('id'):
            """ Get Category for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            category = id_validation['data']
        else:
            category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        return get_response('category list!', serializer.data)

    def post(self, request):
        """ POST API for Category Creation """

        info_logger.info("Category POST api called.")

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('category created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Category Updation  """

        info_logger.info("Category PUT api called.")