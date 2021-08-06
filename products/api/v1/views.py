import logging
from datetime import datetime

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from rest_framework import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny

from products.models import ParentProduct as ParentProducts, ProductHSN, ProductCapping as ProductCappings, \
    ProductVendorMapping, Product as ChildProduct, Tax, Weight, ProductPrice
from categories.models import Category
from brand.models import Brand, Vendor

from retailer_backend.utils import SmallOffsetPagination

from .serializers import ParentProductSerializers, BrandSerializers, ParentProductExportAsCSVSerializers, \
    ActiveDeactiveSelectedParentProductSerializers, ProductHSNSerializers, WeightExportAsCSVSerializers, \
    ProductCappingSerializers, ProductVendorMappingSerializers, ChildProductSerializers, TaxSerializers, \
    CategorySerializers, ProductSerializers, GetParentProductSerializers, ActiveDeactiveSelectedChildProductSerializers, \
    ChildProductExportAsCSVSerializers, TaxCrudSerializers, TaxExportAsCSVSerializers, WeightSerializers, \
    ProductHSNCrudSerializers, HSNExportAsCSVSerializers, ProductPriceSerializers, ProductVendorMappingExportAsCSVSerializers
from brand.api.v1.serializers import VendorSerializers
from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format
from products.services import parent_product_search, child_product_search, product_hsn_search, tax_search, \
    category_search, brand_search, parent_product_name_search, vendor_search, product_vendor_search

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
    queryset = ParentProducts.objects.select_related('parent_brand', 'product_hsn', 'updated_by').prefetch_related(
        'parent_product_pro_category', 'parent_product_pro_tax', 'product_parent_product', 'parent_product_log',
        'product_parent_product__product_pro_image', 'parent_product_pro_category__category',
        'product_parent_product__product_vendor_mapping', 'parent_product_pro_tax__tax', 'parent_product_pro_image',
        'parent_product_log__updated_by', 'product_parent_product__product_vendor_mapping__vendor', ) \
        .only('id', 'parent_id', 'name', 'inner_case_size', 'product_type', 'is_ptr_applicable', 'updated_by',
              'ptr_percent', 'ptr_type', 'status', 'parent_brand__brand_name', 'parent_brand__brand_code',
              'updated_at', 'product_hsn__product_hsn_code', 'is_lead_time_applicable', 'is_ars_applicable',
              'max_inventory', 'brand_case_size').order_by('-id')
    serializer_class = ParentProductSerializers

    def get(self, request):
        """ GET API for Parent Product with Image Category & Tax """

        info_logger.info("Parent Product GET api called.")
        product_total_count = self.queryset.count()
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
            parent_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(parent_product, many=True)
        msg = f"total count {product_total_count}" if parent_product else "no parent product found"
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
            return get_response('parent product created successfully!', serializer.data)
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
        brand = self.request.GET.get('brand')
        product_status = self.request.GET.get('status')
        search_text = self.request.GET.get('search_text')

        # search using parent_id, name & category_name based on criteria that matches
        if search_text:
            self.queryset = parent_product_search(self.queryset, search_text.strip())
        # filter using brand_name, category & product_status exact match
        if brand is not None:
            self.queryset = self.queryset.filter(parent_brand__id=brand)
        if product_status is not None:
            self.queryset = self.queryset.filter(status=product_status)
        if category is not None:
            self.queryset = self.queryset.filter(
                parent_product_pro_category__category__id=category)
        return self.queryset


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
        ch_product_total_count = self.queryset.count()
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
            child_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(child_product, many=True)

        msg = f"total count {ch_product_total_count}" if child_product else "no child product found"
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
    queryset = ProductHSN.objects.prefetch_related('hsn_log', 'hsn_log__updated_by').only('id', 'product_hsn_code'). \
        order_by('-id')
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
        serializer = self.get_serializer(data=request.data)
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
        serializer = self.serializer_class(instance=hsn_instance, data=request.data)
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


class ChildProductListView(GenericAPIView):
    """
        Get Child List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ChildProduct.objects.values('id', 'product_name', 'product_sku')
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


class SlabProductPriceView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ProductPrice.objects.select_related('product', 'seller_shop', 'buyer_shop', 'city', 'pincode', ).order_by('-id')
    serializer_class = ProductPriceSerializers

    def get(self, request):
        """ GET API for Product Price """

        info_logger.info("Product Price GET api called.")
        pro_vendor_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get Product Price for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_vendor_map = id_validation['data']
        else:
            """ GET Product Price  List """
            self.queryset = self.search_filter_product_vendor_map()
            pro_vendor_count = self.queryset.count()
            product_vendor_map = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        msg = f"total count {pro_vendor_count}" if product_vendor_map else "no product price found"
        serializer = self.serializer_class(product_vendor_map, many=True)
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Product Price """

        info_logger.info("Product Price POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('product price created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Product Price Updation """

        info_logger.info("Product Price PUT api called.")
        if not request.data.get('id'):
            return get_response('please provide id to update product price', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(request.data.get('id')))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        product_vendor_map_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=product_vendor_map_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('product price updated!', serializer.data)
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
