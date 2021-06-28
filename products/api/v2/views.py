import logging

from rest_framework import authentication
from rest_framework.generics import GenericAPIView

from django.http import HttpResponse
from .serializers import UploadMasterDataSerializers, DownloadMasterDataSerializers

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format, validate_bulk_data_format
from categories.models import Category

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BulkUploadProductAttributes(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Category.objects.values('id', 'category_name')
    serializer_class = UploadMasterDataSerializers

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
    queryset = Category.objects.values('id', 'category_name')
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