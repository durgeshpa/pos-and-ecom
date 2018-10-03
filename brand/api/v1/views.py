from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.generics import ListCreateAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BrandSerializer, BrandPositionSerializer, BrandDataSerializer
from brand.models import Brand, BrandPosition,BrandData
from rest_framework import viewsets
from rest_framework.decorators import list_route

class GetAllBrandListView(ListCreateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer

    @list_route
    def roots(self, request):
        queryset = BrandPosition.objects.all()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


'''class GetSlotBrandListView(ListCreateAPIView):
    queryset = BrandData.objects.all().order_by('brand_data_order')
    serializer_class = BrandPositionSerializer
    @list_route
    def roots(self, request):
        queryset = BrandData.objects.all().order_by('brand_data_order')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
'''


class GetSlotBrandListView(APIView):

    # queryset =
    # serializer_class = BannerPositionSerializer

    def get(self,*args,**kwargs):
        pos_name = self.kwargs.get('slot_position_name')
        data = BrandData.objects.filter(slot__position_name=pos_name).order_by('brand_data_order')
        if pos_name:
            data = BannerData.objects.filter(slot__position_name=pos_name)
        else:
            data = BannerData.objects.all()
        is_success = True if data else False
        #serializer_class = BannerPositionSerializer
        serializer = BrandPositionSerializer(data,many=True)
        return Response({"message":"", "response_data": serializer.data ,"is_success": is_success})
