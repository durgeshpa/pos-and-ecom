from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CategoriesSerializer
from category.models import Categories
from rest_framework import viewsets
from rest_framework.decorators import list_route

class GetAllCategoryListView(viewsets.ModelViewSet):
    queryset = Categories.objects.filter(category_parent=None)
    serializer_class = CategoriesSerializer

    @list_route
    def roots(self, request):
        queryset = Categories.objects.filter(category_parent=None)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

