import logging
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from django.http import HttpResponse
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_auth import authentication
from rest_framework.generics import GenericAPIView, CreateAPIView

from wms.common_functions import get_stock_available_brand_list
from .serializers import BrandDataSerializer, SubBrandSerializer, BrandCrudSerializers, ProductVendorMapSerializers, \
    BrandExportAsCSVSerializers, BrandListSerializers, BannerImageSerializer

from brand.models import Brand, BrandData
from rest_framework.permissions import AllowAny
from shops.models import Shop, ParentRetailerMapping
from retailer_backend.utils import SmallOffsetPagination
from products.services import brand_search
from products.common_function import get_response, serializer_error
from products.common_validators import validate_id
from brand.common_validators import validate_data_format
from products.models import ParentProduct
from cms.models import Card, CardData, CardItem, CardVersion

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class GetSlotBrandListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        pos_name = self.kwargs.get('slot_position_name')
        shop_id = self.request.GET.get('shop_id')
        brand_slots = BrandData.objects.filter(brand_data__status=True)

        if pos_name and not shop_id:
            brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(brand_slots, many=True)
        elif pos_name and shop_id == '-1':
            brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(brand_slots, many=True)

        elif pos_name and shop_id:
            if Shop.objects.get(id=shop_id).retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
                brand_subbrands = []
                # get list of brand ids with available inventory
                stock_available_brands_list = get_stock_available_brand_list(parent)
                brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=parent).order_by(
                    'brand_data_order')
                for brand_slot in brand_slots:
                    if brand_slot.brand_data.id in stock_available_brands_list:
                        brand_subbrands.append(brand_slot)
                    elif brand_slot.brand_data.brand_child.filter(status=True).count() > 0:
                        for active_sub_brand in brand_slot.brand_data.brand_child.filter(status=True):
                            if active_sub_brand.id in stock_available_brands_list:
                                brand_subbrands.append(brand_slot)
                                break
                brand_data_serializer = BrandDataSerializer(brand_subbrands, many=True)
            else:
                brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=None).order_by(
                    'brand_data_order')
                brand_data_serializer = BrandDataSerializer(brand_slots, many=True)
        else:
            brand_slots = brand_slots.order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(brand_slots, many=True)

        is_success = True if brand_slots else False

        return Response({"message": [""], "response_data": brand_data_serializer.data, "is_success": is_success})


class GetSubBrandsListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        brand_id = kwargs.get('brand')
        shop_id = self.request.GET.get('shop_id')
        brand = Brand.objects.get(pk=brand_id)
        banner_image = []
        card = Card.objects.filter(type='brand',brand_subtype = brand).last()
        if card:
            latest_card_version = CardVersion.objects.filter(card = card).last()
            card_items = latest_card_version.card_data.items.all()
            banner_image = BannerImageSerializer(card_items, many=True).data
        if shop_id and shop_id != '-1' and Shop.objects.get(id=shop_id).retiler_mapping.exists():
            parent = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
            product_subbrands = brand.brand_child.filter(status=True)
            if product_subbrands.exists():
                # get list of brand ids with available inventory
                stock_available_brands_list = get_stock_available_brand_list(parent)
                sub_brands_with_available_products = []
                for sub_brand in product_subbrands:
                    if sub_brand.id in stock_available_brands_list:
                        sub_brands_with_available_products.append(sub_brand)
                brand_data_serializer = SubBrandSerializer(sub_brands_with_available_products, many=True)
            else:
                product_subbrands = []
                brand_data_serializer = SubBrandSerializer(product_subbrands, many=True)
        else:
            product_subbrands = brand.brand_child.filter(status=True)
            brand_data_serializer = SubBrandSerializer(product_subbrands, many=True)
        is_success = True if product_subbrands else False
        data = {}
        if is_success:
            data = {
                "sub_brands": brand_data_serializer.data,
                "banner_image": banner_image
            }
        return Response({"message": [""], "response_data": data, "is_success": is_success})


