import logging
import csv
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import authentication
from rest_framework.generics import GenericAPIView

from categories.models import Category
from products.models import BulkUploadForProductAttributes
from .serializers import UploadMasterDataSerializers, DownloadMasterDataSerializers, CategoryImageSerializers, \
    ParentProductImageSerializers, ChildProductImageSerializers, DATA_TYPE_CHOICES, BrandImageSerializers, \
    CategoryListSerializers, DownloadProductVendorMappingSerializers, BulkProductVendorMappingSerializers, \
    BulkSlabProductPriceSerializers, BulkDiscountedProductPriceSerializers

from retailer_backend.utils import SmallOffsetPagination

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format, validate_bulk_data_format
from products.services import bulk_log_search, category_search


# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class CategoryListView(GenericAPIView):
    """
        Get Category List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Category.objects.values('id', 'category_name',)
    serializer_class = CategoryListSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = category_search(self.queryset, search_text)
        category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        msg = "" if category else "no category found"
        return get_response(msg, serializer.data, True)


class BulkCreateUpdateAttributesView(GenericAPIView):
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

            g)Create Child Product
            h)Create Parent Product
            i)Create Brand
            j)Create Category

            g)Update Child Product
            h)Update Parent Product
            i)Update Brand
            j)Update Category

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


class BulkChoiceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET BulkChoice List for Bulk Uploaded Data """

        info_logger.info("BulkChoice GET api called.")
        """ GET BulkChoice List """
        fields = ['upload_type', 'upload_type_name', ]
        data = {}
        for key, val in DATA_TYPE_CHOICES:
            data[key] = [dict(zip(fields, d)) for d in val]

        msg = ""
        return get_response(msg, data, True)


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


class ParentProductMultiImageUploadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ParentProductImageSerializers

    def post(self, request):
        """ POST API for Updating ParentProductImages """

        info_logger.info("ParentProductMultiPhotoUpload POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
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
            serializer.save(updated_by=request.user)
            info_logger.info("ChildProductMultiImageUploadView upload successfully")
            return get_response('', serializer.data)
        return get_response(serializer_error(serializer), False)


class CategoryMultiImageUploadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = CategoryImageSerializers

    def post(self, request):
        """ POST API for Updating Category Images """

        info_logger.info("CategoryMultiImageUploadView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("CategoryMultiImage upload successfully")
            return get_response('', serializer.data)
        return get_response(serializer_error(serializer), False)


class BrandMultiImageUploadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BrandImageSerializers

    def post(self, request):
        """ POST API for Updating BrandImages """

        info_logger.info("BrandMultiImageUploadView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("BrandMultiImageUploadView upload successfully")
            return get_response('', serializer.data)
        return get_response(serializer_error(serializer), False)


class CreateProductVendorMappingSampleView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = DownloadProductVendorMappingSerializers

    def post(self, request):
        """ POST API for Download Sample CreateProductVendorMapping """

        info_logger.info("CreateProductVendorMappingSample POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("CreateProductVendorMapping Downloaded successfully")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class CreateProductVendorMappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkProductVendorMappingSerializers

    def post(self, request):
        """ POST API for Create BulkProductVendorMapping """

        info_logger.info("BulkProductVendorMappingView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("BulkProductVendorMappingView upload successfully")
            return get_response('', serializer.data)
        return get_response(serializer_error(serializer), False)


class SlabProductPriceSampleCSV(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ Get API for Download sample product slab price CSV """

        info_logger.info("product slab price ExportAsCSV GET api called.")
        filename = "slab_product_price_sample_csv.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(["SKU", "Product Name", "Shop Id", "Shop Name", "MRP", "Slab 1 Qty", "Selling Price 1",
                         "Offer Price 1", "Offer Price 1 Start Date(dd-mm-yy)", "Offer Price 1 End Date(dd-mm-yy)",
                         "Slab 2 Qty", "Selling Price 2", "Offer Price 2", "Offer Price 2 Start Date(dd-mm-yy)",
                         "Offer Price 2 End Date(dd-mm-yy)"])
        writer.writerow(["BDCHNKDOV00000001", "Dove CREAM BAR 100G shop", "600",
                         "GFDN SERVICES PVT LTD (NOIDA) - 9319404555 - Rakesh Kumar - Service Partner", "47", "9", "46",
                         "45.5", "01-03-21", "30-04-21", "10", "45", "44.5", "01-03-21", "30-04-21"])
        info_logger.info("product slab price CSVExported successfully ")
        return HttpResponse(response, content_type='text/csv')


class DiscountedProductPriceSampleCSV(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ Get API for Download sample product slab price CSV """

        info_logger.info("product slab price ExportAsCSV GET api called.")
        filename = "discounted_product_price_sample_csv.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(["SKU", "Product Name", "Shop Id", "Shop Name", "selling price"])
        writer.writerow(["DRGRSNGDAW00000020", "Daawat Rozana Super, 5 KG", "600", "GFDN SERVICES PVT LTD (DELHI)",
                         "123.00"])
        info_logger.info("product slab price CSVExported successfully ")
        return HttpResponse(response, content_type='text/csv')


class CreateBulkSlabProductPriceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkSlabProductPriceSerializers

    def post(self, request):
        """ POST API for Create Bulk Slab Product Price"""

        info_logger.info("BulkSlabProductPriceView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            info_logger.info("BulkSlabProductPriceView upload successfully")
            return get_response("Slab Product Prices uploaded successfully !", True)
        return get_response(serializer_error(serializer), False)


class CreateBulkDiscountedProductPriceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BulkDiscountedProductPriceSerializers

    def post(self, request):
        """ POST API for Create Bulk Slab Product Price"""

        info_logger.info("BulkSlabProductPriceView POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            info_logger.info("BulkSlabProductPriceView upload successfully")
            return get_response("Slab Product Prices uploaded successfully !", True)
        return get_response(serializer_error(serializer), False)