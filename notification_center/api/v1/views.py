from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated)
from rest_framework.response import Response
from rest_framework import generics, viewsets
from rest_framework import status
from rest_framework import permissions, authentication
from django.http import Http404
from fcm.utils import get_device_model

from .serializers import (DeviceSerializer, NotificationSerializer,
    UserNotificationSerializer)
from notification_center.models import (Notification, UserNotification)

Device = get_device_model()


class DeviceViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


class NotificationView(APIView):
	# This api will be used to send the notifications to the users
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (AllowAny,)

 #    def send_notification():
 #    	# This function will call the Send notification utility
 #    	SendNotification().send_notification()
 # 



class UserNotificationView(APIView):
	# This api will be used to send the notifications to the users
    queryset = UserNotification.objects.all()
    serializer_class = UserNotificationSerializer
    permission_classes = (AllowAny,)

