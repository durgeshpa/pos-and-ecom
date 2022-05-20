import csv
import logging
from datetime import datetime

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.db.models import Q

from rest_auth import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from products.models import ParentProduct as ParentProducts, ProductHSN, ProductCapping as ProductCappings, \
    ProductVendorMapping, Product as ChildProduct, Tax, Weight, ProductPrice, ParentProduct, SuperStoreProductPrice
from categories.models import Category, B2cCategory
from brand.models import Brand, Vendor
from shops.models import Shop
from shops.services import shop_search, search_city, search_pincode
from retailer_backend.utils import SmallOffsetPagination
from addresses.models import Pincode, City

from .serializers import ParentProductSerializers, BrandSerializers, ParentProductExportAsCSVSerializers, \
    ActiveDeactiveSelectedParentProductSerializers, ProductHSNSerializers, WeightExportAsCSVSerializers, \
    ProductCappingSerializers, ProductVendorMappingSerializers, ChildProductSerializers, TaxSerializers, \
    CategorySerializers, B2cCategorySerializers, ProductSerializers, GetParentProductSerializers, \
    ActiveDeactiveSelectedChildProductSerializers, \
    ChildProductExportAsCSVSerializers, TaxCrudSerializers, TaxExportAsCSVSerializers, WeightSerializers, \
    ProductHSNCrudSerializers, HSNExportAsCSVSerializers, ProductPriceSerializers, CitySerializer, \
    ProductVendorMappingExportAsCSVSerializers, PinCodeSerializer, ShopsSerializer, \
    DisapproveSelectedProductPriceSerializers, ProductSlabPriceExportAsCSVSerializers, ImageProductSerializers, \
    DiscountChildProductSerializers, HSNExportAsCSVUploadSerializer, ParentProductApprovalSerializers, \
    SuperStoreProductPriceSerializers, SuperStoreProductPriceAsCSVUploadSerializer, \
    SuperStoreProductPriceDownloadSerializer
from brand.api.v1.serializers import VendorSerializers
from products.common_function import get_response, serializer_error, can_approve_product_tax
from products.common_validators import validate_id, validate_data_format, validate_data_format_without_json
from products.services import parent_product_search, child_product_search, product_hsn_search, tax_search, \
    category_search, brand_search, parent_product_name_search, vendor_search, product_vendor_search, \
    product_price_search

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BrandListView(GenericAPIView):
    """
        Get Brand List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.select_related('brand_parent').only('id', 'brand_name', 'brand_parent', )
    serializer_class = BrandSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = brand_search(self.queryset, search_text)
        brand = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(brand, many=True)
        msg = "" if brand else "no brand found"
        return get_response(msg, serializer.data, True)


class CategoryListView(GenericAPIView):
    """
        Get Category List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Category.objects.select_related('category_parent').only('id', 'category_name', 'category_parent', )
    serializer_class = CategorySerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = category_search(self.queryset, search_text)
        category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        msg = "" if category else "no category found"
        return get_response(msg, serializer.data, True)


class B2cCategoryListView(GenericAPIView):
    """
        Get B2c Category List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = B2cCategory.objects.select_related('category_parent').only('id', 'category_name', 'category_parent', )
    serializer_class = B2cCategorySerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = category_search(self.queryset, search_text)
        category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        msg = "" if category else "no b2c category found"
        return get_response(msg, serializer.data, True)


class ParentProductListView(GenericAPIView):
    """
        Get Parent List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ParentProducts.objects.values('id', 'name')
    serializer_class = GetParentProductSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = parent_product_name_search(self.queryset, search_text)
        product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product, many=True)
        msg = "" if product else "no parent product found"
        return get_response(msg, serializer.data, True)


class HSNListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ProductHSN.objects.values('id', 'product_hsn_code')
    serializer_class = ProductHSNSerializers

    def get(self, request):
        """ GET API for Product HSN List"""
        info_logger.info("Product HSN GET api called.")
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = product_hsn_search(self.queryset, search_text)
        product_hsn = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product_hsn, many=True)
        msg = "" if product_hsn else "no hsn found"
        return get_response(msg, serializer.data, True)


class TaxListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Tax.objects.values('id', 'tax_type', 'tax_percentage')
    serializer_class = TaxSerializers

    def get(self, request):
        """ GET Tax List """
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = tax_search(self.queryset, search_text)
        product_tax = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product_tax, many=True)
        msg = "" if product_tax else "no tax found"
        return get_response(msg, serializer.data, True)


