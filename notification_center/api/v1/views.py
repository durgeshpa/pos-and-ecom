from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated)
from rest_framework.response import Response
from addresses.models import Country, State, City, Area, Address
from .serializers import (CountrySerializer, StateSerializer, CitySerializer,
        AreaSerializer, AddressSerializer)
from rest_framework import generics
from rest_framework import status
from rest_framework import permissions, authentication
from django.http import Http404


class NotificationView(APIView):
	# This api will be used to send the notifications to the users
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (AllowAny,)

 #    def send_notification():
 #    	# This function will call the Send notification utility
 #    	SendNotification().send_notification()
 # 