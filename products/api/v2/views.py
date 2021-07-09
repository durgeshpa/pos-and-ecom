import logging
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
import csv
from rest_framework import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from products.models import BulkUploadForProductAttributes, ParentProduct, ProductHSN, ProductCapping, \
    ParentProductImage, ProductVendorMapping, Product, Tax, ProductSourceMapping, ProductPackingMapping, \
    ProductSourceMapping, Weight
from .serializers import UploadMasterDataSerializers, DownloadMasterDataSerializers, \
    ParentProductImageSerializers, ChildProductImageSerializers, \
    ParentProductBulkUploadSerializers, ChildProductBulkUploadSerializers, BulkProductTaxUpdateSerializers
from retailer_backend.utils import SmallOffsetPagination

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format, validate_bulk_data_format
from products.services import bulk_log_search

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ParentProductBulkCreateView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ParentProductBulkUploadSerializers

    def post(self, request, *args, **kwargs):
        """ POST API for Bulk Create Parent Product """

        info_logger.info("Parent Product Bulk Create POST api called.")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('parent product CSV uploaded successfully!', True)
        return get_response(serializer_error(serializer), False)


class ParentProductsDownloadSampleCSV(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        filename = "parent_products_sample.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(["name", "brand", "category", "hsn", "gst", "cess", "surcharge", "inner case size", "product type", "is_ptr_applicable", "ptr_type", "ptr_percent",
                         "is_ars_applicable", "max_inventory_in_days", "is_lead_time_applicable"])

        data = [["parent1", "Too Yumm", "Health Care, Beverages, Grocery & Staples", "123456", "18", "12", "100",
                 "10", "b2b", "yes", "Mark Up", "12", "yes", "2", "yes"], ["parent2", "Too Yumm",
                "Grocery & Staples", "123456", "18", "0", "100", "10", "b2c", "no", " ", "", "no", "2", "yes"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Parent Product Sample CSVExported successfully ")
        return HttpResponse(response, content_type='text/csv')


class ChildProductBulkCreateView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ChildProductBulkUploadSerializers

    def post(self, request, *args, **kwargs):
        """ POST API for Bulk Upload Child Product CSV """

        info_logger.info("Child Product Bulk Create POST api called.")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('child product CSV uploaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class ChildProductsDownloadSampleCSV(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        filename = "child_products_upload_sample.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(["Parent Product ID", "Reason for Child SKU", "Product Name", "Product EAN Code",
                         "Product MRP", "Weight Value", "Weight Unit", "Repackaging Type", "Map Source SKU",
                         'Raw Material Cost', 'Wastage Cost', 'Fumigation Cost', 'Label Printing Cost',
                         'Packing Labour Cost', 'Primary PM Cost', 'Secondary PM Cost', "Packing SKU",
                         "Packing Sku Weight (gm) Per Unit (Qty) Destination Sku"])
        data = [["PHEAMGI0001", "Default", "TestChild1", "abcdefgh", "50", "20", "Gram", "none"],
                ["PHEAMGI0001", "Default", "TestChild2", "abcdefgh", "50", "20", "Gram", "source"],
                ["PHEAMGI0001", "Default", "TestChild3", "abcdefgh", "50", "20", "Gram", "destination",
                 "SNGSNGGMF00000016, SNGSNGGMF00000016", "10.22", "2.33", "7", "4.33", "5.33", "10.22", "5.22",
                 "BPOBLKREG00000001", "10.00"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Child Product Sample CSVExported successfully ")
        return HttpResponse(response, content_type='text/csv')


class BulkUploadProductAttributes(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
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

    def delete(self, request):
        """ Delete Bulk Attribute """

        info_logger.info("Bulk Log DELETE api called.")
        if not request.data.get('bulk_product_attribute_ids'):
            return get_response('please provide bulk_product_attribute_id', False)
        try:
            for id in request.data.get('bulk_product_attribute_ids'):
                bulk_product_attribute = self.queryset.get(id=int(id))
                try:
                    bulk_product_attribute.delete()
                except:
                    return get_response(f'can not delete bulk_product_attribute {bulk_product_attribute.file}', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'{id} is invalid, please provide a valid bulk_product_attribute_id ', False)
        return get_response('bulk product attribute were deleted successfully!', True)

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


class BulkProductTaxGSTUpdateSampleCSV(APIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        filename = "bulk_product_tax_gst_update_sample.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(['parent_id', 'GST', 'Cess', 'Surcharge'])
        writer.writerow(['PHEATOY0006', 2, 12, 4])
        info_logger.info("bulk tax update Sample CSVExported successfully ")
        return HttpResponse(response, content_type='text/csv')


class BulkProductTaxUpdateView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkProductTaxUpdateSerializers

    def post(self, request):
        """ POST API for Updating BulkProductTaxGST """

        info_logger.info("BulkProductTaxUpdateView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("tax updated successfully")
            return get_response('tax updated successfully!', serializer.data)
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