class TaxView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Tax.objects.prefetch_related('tax_log', 'tax_log__updated_by') \
        .only('id', 'tax_name', 'tax_type', 'tax_percentage', 'tax_start_at', 'tax_end_at', 'status'). \
        order_by('-id')

    serializer_class = TaxCrudSerializers

    def get(self, request):
        """ GET API for Tax """
        tax_total_count = self.queryset.count()
        info_logger.info("Tax GET api called.")
        if request.GET.get('id'):
            """ Get Tax for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_tax = id_validation['data']
        else:
            """ GET Tax List """
            self.queryset = self.search_filter_product_tax()
            tax_total_count = self.queryset.count()
            product_tax = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_tax, many=True)
        msg = f"total count {tax_total_count}" if product_tax else "no tax found"
        return get_response(msg, serializer.data, True)

    def post(self, request, *args, **kwargs):
        """ POST API for Tax Creation """

        info_logger.info("Tax POST api called.")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("product Tax created successfully ")
            return get_response('product Tax created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Tax Updation """

        info_logger.info("Tax PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update tax', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        tax_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=tax_instance, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Tax Updated Successfully.")
            return get_response('tax updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Tax """

        info_logger.info("Tax DELETE api called.")
        if not request.data.get('tax_ids'):
            return get_response('please select tax', False)
        try:
            for id in request.data.get('tax_ids'):
                tax_id = self.queryset.get(id=int(id))
                try:
                    tax_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(), 'tax_id': tax_id}
                    info_logger.info("tax deleted info ", dict_data)
                except Exception as er:
                    return get_response(f'You can not delete tax {tax_id.tax_name}, '
                                        f'because this tax is mapped with product', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid tax id {id}', False)
        return get_response('tax were deleted successfully!', True)

    def search_filter_product_tax(self):
        search_text = self.request.GET.get('search_text')
        status = self.request.GET.get('status')
        # search using tax_name and tax_type based on criteria that matches
        if search_text:
            self.queryset = tax_search(self.queryset, search_text.strip())
        if status is not None:
            self.queryset = self.queryset.filter(status=status)
        return self.queryset


class TaxExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = TaxExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected tax CSV """

        info_logger.info("Tax ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Tax CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ParentProductView(GenericAPIView):
    """
        Get Parent Product
        Add Parent Product
        Search Parent Product
        List Parent Product
        Update Parent Product
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ParentProducts.objects.select_related('parent_brand', 'product_hsn', 'updated_by').prefetch_related(
        'parent_product_pro_category', 'parent_product_pro_b2c_category', 'parent_product_pro_tax',
        'product_parent_product', 'parent_product_log',
        'product_parent_product__product_pro_image', 'parent_product_pro_category__category',
        'product_parent_product__product_vendor_mapping', 'parent_product_pro_tax__tax', 'parent_product_pro_image',
        'parent_product_log__updated_by', 'product_parent_product__product_vendor_mapping__vendor', ) \
        .only('id', 'parent_id', 'name', 'inner_case_size', 'product_type', 'is_ptr_applicable', 'updated_by',
              'ptr_percent', 'ptr_type', 'status', 'parent_brand__brand_name', 'parent_brand__brand_code',
              'updated_at', 'product_hsn__product_hsn_code', 'is_lead_time_applicable', 'is_ars_applicable',
              'max_inventory', 'brand_case_size', 'discounted_life_percent', 'tax_status', 'tax_remark').order_by('-id')
    serializer_class = ParentProductSerializers

    def get(self, request):
        """ GET API for Parent Product with Image Category & Tax """

        info_logger.info("Parent Product GET api called.")
        product_total_count = self.queryset.count()
        active_product_total_count = self.queryset.filter(status=True).count()
        if request.GET.get('id'):
            """ Get Parent Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            parent_product = id_validation['data']
        else:
            """ GET Parent Product List """
            self.queryset = self.search_filter_parent_product()
            product_total_count = self.queryset.count()
            active_product_total_count = self.queryset.filter(status=True).count()
            parent_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(parent_product, many=True)
        msg = f"TOTAL PARENT SKUS {product_total_count}  TOTAL ACTIVE PARENT SKUS {active_product_total_count}" \
            if parent_product else "no parent product found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Parent Product Creation with Image Category & Tax """

        info_logger.info("Parent Product POST api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Parent Product Created Successfully.")
            return get_response('Parent product created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Parent Product Updation with Image Category & Tax """

        info_logger.info("Parent Product PUT api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update parent product', False)

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

    def delete(self, request):
        """ Delete Parent Product with image """

        info_logger.info("Parent Product DELETE api called.")
        if not request.data.get('parent_product_id'):
            return get_response('please select parent product', False)
        try:
            for id in request.data.get('parent_product_id'):
                parent_product_id = self.queryset.get(id=int(id))
                try:
                    parent_product_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'parent_product_id': parent_product_id}
                    info_logger.info("parent_product deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete parent product {parent_product_id.name}, '
                                        f'because this parent product is mapped with child product', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid parent_product_id {id}', False)
        return get_response('parent product were deleted successfully!', True)

    def search_filter_parent_product(self):

        category = self.request.GET.get('category')
        b2c_category = self.request.GET.get('b2c_category')
        brand = self.request.GET.get('brand')
        product_status = self.request.GET.get('status')
        tax_status = self.request.GET.get('tax_status')
        search_text = self.request.GET.get('search_text')
        product_type = self.request.GET.get('product_type')

        # search using parent_id, name & category_name based on criteria that matches
        if search_text:
            self.queryset = parent_product_search(self.queryset, search_text.strip())
        # filter using brand_name, category & product_status exact match
        if brand is not None:
            self.queryset = self.queryset.filter(parent_brand__id=brand)
        if product_status is not None:
            self.queryset = self.queryset.filter(status=product_status)
        if tax_status is not None:
            self.queryset = self.queryset.filter(tax_status=tax_status)
        if product_type is not None:
            self.queryset = self.queryset.filter(product_type=product_type)
        if category is not None:
            self.queryset = self.queryset.filter(
                parent_product_pro_category__category__id=category)
        if b2c_category is not None:
            self.queryset = self.queryset.filter(
                parent_product_pro_b2c_category__category_id=b2c_category
            )
        return self.queryset.distinct()


class SourceProductMappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.filter(repackaging_type='source')
    serializer_class = ProductSerializers

    def get(self, request):
        if request.GET.get('id'):
            """ Get Source Product Mapping for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_map = id_validation['data']
        else:
            product_map = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product_map, many=True)
        msg = "" if product_map else "no product mapping found"
        return get_response(msg, serializer.data, True)


class ProductPackingMappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.filter(repackaging_type='packing_material')
    serializer_class = ProductSerializers

    def get(self, request):
        if request.GET.get('id'):
            """ Get product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            pack_mat_product = id_validation['data']
        else:
            pack_mat_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(pack_mat_product, many=True)
        msg = "" if pack_mat_product else "no product package mapping found"
        return get_response(msg, serializer.data, True)


class SiblingProductView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ChildProduct.objects.select_related('parent_product', 'updated_by', 'created_by') \
        .prefetch_related('product_pro_image', 'product_vendor_mapping', 'parent_product__parent_product_pro_image',
                          'parent_product__product_parent_product__product_pro_image',
                          'child_product_log', 'child_product_log__updated_by', 'destination_product_pro',
                          'parent_product__parent_product_pro_category', 'destination_product_pro__source_sku',
                          'parent_product__parent_product_pro_category__category', 'packing_product_rt',
                          'destination_product_repackaging', 'packing_product_rt__packing_sku',
                          'parent_product__product_parent_product__product_vendor_mapping',
                          'parent_product__parent_product_log', 'parent_product__parent_product_log__updated_by',
                          'parent_product__product_parent_product__product_vendor_mapping__vendor', 'product_pro_tax',
                          'parent_product__product_hsn', 'product_vendor_mapping__vendor', 'product_pro_tax__tax',
                          'parent_product__product_parent_product__product_vendor_mapping',
                          'parent_product__parent_brand', 'parent_product__parent_product_pro_tax',
                          'parent_product__parent_product_pro_tax__tax', ).order_by('-id')

    serializer_class = ChildProductSerializers

    def get(self, request):
        """"GET API for Sibling Product with Image Category & Tax """
        if request.GET.get('id'):
            """ Get Child Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            child_product = id_validation['data']

        serializer = self.serializer_class(child_product, many=True)
        parent_id = serializer.data[0]["parent_product"]["parent_id"]
        if parent_id:
            self.queryset = self.queryset.filter(parent_product__parent_id=parent_id).exclude(id=request.GET.get('id'))
            sib_pro_total_count = self.queryset.count()
            sibling_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
            serializer = self.serializer_class(sibling_product, many=True)
        msg = f"TOTAL SIBLING PRODUCT :: {sib_pro_total_count}" if sibling_product else "No sibling product found"
        return get_response(msg, serializer.data, True)


def api_response(msg, data=None, status_code=status.HTTP_406_NOT_ACCEPTABLE, success=False, extra_params=None):
    ret = {"is_success": success, "message": msg, "response_data": data}
    if extra_params:
        ret.update(extra_params)
    return Response(ret, status=status_code)


class ProductDetails(GenericAPIView):
    """
    retailer product details with parent product discriptions .....
    """

    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ChildProductSerializers

    def get(self, request):
        '''get superstore product details ....'''
        id = request.GET.get('id')
        serializer = ChildProduct.objects.filter(id=id)
        serializer = self.serializer_class(serializer, many=True)
        return api_response('products information',serializer.data,status.HTTP_200_OK, True)


class ChildProductView(GenericAPIView):
    """
        Get Child Product
        Add Child Product
        Search Child Product
        List Child Product
        Update Child Product
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ChildProduct.objects.select_related('parent_product', 'updated_by', 'created_by') \
        .prefetch_related('product_pro_image', 'product_vendor_mapping', 'parent_product__parent_product_pro_image',
                          'parent_product__product_parent_product__product_pro_image',
                          'child_product_log', 'child_product_log__updated_by', 'destination_product_pro',
                          'parent_product__parent_product_pro_category', 'destination_product_pro__source_sku',
                          'parent_product__parent_product_pro_category__category', 'packing_product_rt',
                          'destination_product_repackaging', 'packing_product_rt__packing_sku',
                          'parent_product__product_parent_product__product_vendor_mapping',
                          'parent_product__parent_product_log', 'parent_product__parent_product_log__updated_by',
                          'parent_product__product_parent_product__product_vendor_mapping__vendor', 'product_pro_tax',
                          'parent_product__product_hsn', 'product_vendor_mapping__vendor', 'product_pro_tax__tax',
                          'parent_product__product_parent_product__product_vendor_mapping',
                          'parent_product__parent_brand', 'parent_product__parent_product_pro_tax',
                          'parent_product__parent_product_pro_tax__tax', ).order_by('-id')

    serializer_class = ChildProductSerializers

    def get(self, request):
        """ GET API for Child Product with Image Category & Tax """

        if not request.GET.get('product_type'):
            return get_response('product_type is mandatory', False)
        elif int(request.GET.get('product_type')) not in [0, 1]:
            return get_response('please select valid product_type')
        self.queryset = self.queryset.filter(product_type=int(request.GET.get('product_type')))

        ch_product_total_count = self.queryset.count()
        ch_active_product_total_count = self.queryset.filter(status='active').count()
        info_logger.info("Child Product GET api called.")
        if request.GET.get('id'):
            """ Get Child Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            child_product = id_validation['data']
        else:
            """ GET Child Product List """
            self.queryset = self.search_filter_product_list()
            ch_product_total_count = self.queryset.count()
            ch_active_product_total_count = self.queryset.filter(status='active').count()
            child_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(child_product, many=True)

        msg = f"TOTAL CHILD SKUS {ch_product_total_count}  TOTAL ACTIVE CHILD SKUS " \
              f"{ch_active_product_total_count}" if child_product else "no child product found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Child Product """

        info_logger.info("Child Product POST api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("Child Product Created Successfully.")
            return get_response('child product created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Child Product Updation with Image """

        info_logger.info("Child Product PUT api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update child product', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        child_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=child_product_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Child Product Updated Successfully.")
            return get_response('child product updated Successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Child Product with image """

        info_logger.info("Child Product DELETE api called.")
        if not request.data.get('child_product_id'):
            return get_response('please select child product', False)
        try:
            for id in request.data.get('child_product_id'):
                child_product_id = self.queryset.get(id=int(id))
                try:
                    child_product_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'child_product_id': child_product_id}
                    info_logger.info("child_product deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete child product {child_product_id.product_name}, '
                                        f'because this child product is mapped with product price', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid child_product_id {id}', False)
        return get_response('child product were deleted successfully!', True)

    def search_filter_product_list(self):

        category = self.request.GET.get('category')
        b2c_category = self.request.GET.get('b2c_category')
        brand = self.request.GET.get('brand')
        product_status = self.request.GET.get('status')
        parent_product_id = self.request.GET.get('parent_product_id')
        search_text = self.request.GET.get('search_text')

        # search using product_name & id based on criteria that matches
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text.strip())
        # filter using brand_name, category & product_status exact match
        if brand is not None:
            self.queryset = self.queryset.filter(parent_product__parent_brand__id=brand)
        if parent_product_id is not None:
            self.queryset = self.queryset.filter(parent_product=parent_product_id)
        if product_status is not None:
            self.queryset = self.queryset.filter(status=product_status)
        if category is not None:
            self.queryset = self.queryset.filter(
                parent_product__parent_product_pro_category__category__id=category)
        if b2c_category is not None:
            self.queryset = self.queryset.filter(
                parent_product__parent_product_pro_b2c_category__category__id=b2c_category)
        
        return self.queryset


class ActiveDeactiveSelectedParentProductView(UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    parent_product_list = ParentProducts.objects.values('id', )
    serializer_class = ActiveDeactiveSelectedParentProductSerializers

    def put(self, request):
        """ PUT API for Activate or Deactivate Selected Parent Product """

        info_logger.info("Parent Product ActiveDeactivateSelectedProduct PUT api called.")
        serializer = self.serializer_class(instance=self.parent_product_list.filter(
            id__in=request.data['parent_product_id_list']), data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('parent product updated successfully!', True)
        return get_response(serializer_error(serializer), None)


class ActiveDeactiveSelectedChildProductView(UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    child_product_list = ChildProduct.objects.values('id', )
    serializer_class = ActiveDeactiveSelectedChildProductSerializers

    def put(self, request):
        """ PUT API for Activate or Deactivate Selected Child Product """

        info_logger.info("Child Product ActiveDeactivateSelectedProduct PUT api called.")
        serializer = self.serializer_class(instance=self.child_product_list.filter(
            id__in=request.data['child_product_id_list']), data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('child product updated successfully!', True)
        return get_response(serializer_error(serializer), None)


class ProductCappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ProductCappings.objects.select_related('product', 'seller_shop').order_by('-id')
    serializer_class = ProductCappingSerializers
    """
        Get Product Capping
        Add Product Capping
        Search Product Capping
        List Product Capping
        Update Product Capping
    """

    def get(self, request):
        """ GET API for Product Capping List"""

        info_logger.info("Product Capping GET api called.")
        if request.GET.get('id'):
            """ Get Parent Product when id is given in params """
            # validations for input id
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_capping = id_validation['data']
        else:
            """ GET API to get Parent Product List """
            self.queryset = self.get_product_capping()
            product_capping = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_capping, many=True)
        return get_response('Product Capping List', serializer.data, True)

    def post(self, request):

        """ Post API for Product Capping Creation """

        info_logger.info("Product Capping POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('Product Capping Created', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):

        """ Put API for Product Capping Updation """

        info_logger.info("Product Capping PUT api called.")
        if not request.data.get('id'):
            return get_response('please provide id to update product capping', False)
        cap_product_id = int(request.data.get('id'))
        try:
            id_instance = self.queryset.get(id=cap_product_id)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'id {cap_product_id} not found', False)

        serializer = self.serializer_class(instance=id_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return get_response('product capping updated successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):

        """ Delete Product Capping """

        info_logger.info("Product Capping DELETE api called.")
        if not request.data.get('product_capping_id'):
            return get_response('please provide a product_capping_id', False)
        try:
            with transaction.atomic():
                for cap_product_id in request.data.get('product_capping_id'):
                    product_capping_id = self.queryset.get(id=int(cap_product_id))
                    product_capping_id.delete()
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'id {cap_product_id} not found', False)
        return get_response('product capping were deleted successfully!', [], True)

    def get_product_capping(self):
        product_sku = self.request.GET.get('product_sku')
        product_name = self.request.GET.get('product_name')
        product_capping_status = self.request.GET.get('status')
        seller_shop = self.request.GET.get('seller_shop')

        # filter using product_sku, seller_shop, product_capping_status & product_name
        if product_sku is not None:
            self.queryset = self.queryset.filter(product__product_sku__icontains=product_sku)
        if seller_shop is not None:
            self.queryset = self.queryset.filter(seller_shop_id=seller_shop)
        if product_capping_status is not None:
            self.queryset = self.queryset.filter(status=product_capping_status)
        if product_name is not None:
            self.queryset = self.queryset.filter(
                product_id=product_name)

        return self.queryset


class ProductHSNView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ProductHSN.objects.prefetch_related('hsn_log', 'hsn_log__updated_by')\
        .only('id', 'product_hsn_code').order_by('-id')
    serializer_class = ProductHSNCrudSerializers

    def get(self, request):
        """ GET API for Product HSN """

        info_logger.info("Product HSN GET api called.")
        ch_hsn_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Product HSN for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_hsn = id_validation['data']
        else:
            """ GET Product HSN List """
            self.queryset = self.search_filter_product_hsn()
            ch_hsn_total_count = self.queryset.count()
            product_hsn = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_hsn, many=True)
        msg = f"total count {ch_hsn_total_count}" if product_hsn else "no hsn found"
        return get_response(msg, serializer.data)

    def post(self, request, *args, **kwargs):
        """ POST API for ProductHSN Creation """

        info_logger.info("ProductHSN POST api called.")
        serializer = self.get_serializer(data=request.data,
                                         context={"request": self.request, "user": self.request.user})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("product HSN created successfully ")
            return get_response('product HSN created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for ProductHSN Updation """

        info_logger.info("HSN PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update hsn', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        hsn_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=hsn_instance, data=request.data,
                                           context={"request": self.request, "user": self.request.user})
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("HSN Updated Successfully.")
            return get_response('hsn updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    # @transaction.atomic
    def delete(self, request):
        """ Delete Product HSN  """

        info_logger.info("Product HSN DELETE api called.")
        if not request.data.get('hsn_ids'):
            return get_response('please select hsn', False)
        try:
            for h_id in request.data.get('hsn_ids'):
                hsn_id = self.queryset.get(id=int(h_id))
                try:
                    hsn_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'hsn_id': hsn_id}
                    info_logger.info("hsn deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete hsn {hsn_id.product_hsn_code}, '
                                        f'because this hsn is mapped with product', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid hsn id {h_id}', False)
        return get_response('hsn were deleted successfully!', True)

    def search_filter_product_hsn(self):
        search_text = self.request.GET.get('search_text')
        product_hsn_cd = self.request.GET.get('product_hsn_code')
        # search using product_hsn_code based on criteria that matches
        if search_text:
            self.queryset = product_hsn_search(self.queryset, search_text)
        if product_hsn_cd is not None:
            self.queryset = self.queryset.filter(id=int(product_hsn_cd))

        return self.queryset


class WeightView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Weight.objects.prefetch_related('weight_log', 'weight_log__updated_by') \
        .only('id', 'weight_value', 'weight_unit', 'status', 'weight_name').order_by('-id')

    serializer_class = WeightSerializers

    def get(self, request):
        """ GET API for Weight """

        info_logger.info("Weight GET api called.")
        weight_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Weight for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            weight = id_validation['data']
        else:
            """ GET Weight List """
            weight = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(weight, many=True)
        msg = f"total count {weight_total_count}" if weight else "no weight found"
        return get_response(msg, serializer.data, True)

    def post(self, request, *args, **kwargs):
        """ POST API for Weight Creation """

        info_logger.info("Weight POST api called.")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            info_logger.info("weight created successfully ")
            return get_response('weight created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Weight Updation """

        info_logger.info("Weight PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update weight', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        tax_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=tax_instance, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Weight Updated Successfully.")
            return get_response('weight updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Weight """

        info_logger.info("Weight DELETE api called.")
        if not request.data.get('weight_ids'):
            return get_response('please select weight', False)
        try:
            for w_id in request.data.get('weight_ids'):
                weight_id = self.queryset.get(id=int(w_id))
                try:
                    weight_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'weight_id': weight_id}
                    info_logger.info("weight deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete weight {weight_id.weight_name}, '
                                        f'because this weight is mapped with product', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid weight id {w_id}', False)
        return get_response('weight were deleted successfully!', True)


class WeightExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = WeightExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Weight CSV """

        info_logger.info("Weight ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Weight CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class HSNExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = HSNExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected HSN CSV """

        info_logger.info("HSN ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("HSN CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class HSNExportAsCSVSampleDownloadView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ Get API for Download sample TAX with HSN CSV """

        info_logger.info("HSNExportAsCSVSampleDownloadView GET api called.")
        filename = "hsn_tax_sample_csv.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(["product_hsn_code", "gst_rate_1", "gst_rate_2", "gst_rate_3",
                         "cess_rate_1", "cess_rate_2", "cess_rate_3"])
        writer.writerow([8013210, 5, 12, 18, 20.89, 3, 5.55])
        info_logger.info("HSN Tax CSVExported successfully ")
        return HttpResponse(response, content_type='text/csv')


class HSNExportAsCSVUploadView(GenericAPIView):
    """
    This class is used to upload csv file for TAX with HSN
    """
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = HSNExportAsCSVUploadSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'user': self.request.user})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)


class ChildProductExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ChildProductExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Parent Product CSV with Image Category & Tax """

        info_logger.info("Parent Product ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Parent Product CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ParentProductExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ParentProductExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Parent Product CSV with Image Category & Tax """

        info_logger.info("Parent Product ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Parent Product CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ActiveChildProductListView(GenericAPIView):
    """
        Get Child List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.filter(status="active").values('id', 'product_name', 'product_sku', 'product_mrp')
    serializer_class = ProductSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text)
        product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product, many=True)
        msg = "" if product else "no child product found"
        return get_response(msg, serializer.data, True)


class VendorListView(GenericAPIView):
    """
        Get Vendor List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Vendor.objects.values('id', 'vendor_name', 'mobile')
    serializer_class = VendorSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = vendor_search(self.queryset, search_text)
        vendor = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(vendor, many=True)
        msg = "" if vendor else "no vendor found"
        return get_response(msg, serializer.data, True)


class ChildProductListView(GenericAPIView):
    """
        Get Child List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.filter(repackaging_type__in=['none', 'source', 'destination']) \
        .values('id', 'product_name', 'product_sku', 'product_mrp')
    serializer_class = ProductSerializers

    def get(self, request):
        if not request.GET.get('product_type'):
            return get_response('product_type is mandatory', False)
        elif int(request.GET.get('product_type')) not in [0, 1]:
            return get_response('please select valid product_type')
        self.queryset = self.queryset.filter(product_type=int(request.GET.get('product_type')))

        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text)
        product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product, many=True)
        msg = "" if product else "no child product found"
        return get_response(msg, serializer.data, True)


class SellerShopListView(GenericAPIView):
    """
        Get SellerShop List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.select_related('shop_owner', 'shop_type', 'shop_type__shop_sub_type', ) \
        .filter(shop_type__shop_type__in=['sp', ]) \
        .only('id', 'shop_name', 'status', 'shop_type__shop_type', 'shop_type__shop_sub_type__retailer_type_name',
              'shop_owner__first_name', 'shop_owner__last_name', 'shop_owner__phone_number', )
    serializer_class = ShopsSerializer

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)
        vendor = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(vendor, many=True)
        msg = "" if vendor else "no seller shop found"
        return get_response(msg, serializer.data, True)


class BuyerShopListView(GenericAPIView):
    """
        Get BuyerShop List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Shop.objects.filter(shop_type__shop_type__in=['r', 'f'])
    serializer_class = ShopsSerializer

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = shop_search(self.queryset, search_text)
        vendor = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(vendor, many=True)
        msg = "" if vendor else "no buyer shop found"
        return get_response(msg, serializer.data, True)


class CityListView(GenericAPIView):
    """
        Get City List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = City.objects.only('id', 'city_name')
    serializer_class = CitySerializer

    def get(self, request):
        """ GET API for City """
        info_logger.info("City GET api called.")
        shop_id = self.request.GET.get('shop_id', None)
        if shop_id:
            self.queryset = self.queryset.filter(city_address__shop_name__id=shop_id).distinct('id')
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = search_city(self.queryset, search_text)
        city_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(city_data, many=True)
        msg = "" if city_data else "no city found"
        return get_response(msg, serializer.data, True)


class PinCodeListView(GenericAPIView):
    """
        Get Pincode List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Pincode.objects.only('id', 'pincode')
    serializer_class = PinCodeSerializer

    def get(self, request):
        """ GET API for PinCode """
        info_logger.info("PinCode GET api called.")
        shop_id = self.request.GET.get('shop_id', None)
        if shop_id:
            self.queryset = self.queryset.filter(pincode_address__shop_name__id=shop_id).distinct('pincode')
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = search_pincode(self.queryset, search_text)
        pin_code_data = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(pin_code_data, many=True)
        msg = "" if pin_code_data else "no pincode found"
        return get_response(msg, serializer.data, True)


class ProductStatusListView(GenericAPIView):
    """
        Get Product Status List
    """
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET Choice List for Product Status """

        info_logger.info("Product Status GET api called.")
        """ GET Status Choice List """
        fields = ['product_status', 'status', ]
        data = [dict(zip(fields, d)) for d in ChildProduct.STATUS_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ProductPriceStatusListView(GenericAPIView):
    """
        Get ProductPrice Status List
    """
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET Choice List for ProductPrice Status """

        info_logger.info("ProductPrice Status GET api called.")
        """ GET Status Choice List """
        fields = ['approval_status', 'approval_status_value']
        data = [dict(zip(fields, d)) for d in ProductPrice.APPROVAL_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ProductVendorMappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ProductVendorMapping.objects.select_related('vendor', 'product').order_by('-id')
    serializer_class = ProductVendorMappingSerializers

    def get(self, request):
        """ GET API for Product Vendor Mapping """

        info_logger.info("Product Vendor Mapping GET api called.")
        pro_vendor_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Product Vendor Mapping for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_vendor_map = id_validation['data']
        else:
            """ GET Product Vendor Mapping  List """
            self.queryset = self.search_filter_product_vendor_map()
            pro_vendor_count = self.queryset.count()
            product_vendor_map = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        msg = f"total count {pro_vendor_count}" if product_vendor_map else "no product vendor mapping found"
        serializer = self.serializer_class(product_vendor_map, many=True)
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Product Vendor Mapping """

        info_logger.info("Product Vendor Mapping POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('product vendor mapping created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Product Vendor Mapping Updation """

        info_logger.info("Product Vendor Mapping PUT api called.")
        if not request.data.get('id'):
            return get_response('please provide id to update product vendor mapping', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data.get('id')))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        product_vendor_map_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=product_vendor_map_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('product vendor mapping updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_product_vendor_map(self):

        vendor_id = self.request.GET.get('vendor_id')
        product_id = self.request.GET.get('product_id')
        product_status = self.request.GET.get('product_status')
        status = self.request.GET.get('status')
        search_text = self.request.GET.get('search_text')
        # search using tax_name and tax_type based on criteria that matches
        if search_text:
            self.queryset = product_vendor_search(self.queryset, search_text.strip())

        # filter using vendor_id, product_id, product_status & status exact match
        if product_id is not None:
            self.queryset = self.queryset.filter(product_id=product_id)
        if vendor_id is not None:
            self.queryset = self.queryset.filter(vendor_id=vendor_id)
        if status is not None:
            self.queryset = self.queryset.filter(status=status)
        if product_status is not None:
            self.queryset = self.queryset.filter(product__status=product_status)
        return self.queryset

    def delete(self, request):
        """ Delete Product Vendor Mapping """

        info_logger.info("Product Vendor Mapping DELETE api called.")
        if not request.data.get('product_vendor_map_ids'):
            return get_response('please select product vendor mapping', False)
        try:
            for id in request.data.get('product_vendor_map_ids'):
                product_vendor_map_id = self.queryset.get(id=int(id))
                try:
                    product_vendor_map_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'product_vendor_map_id': product_vendor_map_id}
                    info_logger.info("product_vendor_mapping deleted info ", dict_data)
                except Exception as er:
                    return get_response(f'You can not delete product vendor mapping {product_vendor_map_id}, '
                                        f'because this product vendor mapping is getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid product vendor mapping  id {id}', False)
        return get_response('product vendor mapping were deleted successfully!', True)


class ProductVendorMappingExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ProductVendorMappingExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected product vendor mapping CSV """

        info_logger.info("product vendor mapping ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("product vendor mapping CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class ProductSlabPriceExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = ProductSlabPriceExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected product slab price CSV """

        info_logger.info("product slab price ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("product slab price CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)


class DisapproveSelectedProductPriceView(UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    product_price_list = ProductPrice.objects.values('id', )
    serializer_class = DisapproveSelectedProductPriceSerializers

    def put(self, request):
        """ PUT API to Disapproved Selected Slap Product Price """

        info_logger.info("Product Price Disapproved PUT api called.")
        serializer = self.serializer_class(instance=self.product_price_list.filter(
            id__in=request.data['product_price_id_list']), data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return get_response('Product price disapproved successfully!', True)
        return get_response(serializer_error(serializer), None)


class SlabProductPriceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    queryset = ProductPrice.objects.select_related('product', 'seller_shop', 'buyer_shop', 'city', 'pincode', ) \
        .prefetch_related('price_slabs', 'product__parent_product', 'product__product_ref', 'seller_shop__shop_type',
                          'buyer_shop__shop_type', 'buyer_shop__shop_owner', 'seller_shop__shop_owner'). \
        only('id', 'product', 'mrp', 'seller_shop', 'buyer_shop', 'city', 'pincode', 'approval_status', ).order_by(
        '-id')
    serializer_class = ProductPriceSerializers

    def get(self, request):
        """ GET API for Product Price """

        info_logger.info("Product Price GET api called.")

        if not request.GET.get('product_type'):
            return get_response('product_type is mandatory', False)
        elif int(request.GET.get('product_type')) not in [0, 1]:
            return get_response('please select valid product_type')

        self.queryset = self.queryset.filter(
            id__in=self.queryset.filter(price_slabs__isnull=False, product__product_type=
            int(request.GET.get('product_type'))).values_list('pk', flat=True))
        if not (request.user.is_superuser or request.user.has_perm('products.change_productprice')):
            self.queryset = self.queryset.filter(Q(seller_shop__related_users=request.user) |
                                                 Q(seller_shop__shop_owner=request.user)).distinct()

        slab_pro_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Product Price for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_slab_price = id_validation['data']
        else:
            """ GET Product Price  List """
            self.queryset = self.search_filter_product_price()
            slab_pro_count = self.queryset.count()
            product_slab_price = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        msg = f"total count {slab_pro_count}" if product_slab_price else "no product price found"
        serializer = self.serializer_class(product_slab_price, many=True)
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Product Price """

        info_logger.info("Product Price POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('product price created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_product_price(self):

        seller_shop_id = self.request.GET.get('seller_shop_id')
        product_id = self.request.GET.get('product_id')
        product_sku = self.request.GET.get('product_sku')
        category_id = self.request.GET.get('category_id')
        approval_status = self.request.GET.get('approval_status')
        mrp = self.request.GET.get('mrp')
        search_text = self.request.GET.get('search_text')

        # search using product name and product sku based on criteria that matches
        if search_text:
            self.queryset = product_price_search(self.queryset, search_text.strip())

        # filter using seller_shop_id, product_id, product_status, mrp & status exact match
        if product_id is not None:
            self.queryset = self.queryset.filter(product_id=product_id)
        if category_id is not None:
            self.queryset = self.queryset.filter(product__parent_product__parent_product_pro_category__category_id=
                                                 category_id)
        if product_sku is not None:
            self.queryset = self.queryset.filter(product__product_sku__icontains=product_sku)
        if seller_shop_id is not None:
            self.queryset = self.queryset.filter(seller_shop_id=seller_shop_id)
        if approval_status is not None:
            self.queryset = self.queryset.filter(approval_status=int(approval_status))
        if mrp is not None:
            self.queryset = self.queryset.filter(mrp__icontains=mrp)
        return self.queryset

    def delete(self, request):
        """ Delete Product Price """

        info_logger.info("Product Price DELETE api called.")
        if not request.data.get('product_price_ids'):
            return get_response('please select product price', False)
        try:
            for id in request.data.get('product_price_ids'):
                product_price_id = self.queryset.get(id=int(id))
                try:
                    product_price_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'product_price_id': product_price_id}
                    info_logger.info("product price deleted info ", dict_data)
                except Exception as er:
                    return get_response(f'You can not delete product price {product_price_id}, '
                                        f'because this product price is getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid product price id {id}', False)
        return get_response('product price were deleted successfully!', True)


class ProductListView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.prefetch_related('product_pro_image', ).order_by('-id')

    serializer_class = ImageProductSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text)
        child_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(child_product, many=True)
        msg = "" if child_product else "no product found"
        return get_response(msg, serializer.data, True)


class DiscountProductListForManualPriceView(GenericAPIView):
    """
        Get Discount Child List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.filter(product_type=ChildProduct.PRODUCT_TYPE_CHOICE.DISCOUNTED,
                                           is_manual_price_update=True) \
        .values('id', 'product_name', 'product_sku', 'product_mrp')
    serializer_class = ProductSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text)
        product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product, many=True)
        msg = "" if product else "no discounted product found"
        return get_response(msg, serializer.data, True)


class DiscountProductView(GenericAPIView):
    """
        Get Discount Child List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ChildProduct.objects.filter(product_type=ChildProduct.PRODUCT_TYPE_CHOICE.DISCOUNTED). \
        select_related('parent_product', 'updated_by') \
        .prefetch_related('product_pro_image', 'product_vendor_mapping', 'parent_product__parent_product_pro_image',
                          'parent_product__product_parent_product__product_pro_image', 'child_product_log',
                          'child_product_log__updated_by', 'parent_product__parent_product_pro_category',
                          'parent_product__parent_product_pro_category__category',
                          'parent_product__product_parent_product__product_vendor_mapping',
                          'parent_product__parent_product_log', 'parent_product__parent_product_log__updated_by',
                          'parent_product__product_parent_product__product_vendor_mapping__vendor', 'product_pro_tax',
                          'parent_product__product_hsn', 'product_vendor_mapping__vendor', 'product_pro_tax__tax',
                          'parent_product__product_parent_product__product_vendor_mapping',
                          'parent_product__parent_brand', 'parent_product__parent_product_pro_tax',
                          'parent_product__parent_product_pro_tax__tax', ).order_by('-id')

    serializer_class = DiscountChildProductSerializers

    def get(self, request):
        """ GET API for Discount Child Product with Image Category & Tax """

        d_ch_product_total_count = self.queryset.count()
        info_logger.info("Discount Child Product GET api called.")
        if request.GET.get('id'):
            """ Get Discount Child Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            child_product = id_validation['data']
        else:
            """ GET Discount Child Product List """
            self.queryset = self.search_filter_product_list()
            d_ch_product_total_count = self.queryset.count()
            child_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(child_product, many=True)

        msg = f"total count {d_ch_product_total_count}" if child_product else "no discount child product found"
        return get_response(msg, serializer.data, True)

    def put(self, request):
        """ PUT API for Discount Child Product Updation with Image """

        info_logger.info("Discount Child Product PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update discount product', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])

        child_product_instance = id_instance['data'].last()
        serializer = self.serializer_class(instance=child_product_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Discount Child Product Updated Successfully.")
            return get_response('discount child product updated Successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_product_list(self):

        parent_product_id = self.request.GET.get('parent_product_id')
        search_text = self.request.GET.get('search_text')

        # search using product_name & id based on criteria that matches
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text.strip())

        # filter using parent_product_id exact match
        if parent_product_id is not None:
            self.queryset = self.queryset.filter(parent_product=parent_product_id)
        return self.queryset


class ParentProductsTaxStatusChoicesView(GenericAPIView):
    """
        Get Parent Products Tax Status Choices List
    """
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        """ GET Choice List for Parent Products Tax Status """

        info_logger.info("Parent Products Tax Status GET api called.")
        """ GET Parent Products Tax Status Choice List """
        fields = ['id', 'value', ]
        data = [dict(zip(fields, d)) for d in ParentProducts.TAX_STATUS_CHOICES]
        msg = ""
        return get_response(msg, data, True)


class ParentProductApprovalView(GenericAPIView):
    """
        Get Parent Product
        Search Parent Product
        List Parent Product
        Update Parent Product
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ParentProducts.objects.filter(tax_status__in=[ParentProducts.PENDING, ParentProducts.DECLINED])\
        .select_related('parent_brand', 'product_hsn', 'updated_by')\
        .prefetch_related('parent_product_pro_tax', 'parent_product_log', 'parent_product_pro_tax__tax', ) \
        .only('id', 'parent_id', 'name', 'product_type', 'updated_by', 'status', 'parent_brand__brand_name',
              'parent_brand__brand_code', 'updated_at', 'product_hsn__product_hsn_code', 'tax_status', 'tax_remark')\
        .order_by('-id')
    serializer_class = ParentProductApprovalSerializers

    def get(self, request):
        """ GET API for Parent Product with Image Category & Tax """

        info_logger.info("Parent Product GET api called.")
        product_total_count = self.queryset.count()
        active_product_total_count = self.queryset.filter(status=True).count()
        if request.GET.get('id'):
            """ Get Parent Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            parent_product = id_validation['data']
        else:
            """ GET Parent Product List """
            self.queryset = self.search_filter_parent_product()
            product_total_count = self.queryset.count()
            active_product_total_count = self.queryset.filter(status=True).count()
            parent_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(parent_product, many=True)
        msg = f"TOTAL PARENT SKUS {product_total_count}  TOTAL ACTIVE PARENT SKUS {active_product_total_count}" \
            if parent_product else "no parent product found"
        return get_response(msg, serializer.data, True)

    @can_approve_product_tax
    def put(self, request):
        """ PUT API to Approve Parent Product Tax """

        info_logger.info("Parent Product PUT api called.")

        modified_data = validate_data_format_without_json(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if 'id' not in modified_data:
            return get_response('please provide id to update parent product', False)

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

    def search_filter_parent_product(self):

        category = self.request.GET.get('category')
        brand = self.request.GET.get('brand')
        product_status = self.request.GET.get('status')
        tax_status = self.request.GET.get('tax_status')
        search_text = self.request.GET.get('search_text')

        # search using parent_id, name & category_name based on criteria that matches
        if search_text:
            self.queryset = parent_product_search(self.queryset, search_text.strip())
        # filter using brand_name, category & product_status exact match
        if brand is not None:
            self.queryset = self.queryset.filter(parent_brand__id=brand)
        if product_status is not None:
            self.queryset = self.queryset.filter(status=product_status)
        if tax_status is not None:
            self.queryset = self.queryset.filter(tax_status=tax_status)
        if category is not None:
            self.queryset = self.queryset.filter(
                parent_product_pro_category__category__id=category)
        return self.queryset.distinct()


class BulkParentProductApprovalView(GenericAPIView):
    """
        Update Parent Product
    """
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ParentProducts.objects.filter(tax_status__in=[ParentProducts.PENDING, ParentProducts.DECLINED])\
        .select_related('parent_brand', 'product_hsn', 'updated_by')\
        .prefetch_related('parent_product_pro_tax', 'parent_product_log', 'parent_product_pro_tax__tax', ) \
        .only('id', 'parent_id', 'name', 'product_type', 'updated_by', 'status', 'parent_brand__brand_name',
              'parent_brand__brand_code', 'updated_at', 'product_hsn__product_hsn_code', 'tax_status', 'tax_remark')\
        .order_by('-id')
    serializer_class = ParentProductApprovalSerializers

    @can_approve_product_tax
    def put(self, request):
        """ PUT API to Approve Parent Product Tax """

        info_logger.info("Bulk Parent Product PUT api called.")
        if not request.data.get('parent_product_ids'):
            return get_response('please select parent product', False)
        non_approved = []
        try:
            for id in request.data.get('parent_product_ids'):
                # validations for input id
                id_instance = validate_id(self.queryset, int(id))
                if 'error' in id_instance:
                    return get_response(id_instance['error'])
                parent_product_instance = id_instance['data'].last()

                serializer = self.serializer_class(instance=parent_product_instance,
                                                   data={'id': int(id), 'tax_status': ParentProduct.APPROVED})
                if serializer.is_valid():
                    serializer.save(updated_by=request.user)
                    info_logger.info("Parent Product Updated Successfully.")
                else:
                    non_approved.append(id)
        except Exception as e:
            error_logger.error(e)
            return get_response(f'please provide a valid tax id {id}', False)
        if non_approved:
            return get_response('Some products were not approved, kindly try to update individually to see error', False)
        else:
            return get_response('All selected products approved', True)


class SuperStoreProductListView(GenericAPIView):
    """
        Get Parent List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.filter(parent_product__product_type=ParentProducts.SUPERSTORE)
    serializer_class = ProductSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = child_product_search(self.queryset, search_text)
        product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product, many=True)
        msg = "" if product else "no product found"
        return get_response(msg, serializer.data, True)


class SuperStoreProductPriceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    queryset = SuperStoreProductPrice.objects.select_related('product', 'seller_shop')\
        .prefetch_related('product__parent_product', 'seller_shop__shop_type', 'seller_shop__shop_owner',
                          'product__parent_product__parent_product_pro_category',
                          'product__parent_product__parent_product_pro_b2c_category',). \
        order_by('-updated_at')
    serializer_class = SuperStoreProductPriceSerializers

    def get(self, request):
        """ GET API for SuperStore Product Price """

        info_logger.info("SuperStoreProductPrice GET api called.")

        price_count = 1
        if request.GET.get('id'):
            """ Get SuperStore Product Price for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_price = id_validation['data']
        else:
            """ GET Product Price  List """
            self.queryset = self.search_filter_super_store_product_price()
            price_count = self.queryset.count()
            product_price = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        msg = f"total count {price_count}" if product_price else "no product price found"
        serializer = self.serializer_class(product_price, many=True)
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for SuperStore Product Price """

        info_logger.info("SuperStore Product Price POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('product price created successfully!', None, 200)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for SuperStore Product Price Update """

        info_logger.info("SuperStore Product Price Updation PUT api called.")
        if 'id' not in request.data:
            return get_response('please provide id to update super store product price', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        product_price_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=product_price_instance, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("product price Updated Successfully.")
            return get_response('product price updated Successfully!', None, 200)
        return get_response(serializer_error(serializer), False)

    def search_filter_super_store_product_price(self):

        seller_shop_id = self.request.GET.get('seller_shop_id', None)
        product_id = self.request.GET.get('product_id')
        product_sku = self.request.GET.get('product_sku')
        category_id = self.request.GET.get('category_id')
        b2c_category_id = self.request.GET.get('b2c_category_id')
        mrp = self.request.GET.get('mrp')
        search_text = self.request.GET.get('search_text')

        # search using product name and product sku based on criteria that matches
        if search_text:
            self.queryset = product_price_search(self.queryset, search_text.strip())

        # filter using seller_shop_id, product_id, product_status, mrp & status exact match
        if product_id is not None and product_id is not '':
            self.queryset = self.queryset.filter(product_id=product_id)
        if category_id is not None and not category_id is '':
            self.queryset = self.queryset.filter(product__parent_product__parent_product_pro_category__category_id=
                                                 category_id)
        if b2c_category_id is not None and not b2c_category_id is '':
            self.queryset = self.queryset.filter(product__parent_product__parent_product_pro_b2c_category__category_id=
                                                 b2c_category_id)
        if product_sku is not None and not product_sku is '':
            self.queryset = self.queryset.filter(product__product_sku__icontains=product_sku)
        if seller_shop_id is not None and not seller_shop_id is '':
            self.queryset = self.queryset.filter(seller_shop_id=seller_shop_id)
        if mrp is not None and not mrp is '':
            self.queryset = self.queryset.filter(mrp__icontains=mrp)
        return self.queryset

    def delete(self, request):
        """ Delete SuperStore Product Price """

        info_logger.info("SuperStore Product Price DELETE api called.")
        if not request.data.get('product_price_ids'):
            return get_response('please select product price', False)
        try:
            for id in request.data.get('product_price_ids'):
                product_price_id = self.queryset.get(id=int(id))
                try:
                    product_price_id.delete()
                    info_logger.info(f"product price deleted by {request.user} product price id - {product_price_id}")
                except Exception as er:
                    return get_response(f'You can not delete product price {product_price_id}, '
                                        f'because this product price is getting used', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid product price id {id}', False)
        return get_response('product price were deleted successfully!', True)


class SuperStoreProductPriceAsCSVUploadView(GenericAPIView):
    """
    This class is used to upload csv file for Super store product prices
    """
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = SuperStoreProductPriceAsCSVUploadSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'user': self.request.user})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('data uploaded successfully!', serializer.data, True)
        return get_response(serializer_error(serializer), False)


class SuperStoreProductPriceAsCSVDownloadView(GenericAPIView):
    """
    This class is used to upload csv file for Super store product prices
    """
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = SuperStoreProductPriceDownloadSerializer

    def post(self, request):
        """ POST API for Download Sample CreateProductVendorMapping """

        info_logger.info("CreateProductVendorMappingSample POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("CreateProductVendorMapping Downloaded successfully")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)
