from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CategorySerializer,CategoryDataSerializer
from categories.models import Category,CategoryData,CategoryPosation
from rest_framework import viewsets
from rest_framework.decorators import list_route

class GetAllSubCategoryListView(viewsets.ModelViewSet):
    queryset = Category.objects.filter(category_parent=None)
    serializer_class = CategorySerializer

    @list_route
    def roots(self, request):
        queryset = Category.objects.filter(category_parent=None)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class GetCategoryListBySlot(APIView):

    def get(self,*args,**kwargs):
        slot_name = self.kwargs.get("slot_name")
        if slot_name:
            category_data = CategoryData.objects.filter(category_pos__posation_name=slot_name)
        else:
            category_data = CategoryData.objects.all()
        category_data_serializer = CategoryDataSerializer(category_data,many=True)
        is_success = True if category_data else False
        return Response({ "message":"","response_data": category_data_serializer.data,"is_success":is_success})