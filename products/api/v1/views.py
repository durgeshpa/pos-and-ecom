import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import URLValidator

from rest_framework import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny

from products.models import ParentProduct as ParentProducts, ProductHSN, ProductCapping as ProductCappings, \
    ParentProductImage, ProductVendorMapping, Product as ChildProduct, Tax
from brand.models import Brand

from retailer_backend.utils import SmallOffsetPagination
from .serializers import ParentProductSerializers, BrandSerializers, ParentProductBulkUploadSerializers, \
    ParentProductExportAsCSVSerializers, ActiveDeactivateSelectedProductSerializers, ProductHSNSerializers, \
    ProductCappingSerializers, ProductVendorMappingSerializers, ChildProductSerializers, TaxSerializers, CategorySerializers
from products.common_function import get_response, serializer_error
from products.common_validators import validate_id, validate_data_format
from products.services import parent_product_search, child_product_search, product_hsn_search, tax_search
from categories.models import Category

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class BrandView(GenericAPIView):
    """
        Get Brand
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.all()
    serializer_class = BrandSerializers

    def get(self, request):
        if request.GET.get('id'):
            """ Get Parent Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            brand = id_validation['data']
        else:
            brand = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(brand, many=True)
        return get_response('brand list!', serializer.data)


class CategoryView(GenericAPIView):
    """
        Get Brand
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Category.objects.all()
    serializer_class = CategorySerializers

    def get(self, request):
        if request.GET.get('id'):
            """ Get Parent Product for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            category = id_validation['data']
        else:
            category = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(category, many=True)
        return get_response('category list!', serializer.data)


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
        'parent_product_pro_tax__tax', 'product_parent_product__product_vendor_mapping__vendor'). \
        only('id', 'parent_id', 'name', 'inner_case_size', 'product_type', 'is_ptr_applicable', 'updated_by',
             'ptr_percent', 'ptr_type', 'status', 'parent_brand__brand_name', 'parent_brand__brand_code',
             'product_hsn__product_hsn_code', 'is_lead_time_applicable', 'is_ars_applicable', 'max_inventory').order_by('-id')
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
        return get_response('parent product list!', serializer.data)

    def post(self, request):
        """ POST API for Parent Product Creation with Image Category & Tax """

        info_logger.info("Parent Product POST api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('parent product created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Parent Product Updation with Image Category & Tax """

        info_logger.info("Parent Product PUT api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if not modified_data['id']:
            return get_response('please provide id to update parent product', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        parent_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=parent_product_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return get_response('parent product updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

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

    def validate_data_format(self):
        # Validate product data
        try:
            data = json.loads(self.request.data["data"], )
        except (KeyError, ValueError):
            return {'error': "Invalid Data Format"}
        image_files = self.request.FILES.getlist('parent_product_pro_image')
        data['parent_product_pro_image'] = image_files
        return data


class ParentProductBulkUploadView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = ParentProductBulkUploadSerializers

    def post(self, request, *args, **kwargs):
        """ POST API for Bulk Upload Parent Product CSV with Category & Tax """

        info_logger.info("Parent Product Bulk Upload POST api called.")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('parent product CSV uploaded successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class ParentProductExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request):
        """ POST API for Download Selected Parent Product CSV with Image Category & Tax """

        info_logger.info("Parent Product ExportAsCSV POST api called.")
        serializer = ParentProductExportAsCSVSerializers(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            return response
        return get_response(serializer_error(serializer), False)


class ActiveDeactivateSelectedProductView(UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    parent_product_list = ParentProducts.objects.all()

    def put(self, request):
        """ PUT API for Activate or Deactivate Selected Parent Product """

        info_logger.info("Parent Product ActiveDeactivateSelectedProduct PUT api called.")
        serializer = ActiveDeactivateSelectedProductSerializers(instance=self.parent_product_list.filter(
            id__in=request.data['parent_product_id_list']),
            data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return get_response('parent product updated successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)


class ProductCappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
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
        return get_response('Product Capping List', serializer.data)

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
    permission_classes = (AllowAny,)
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
        return get_response('product vendor list!', serializer.data)

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
    queryset = ChildProduct.objects.select_related('updated_by').prefetch_related('product_pro_image', 'product_vendor_mapping', 'parent_product',
              'parent_product__parent_product_pro_image', 'parent_product__parent_product_pro_category', 'parent_product__parent_product_pro_tax',
              'parent_product__parent_product_pro_category__category', 'parent_product__product_parent_product__product_vendor_mapping',
              'parent_product__parent_product_pro_tax__tax', 'parent_product__parent_brand', 'parent_product__product_hsn','parent_product__product_parent_product__product_vendor_mapping',
              'parent_product__product_parent_product__product_vendor_mapping__vendor', 'product_vendor_mapping__vendor').order_by('-id')
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
        return get_response('child product list!', serializer.data)

    def post(self, request):
        """ POST API for Child Product """

        info_logger.info("Child Product POST api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save()
            return get_response('child product created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Child Product Updation with Image """

        info_logger.info("Child Product PUT api called.")

        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if not modified_data['id']:
            return get_response('please provide id to update child product', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        parent_product_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=parent_product_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save()
            return get_response('child product updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

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


class ProductHSNView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ProductHSN.objects.all()
    serializer_class = ProductHSNSerializers

    def get(self, request):
        """ GET API for Product HSN """

        info_logger.info("Product HSN GET api called.")
        if request.GET.get('id'):
            """ Get Product HSN for specific ID """
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            product_hsn = id_validation['data']
        else:
            """ GET Product HSN List """
            self.queryset = self.search_filter_product_hsn()
            product_hsn = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_hsn, many=True)
        return get_response('product hsn list!', serializer.data)

    def post(self, request, *args, **kwargs):
        """ POST API for ProductHSN Creation """

        info_logger.info("ProductHSN POST api called.")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('product HSN created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_product_hsn(self):
        search_text = self.request.GET.get('search_text')
        # search using product_hsn_code based on criteria that matches
        if search_text:
            self.queryset = product_hsn_search(self.queryset, search_text)
        return self.queryset


class TaxView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = Tax.objects.all()
    serializer_class = TaxSerializers

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
            self.queryset = self.search_filter_product_hsn()
            product_tax = SmallOffsetPagination().paginate_queryset(self.queryset, request)

        serializer = self.serializer_class(product_tax, many=True)
        return get_response('product tax list!', serializer.data)

    def post(self, request, *args, **kwargs):
        """ POST API for Tax Creation """

        info_logger.info("Tax POST api called.")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return get_response('product HSN created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_product_hsn(self):
        search_text = self.request.GET.get('search_text')
        # search using product_hsn_code based on criteria that matches
        if search_text:
            self.queryset = tax_search(self.queryset, search_text)
        return self.queryset
