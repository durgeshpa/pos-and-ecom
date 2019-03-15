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
        elif pos_name and shop_id:
            parent = ParentRetailerMapping.objects.get(retailer=shop_id).parent.id
            products_mappings = OrderedProductMapping.objects.filter(
                ordered_product__order__ordered_cart__shop__id=parent,
            )
            product_brands = []
            for product in products_mappings:
                if product.available_qty > 0:
                    product_brands.append(product.product.product_brand)
            product_brands = set(product_brands)
            product_brands = list(product_brands)
            data = data.filter(slot__position_name=pos_name, slot__shop=parent, brand_data__in = product_brands).order_by('brand_data_order')
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
        brand = Brand.objects.get(pk=brand_id)
        data = brand.brnd_parent.filter(active_status='active')
        is_success = True if data else False
        brand_data_serializer = SubBrandSerializer(brand.brnd_parent.filter(active_status='active'),many=True)
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
