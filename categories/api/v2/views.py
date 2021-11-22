from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from shops.models import Shop, ParentRetailerMapping
from wms.common_functions import get_stock_available_category_list
from .serializers import CategorySerializer,CategoryDataSerializer, BrandSerializer, AllCategorySerializer
from categories.models import Category,CategoryData,CategoryPosation
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.permissions import (AllowAny,IsAuthenticated)
from brand.models import Brand


class GetAllSubCategoryListView(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Category.objects.filter(category_parent=None)
    serializer_class = CategorySerializer

    @list_route
    def roots(self, request):
        queryset = Category.objects.filter(category_parent=None)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class GetCategoryListBySlot(APIView):
    permission_classes = (AllowAny,)

    def get(self,*args,**kwargs):
        slot_name = self.kwargs.get("slot_name")
        if slot_name:
            category_data = CategoryData.objects.filter(category_pos__posation_name=slot_name)
        else:
            category_data = CategoryData.objects.all()
        category_data_serializer = CategoryDataSerializer(category_data,many=True)
        is_success = True if category_data else False
        return Response({ "message":[""],"response_data": category_data_serializer.data,"is_success":is_success})


class GetcategoryBrandListView(APIView):

    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        category_id = kwargs.get('category')
        category = Category.objects.get(pk=category_id)
        brands = Brand.objects.filter(categories = category_id)
        category_brand_serializer = BrandSerializer(brands,many=True)
        is_success = True if brands else False
        return Response({"message":[""], "response_data": category_brand_serializer.data ,"is_success":is_success })


class GetSubCategoriesListView(APIView):

    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        category_id = kwargs.get('category')
        category = Category.objects.get(pk=category_id)
        sub_categories = category.cat_parent.filter(status=True)
        sub_category_data_serializer = CategorySerializer(sub_categories,many=True)

        is_success = True if sub_categories else False
        return Response({"message":[""], "response_data": sub_category_data_serializer.data ,"is_success":is_success })


class GetAllCategoryListView(APIView):

    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        categories_to_return = []
        shop_id = self.request.GET.get('shop_id')
        if Shop.objects.filter(id=shop_id).exists():
            try:
                shop = ParentRetailerMapping.objects.get(retailer=shop_id, status=True).parent
            except Exception as e:
                return Response(data={'message': str(e)})
            # get list of category ids with available inventory for this shop
            categories_with_products = get_stock_available_category_list(shop)
        else:
            # get list of category ids with available inventory
            categories_with_products = get_stock_available_category_list()
        all_active_categories = Category.objects.filter(category_parent=None, status=True)
        for c in all_active_categories:
            if c.id in categories_with_products:
                categories_to_return.append(c)
            elif c.cat_parent.filter(status=True).count() > 0:
                for sub_category in c.cat_parent.filter(status=True):
                    if sub_category.id in categories_with_products:
                        categories_to_return.append(c)
                        break
        category_subcategory_serializer = AllCategorySerializer(categories_to_return, many=True)

        is_success = True if all_active_categories else False
        return Response({ "message":[""],"response_data": category_subcategory_serializer.data,"is_success":is_success})
