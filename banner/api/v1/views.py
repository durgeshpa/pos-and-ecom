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

class GetAllBannerListView(viewsets.ModelViewSet):
    queryset = Banner.objects.filter(status=True)
    serializer_class = BannerSerializer

    @list_route
    def roots(self, request):
        queryset = Banner.objects.filter(status=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
