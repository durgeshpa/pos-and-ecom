from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BrandSerializer, BrandPositionSerializer, BrandDataSerializer, SubBrandSerializer
from brand.models import Brand, BrandPosition,BrandData
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist
from shops.models import Shop, ParentRetailerMapping
from sp_to_gram.models import OrderedProductMapping


class GetSlotBrandListView(APIView):


    permission_classes = (AllowAny,)
    def get(self,*args,**kwargs):
        pos_name = self.kwargs.get('slot_position_name')
        shop_id = self.request.GET.get('shop_id')
        data = BrandData.objects.filter(brand_data__active_status='active')

        if pos_name and not shop_id:
            data = data.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(data,many=True)
        elif pos_name and shop_id == '-1':
            data = data.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(data,many=True)
        elif pos_name and shop_id:
            if Shop.objects.get(id=shop_id).retiler_mapping.exists():
                parent = ParentRetailerMapping.objects.get(retailer=shop_id).parent
                products_mappings = OrderedProductMapping.get_shop_stock(shop=parent).filter(available_qty__gt=0)
                product_brands = [product.product.product_brand for product in products_mappings]
                brand_subbrands = []
                brands = data.filter(slot__position_name=pos_name, slot__shop=parent).order_by('brand_data_order')
                for brand in brands:
                    if brand.brand_data.brnd_parent.filter(active_status='active').count()>0:
                        brand_subbrands.append(brand.brand_data)
                product_brands = set(product_brands)
                product_brands = list(product_brands)
                total_brands_list = product_brands + brand_subbrands
                data = data.filter(slot__position_name=pos_name, slot__shop=parent.id, brand_data__in = total_brands_list).order_by('brand_data_order')
                brand_data_serializer = BrandDataSerializer(data,many=True)
            else:
                data = data.filter(slot__position_name=pos_name, slot__shop=None).order_by('brand_data_order')
                brand_data_serializer = BrandDataSerializer(data,many=True)
        else:
            data = data.order_by('brand_data_order')
            brand_data_serializer = BrandDataSerializer(data,many=True)

        is_success = True if data else False

        return Response({"message":[""], "response_data": brand_data_serializer.data ,"is_success": is_success})

class GetSubBrandsListView(APIView):

    permission_classes = (AllowAny,)
    def get(self, *args, **kwargs):
        brand_id = kwargs.get('brand')
        shop_id = self.request.GET.get('shop_id')
        brand = Brand.objects.get(pk=brand_id)
        if shop_id and shop_id != '-1' and Shop.objects.get(id=shop_id).retiler_mapping.exists():
            parent = ParentRetailerMapping.objects.get(retailer=shop_id).parent
            grns = OrderedProductMapping.get_shop_stock(shop=parent).filter(available_qty__gt=0)
            product_subbrands = [grn.product.product_brand for grn in grns if grn.product.product_brand.brand_parent == brand ]
            product_subbrands = set(product_subbrands)
            product_subbrands = list(product_subbrands)
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
