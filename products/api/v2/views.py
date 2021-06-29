import logging
from rest_framework import authentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from .serializers import UploadMasterDataSerializers, DownloadMasterDataSerializers, \
    ProductCategoryMappingSerializers, ParentProductImageSerializers, ChildProductImageSerializers
from retailer_backend.utils import SmallOffsetPagination

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format, validate_bulk_data_format
from products.models import BulkUploadForProductAttributes

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BulkUploadProductAttributes(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = BulkUploadForProductAttributes.objects.select_related('updated_by')\
        .only('file', 'updated_by').order_by('-id')
    serializer_class = UploadMasterDataSerializers

    def get(self, request):

        file = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(file, many=True)
        msg = "" if file else "no uploaded file found"
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