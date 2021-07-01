import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from rest_framework import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView, UpdateAPIView

from products.models import ParentProduct as ParentProducts, ProductHSN, ProductCapping as ProductCappings, \
    ParentProductImage, ProductVendorMapping, Product as ChildProduct, Tax, ProductSourceMapping, ProductPackingMapping, \
    ProductSourceMapping, Weight
from categories.models import Category
from brand.models import Brand

from retailer_backend.utils import SmallOffsetPagination
from .serializers import ParentProductSerializers, BrandSerializers, ParentProductExportAsCSVSerializers, \
    ActiveDeactiveSelectedParentProductSerializers, ProductHSNSerializers, WeightExportAsCSVSerializers, \
    ProductCappingSerializers, ProductVendorMappingSerializers, ChildProductSerializers, TaxSerializers, \
    CategorySerializers, ProductSerializers, GetParentProductSerializers, ActiveDeactiveSelectedChildProductSerializers, \
    ChildProductExportAsCSVSerializers, TaxCrudSerializers, TaxExportAsCSVSerializers, WeightSerializers

from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format, validate_bulk_data_format
from products.services import parent_product_search, child_product_search, product_hsn_search, tax_search, \
    category_search, brand_search, parent_product_name_search


from rest_framework.permissions import AllowAny

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BrandListView(GenericAPIView):
    """
        Get Brand List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.values('id', 'brand_name')
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
    queryset = Category.objects.values('id', 'category_name')
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
        msg = "" if product else "no product found"
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
    permission_classes = (AllowAny,)
    queryset = Tax.objects.prefetch_related('tax_log', 'tax_log__updated_by')\
        .only('id', 'tax_name', 'tax_type', 'tax_percentage', 'tax_start_at', 'tax_end_at', 'status').\
        order_by('-id')

    serializer_class = TaxCrudSerializers

    def get(self, request):
        """ GET API for Tax """

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
            product_tax = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_tax, many=True)
        msg = "" if product_tax else "no tax found"
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
            return get_response('please provide tax_ids', False)
        try:
            for id in request.data.get('tax_ids'):
                tax_id = self.queryset.get(id=int(id))
                try:
                    tax_id.delete()
                except:
                    return get_response(f'can not delete tax {tax_id.tax_name}', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid tax_id {id}', False)
        return get_response('tax were deleted successfully!', True)

    def search_filter_product_tax(self):
        search_text = self.request.GET.get('search_text')
        # search using tax_name and tax_type based on criteria that matches
        if search_text:
            self.queryset = tax_search(self.queryset, search_text)
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
        'parent_product_pro_image', 'parent_product_pro_category', 'parent_product_pro_tax', 'product_parent_product',
        'parent_product_pro_category__category', 'product_parent_product__product_vendor_mapping',
        'parent_product_pro_tax__tax', 'product_parent_product__product_vendor_mapping__vendor', 'parent_product_log', 'parent_product_log__updated_by'). \
        only('id', 'parent_id', 'name', 'inner_case_size', 'product_type', 'is_ptr_applicable', 'updated_by',
             'ptr_percent', 'ptr_type', 'status', 'parent_brand__brand_name', 'parent_brand__brand_code', 'updated_at',
             'product_hsn__product_hsn_code', 'is_lead_time_applicable', 'is_ars_applicable', 'max_inventory')\
        .order_by('-id')
    serializer_class = ParentProductSerializers

    def get(self, request):
        """ GET API for Parent Product with Image Category & Tax """

        info_logger.info("Parent Product GET api called.")
        if request.GET.get('id'):
            """ Get Parent Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            parent_product = id_validation['data']
        else:
            """ GET Parent Product List """
            self.queryset = self.search_filter_parent_product()
            parent_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(parent_product, many=True)
        msg = "" if parent_product else "no product product found"
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
            return get_response('please provide parent_product_id', False)
        try:
            for id in request.data.get('parent_product_id'):
                parent_product_id = self.queryset.get(id=int(id))
                try:
                    parent_product_id.delete()
                except:
                    return get_response(f'can not delete parent_product {parent_product_id.name}', False)
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
            self.queryset = parent_product_search(self.queryset, search_text)
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
    queryset = ChildProduct.objects.select_related('parent_product').prefetch_related('product_pro_image',
        'product_vendor_mapping', 'parent_product__parent_product_pro_image', 'child_product_log', 'child_product_log__updated_by',
        'parent_product__parent_product_pro_category__category', 'parent_product__parent_product_pro_category',
        'destination_product_pro', 'destination_product_pro__source_sku', 'destination_product_repackaging',
        'packing_product_rt', 'packing_product_rt__packing_sku', 'parent_product__product_hsn',
        'parent_product__product_parent_product__product_vendor_mapping', 'parent_product__parent_product_log',
        'parent_product__parent_product_log__updated_by', 'parent_product__product_parent_product__product_vendor_mapping__vendor',
        'product_vendor_mapping__vendor', 'parent_product__product_parent_product__product_vendor_mapping',
        'parent_product__parent_brand', 'parent_product__parent_product_pro_tax', 'product_pro_tax',
        'parent_product__parent_product_pro_tax__tax', 'product_pro_tax__tax',).order_by('-id')

    serializer_class = ChildProductSerializers

    def get(self, request):
        """ GET API for Child Product with Image Category & Tax """

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
            child_product = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(child_product, many=True)
        msg = "" if child_product else "no child product found"
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
        parent_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=parent_product_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("Child Product Updated Successfully.")
            return get_response('child product updated Successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Child Product with image """

        info_logger.info("Child Product DELETE api called.")
        if not request.data.get('child_product_id'):
            return get_response('please provide child_product_id', False)
        try:
            for id in request.data.get('child_product_id'):
                child_product_id = self.queryset.get(id=int(id))
                try:
                    child_product_id.delete()
                except:
                    return get_response(f'can not delete child_product {child_product_id.product_name}', False)
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
            self.queryset = child_product_search(self.queryset, search_text)
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


class ActiveDeactiveSelectedParentProductView(UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    parent_product_list = ParentProducts.objects.values('id',)
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
    child_product_list = ChildProduct.objects.values('id',)
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


class ProductVendorMappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = ProductVendorMapping.objects.select_related('vendor', 'product')
    serializer_class = ProductVendorMappingSerializers

    def get(self, request):
        """ GET API for Product Vendor Mapping """

        info_logger.info("Product Vendor Mapping GET api called.")
        if request.GET.get('id'):
            """ Get Product Vendor Mapping for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_vendor_map = id_validation['data']
        else:
            """ GET Product Vendor Mapping  List """
            self.queryset = self.search_filter_product_vendor_map()
            product_vendor_map = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_vendor_map, many=True)
        return get_response('product vendor list!', serializer.data, True)

    def post(self, request):
        """ POST API for Product Vendor Mapping """

        info_logger.info("Product Vendor Mapping POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
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
            serializer.save()
            return get_response('product vendor mapping updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_product_vendor_map(self):

        vendor_id = self.request.GET.get('vendor_id')
        product_id = self.request.GET.get('product_id')
        product_status = self.request.GET.get('product_status')
        status = self.request.GET.get('status')

        # filter using vendor_name, product_id, product_status & status exact match
        if product_id is not None:
            self.queryset = self.queryset.filter(product_id=product_id)
        if vendor_id is not None:
            self.queryset = self.queryset.filter(vendor_id=vendor_id)
        if status is not None:
            self.queryset = self.queryset.filter(status=status)
        if product_status is not None:
            self.queryset = self.queryset.filter(product__status=product_status)
        return self.queryset


class WeightView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Weight.objects.prefetch_related('weight_log', 'weight_log__updated_by')\
        .only('id', 'weight_value', 'weight_unit', 'status', 'weight_name').order_by('-id')

    serializer_class = WeightSerializers

    def get(self, request):
        """ GET API for Weight """

        info_logger.info("Weight GET api called.")
        if request.GET.get('id'):
            """ Get Weight for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_tax = id_validation['data']
        else:
            """ GET Weight List """
            product_tax = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(product_tax, many=True)
        msg = "" if product_tax else "no weight found"
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
            return get_response('please provide weight_ids', False)
        try:
            for w_id in request.data.get('weight_ids'):
                weight_id = self.queryset.get(id=int(w_id))
                try:
                    weight_id.delete()
                except:
                    return get_response(f'can not delete weight {weight_id.weight_name}', False)
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