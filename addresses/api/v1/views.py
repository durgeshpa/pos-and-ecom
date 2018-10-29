from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated)
from rest_framework.response import Response
from addresses.models import Country, State, City, Area, Address
from .serializers import (CountrySerializer, StateSerializer, CitySerializer,
        AreaSerializer, AddressSerializer)
from rest_framework import generics

class CountryView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (AllowAny,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = CountrySerializer(queryset, many=True)
        return Response(serializer.data)

class StateView(generics.ListAPIView):
    serializer_class = StateSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = State.objects.all()
        country_id = self.request.query_params.get('country_id', None)
        if country_id is not None:
            queryset = queryset.filter(country=country_id)
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = StateSerializer(queryset, many=True)
        return Response(serializer.data)

class CityView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = City.objects.all()
        state_id = self.request.query_params.get('state_id', None)
        if state_id is not None:
            queryset = queryset.filter(country=state_id)
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = CitySerializer(queryset, many=True)
        return Response(serializer.data)

class AreaView(generics.ListCreateAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = (AllowAny,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = AreaSerializer(queryset, many=True)
        return Response(serializer.data)

class AddressView(generics.ListCreateAPIView):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = (AllowAny,)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = AddressSerializer(queryset, many=True)
        return Response(serializer.data)