class BrandListView(GenericAPIView):
    """
        Get Brand List
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.values('id', 'brand_name', )
    serializer_class = BrandListSerializers

    def get(self, request):
        search_text = self.request.GET.get('search_text')
        if search_text:
            self.queryset = brand_search(self.queryset, search_text)
        brand = SmallOffsetPagination().paginate_queryset(self.queryset, request)
        serializer = self.serializer_class(brand, many=True)
        msg = "" if brand else "no brand found"
        return get_response(msg, serializer.data, True)


class BrandView(GenericAPIView):
    """
        Get Brand
        Add Brand
        Search Brand
        List Brand
        Update Brand
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.select_related('brand_parent').prefetch_related('brand_child', 'brand_log',
                                                                             'brand_log__updated_by'). \
        only('id', 'brand_name', 'brand_code', 'brand_parent', 'brand_description', 'brand_slug',
             'brand_logo', 'status').order_by('-id')

    serializer_class = BrandCrudSerializers

    def get(self, request):
        info_logger.info("Brand GET api called.")
        brand_total_count = self.queryset.count()
        if request.GET.get('id'):
            """ Get brand for specific ID with SubBrand"""
            id_validation = validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])
            brand = id_validation['data']
        else:
            """ GET API for Brand LIST with SubBrand """
            self.queryset = self.search_filter_brand()
            brand = SmallOffsetPagination().paginate_queryset(self.queryset, request)
            brand_total_count = self.queryset.count()
        serializer = self.serializer_class(brand, many=True)
        msg = f"total count {brand_total_count}" if brand else "no brand found"
        return get_response(msg, serializer.data, True)

    def post(self, request):
        """ POST API for Brand Creation """

        info_logger.info("Brand POST api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        serializer = self.serializer_class(data=modified_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return get_response('brand created successfully!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def put(self, request):
        """ PUT API for Brand Updation  """

        info_logger.info("Brand PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if not modified_data['id']:
            return get_response('please provide id to update brand', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        brand_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=brand_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("brand updated successfully.")
            return get_response('brand updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def delete(self, request):
        """ Delete Brand """

        info_logger.info("Brand DELETE api called.")
        if not request.data.get('brand_ids'):
            return get_response('please select brand', False)
        try:
            for b_id in request.data.get('brand_ids'):
                brand_id = self.queryset.get(id=int(b_id))
                try:
                    brand_id.delete()
                    dict_data = {'deleted_by': request.user, 'deleted_at': datetime.now(),
                                 'brand_id': brand_id}
                    info_logger.info("child_product deleted info ", dict_data)
                    info_logger.info("brand deleted info ", dict_data)
                except:
                    return get_response(f'You can not delete brand {brand_id.brand_name}, '
                                        f'because this brand is mapped with product', False)
        except ObjectDoesNotExist as e:
            error_logger.error(e)
            return get_response(f'please provide a valid brand {b_id}', False)
        return get_response('brand were deleted successfully!', True)

    def search_filter_brand(self):

        brand_status = self.request.GET.get('status')
        search_text = self.request.GET.get('search_text')

        # search based on Brand Name, Brand Code & Parent Brand Name
        if search_text:
            self.queryset = brand_search(self.queryset, search_text.strip())

        # filter based on status
        if brand_status is not None:
            self.queryset = self.queryset.filter(status=brand_status)

        return self.queryset


class BrandVendorMappingView(GenericAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (AllowAny,)
    queryset = ParentProduct.objects.select_related('parent_brand').prefetch_related(
        'product_parent_product', 'product_parent_product__product_vendor_mapping',
        'product_parent_product__product_vendor_mapping__vendor', ).only('parent_brand', ).order_by('-id')
    serializer_class = ProductVendorMapSerializers

    def get(self, request):

        info_logger.info("BrandVendorMappingView GET api called.")
        if request.GET.get('id'):
            """ Get brand vendor mapping for specific Brand ID """
            id_validation = self.validate_id(self.queryset, int(request.GET.get('id')))
            if 'error' in id_validation:
                return get_response(id_validation['error'])

            brand = id_validation['data']
            serializer = self.serializer_class(brand, many=True)
            msg = "" if brand else "no brand found"
            return get_response(msg, serializer.data, True)
        else:
            msg = "please provide brand id"
            return get_response(msg, None)

    def validate_id(self, queryset, brand_id):
        """ validation only ids that belong to a selected related model """
        if not queryset.filter(parent_brand=brand_id).exists():
            return {'error': 'please provide a valid brand id'}
        uniq_data = queryset.filter(parent_brand=brand_id).order_by('-id').distinct()
        return {'data': uniq_data}


class BrandExportAsCSVView(CreateAPIView):
    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = BrandExportAsCSVSerializers

    def post(self, request):
        """ POST API for Download Selected Brand CSV """

        info_logger.info("Brand ExportAsCSV POST api called.")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            response = serializer.save()
            info_logger.info("Brand CSVExported successfully ")
            return HttpResponse(response, content_type='text/csv')
        return get_response(serializer_error(serializer), False)
