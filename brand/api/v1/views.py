import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication
from rest_framework.generics import GenericAPIView

from wms.common_functions import get_stock_available_brand_list
from .serializers import BrandDataSerializer, SubBrandSerializer, BrandCrudSerializers
from brand.models import Brand, BrandData
from rest_framework.permissions import AllowAny
from shops.models import Shop, ParentRetailerMapping
from retailer_backend.utils import SmallOffsetPagination
from products.services import brand_search
from products.common_function import get_response, serializer_error
from products.common_validators import validate_id
from brand.common_validators import validate_data_format

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class GetSlotBrandListView(APIView):

    permission_classes = (AllowAny,)

    def get(self,*args,**kwargs):
        pos_name = self.kwargs.get('slot_position_name')
        shop_id = self.request.GET.get('shop_id')
        brand_slots = BrandData.objects.filter(brand_data__active_status='active')

        if pos_name and not shop_id:
            brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(brand_slots, many=True)
        elif pos_name and shop_id == '-1':
            brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(brand_slots,many=True)

        elif pos_name and shop_id:
            if Shop.objects.get(id=shop_id).retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=shop_id, status = True).parent
                brand_subbrands = []
                # get list of brand ids with available inventory
                stock_available_brands_list = get_stock_available_brand_list(parent)
                brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=parent).order_by('brand_data_order')
                for brand_slot in brand_slots:
                    if brand_slot.brand_data.id in stock_available_brands_list:
                        brand_subbrands.append(brand_slot)
                    elif brand_slot.brand_data.brnd_parent.filter(active_status='active').count() > 0:
                        for active_sub_brand in brand_slot.brand_data.brnd_parent.filter(active_status='active'):
                            if active_sub_brand.id in stock_available_brands_list:
                                brand_subbrands.append(brand_slot)
                                break
                brand_data_serializer = BrandDataSerializer(brand_subbrands,many=True)
            else:
                brand_slots = brand_slots.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
                brand_data_serializer = BrandDataSerializer(brand_slots,many=True)
        else:
            brand_slots = brand_slots.order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(brand_slots,many=True)

        is_success = True if brand_slots else False

        return Response({"message": [""], "response_data": brand_data_serializer.data, "is_success": is_success})


class GetSubBrandsListView(APIView):

    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        brand_id = kwargs.get('brand')
        shop_id = self.request.GET.get('shop_id')
        brand = Brand.objects.get(pk=brand_id)
        if shop_id and shop_id != '-1' and Shop.objects.get(id=shop_id).retiler_mapping.exists():
            parent = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
            product_subbrands = brand.brnd_parent.filter(active_status='active')
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
                brand_data_serializer = SubBrandSerializer(product_subbrands,many=True)
        else:
            product_subbrands = brand.brnd_parent.filter(active_status='active')
            brand_data_serializer = SubBrandSerializer(product_subbrands,many=True)

        is_success = True if product_subbrands else False
        return Response({"message":[""], "response_data": brand_data_serializer.data ,"is_success":is_success })


class BrandView(GenericAPIView):
    """
        Get Brand
        Add Brand
        Search Brand
        List Brand
        Update Brand
    """
    authentication_classes = (authentication.TokenAuthentication,)
    queryset = Brand.objects.select_related('brand_parent', 'updated_by').prefetch_related('brand_child', 'brand_log').\
        only('id', 'brand_name', 'brand_code', 'brand_parent', 'brand_description', 'updated_by', 'brand_slug',
             'brand_logo', 'status').order_by('-id')
    serializer_class = BrandCrudSerializers

    def get(self, request):

        info_logger.info("Brand GET api called.")
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
        serializer = self.serializer_class(brand, many=True)
        msg = "" if brand else "no brand found"
        return get_response(msg, serializer.data)

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

        info_logger.info("Category PUT api called.")
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return get_response(modified_data['error'])

        if not modified_data['id']:
            return get_response('please provide id to update brand', False)

        # validations for input id
        id_instance = validate_id(self.queryset, int(modified_data['id']))
        if 'error' in id_instance:
            return get_response(id_instance['error'])
        category_instance = id_instance['data'].last()

        serializer = self.serializer_class(instance=category_instance, data=modified_data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            info_logger.info("category Updated Successfully.")
            return get_response('category updated!', serializer.data)
        return get_response(serializer_error(serializer), False)

    def search_filter_brand(self):

        brand_status = self.request.GET.get('status')
        search_text = self.request.GET.get('search_text')

        # search based on Brand Name, Brand Code & Parent Brand Name
        if search_text:
            self.queryset = brand_search(self.queryset, search_text)

        # filter based on status
        if brand_status is not None:
            self.queryset = self.queryset.filter(status=brand_status)

        return self.queryset
