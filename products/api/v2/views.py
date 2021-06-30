import logging
from django.http import HttpResponse

from rest_framework import authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny

from products.models import BulkUploadForProductAttributes

from .serializers import UploadMasterDataSerializers, DownloadMasterDataSerializers, \
    ProductCategoryMappingSerializers, ParentProductImageSerializers, ChildProductImageSerializers
from retailer_backend.utils import SmallOffsetPagination

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format, validate_bulk_data_format
from products.services import bulk_log_search

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BulkUploadProductAttributes(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = BulkUploadForProductAttributes.objects.select_related('updated_by')\
        .only('id', 'file', 'upload_type', 'updated_by', 'created_at', 'updated_at').order_by('-id')
    serializer_class = UploadMasterDataSerializers

    def get(self, request):
        """ GET Bulk Log List for Bulk Uploaded Data """

        info_logger.info("Bulk Log GET api called.")

        if request.GET.get('id'):
            """ Get Bulk Log Detail for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            log = id_validation['data']
        else:
            """ GET Bulk Log List """
            self.queryset = self.search_filter_bulk_log()
            log = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(log, many=True)
        msg = "" if log else "no log found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """
            This function will be used for following operations:
            a)Set the Status to "Deactivated" for a Product
            b)Mapping of "Sub Brand" to "Brand"
            c)Mapping of "Sub Category" to "Category"
            d)Set the data for "Parent SKU"
            e)Mapping of Child SKU to Parent SKU
            f)Set the Child SKU Data
            After following operations, an entry will be created in 'BulkUploadForProductAttributes' Table
        """

        modified_data = validate_bulk_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.get_serializer(data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('data uploaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_bulk_log(self):
        search_text = self.request.GET.get('search_text')
        # search using upload_type and uploaded_by
        if search_text:
            self.queryset = bulk_log_search(self.queryset, search_text)
        return self.queryset


class BulkDownloadProductAttributes(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = DownloadMasterDataSerializers

    def post(self, request):
        """ POST API for Download Sample BulkDownloadProductAttributes """

        info_logger.info("BulkDownloadProductAttributes POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("BulkDownloadProductAttributes Downloaded successfully")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ProductCategoryMapping(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ProductCategoryMappingSerializers

    def post(self, request):
        """ POST API for Updating ProductCategoryMapping """

        info_logger.info("BulkDownloadProductAttributes POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("ProductCategoryMapping upload successfully")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ParentProductMultiImageUploadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ParentProductImageSerializers

    def post(self, request):
        """ POST API for Updating ParentProductImages """

        info_logger.info("ParentProductMultiPhotoUpload POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            info_logger.info("ParentProductMultiPhotoUpload upload successfully")
            return get_response('', serializer.data)
        return get_response(serializer_error(serializer), False)


class ChildProductMultiImageUploadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ChildProductImageSerializers

    def post(self, request):
        """ POST API for Updating ChildProductImages """

        info_logger.info("ChildProductMultiImageUploadView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            info_logger.info("ChildProductMultiImageUploadView upload successfully")
            return get_response('', serializer.data)
        return get_response(serializer_error(serializer), False)