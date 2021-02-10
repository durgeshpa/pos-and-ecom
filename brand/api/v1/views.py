from rest_framework.views import APIView
from rest_framework.response import Response

from wms.common_functions import get_stock_available_brand_list
from .serializers import BrandDataSerializer, SubBrandSerializer
from brand.models import Brand, BrandData
from rest_framework.permissions import AllowAny
from shops.models import Shop, ParentRetailerMapping


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


'''class GetAllBrandListView(ListCreateAPIView):
    queryset = Brand.objects.filter(active_status='active')
    serializer_class = BrandSerializer

    @list_route
    def roots(self, request):
        queryset = Brand.objects.filter(active_status='active')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
'''

'''class GetSlotBrandListView(ListCreateAPIView):
    queryset = BrandData.objects.all().order_by('brand_data_order')
    serializer_class = BrandPositionSerializer
    @list_route
    def roots(self, request):
        queryset = BrandData.objects.all().order_by('brand_data_order')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
'''
