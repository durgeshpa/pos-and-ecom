from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated)
from rest_framework.response import Response
from rest_framework import generics, viewsets
from rest_framework import status
from rest_framework import permissions
from rest_auth import authentication
from django.http import Http404
from fcm.utils import get_device_model

from .serializers import (DeviceSerializer, NotificationSerializer,
    UserNotificationSerializer)
from notification_center.models import (Notification, UserNotification)
from ...common_function import validate_data_format, validate_dev_id

Device = get_device_model()


class DeviceViewSet(viewsets.ModelViewSet):
    # permission_classes = (AllowAny,)
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self,  request, *args, **kwargs):

        dev_id = request.GET.get('dev_id', None)
        if dev_id is None:
            return Response({'is_success': False, 'message': "Please Provide dev id", 'response_data': None},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        queryset = self.queryset.filter(dev_id=dev_id)
        serializer = self.serializer_class(queryset, many=True)
        msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        return Response(msg, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': [''], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        device = serializer.save(user=self.request.user)
        return device

    def update(self, request, *args, **kwargs):

        pk = self.kwargs.get('pk', None)
        modified_data = validate_data_format(self.request)
        if 'error' in modified_data:
            return Response({'is_success': False, 'message': [modified_data['error']], 'response_data': None},
                            status=status.HTTP_406_NOT_ACCEPTABLE)

        if not pk:
            return Response({'is_success': False, 'message': ['please provide id to update device data'],
                             'response_data': None}, status=status.HTTP_406_NOT_ACCEPTABLE)

        # validations for input id
        id_instance = validate_dev_id(self.queryset, int(pk))
        if 'error' in id_instance:
            return Response({'is_success': False, 'message': [id_instance['error']], 'response_data': None},
                            status=status.HTTP_406_NOT_ACCEPTABLE)

        device_instance = id_instance['data'].last()
        serializer = self.get_serializer(instance=device_instance, data=request.data)
        if serializer.is_valid(raise_exception=True):
            self.perform_create(serializer)
            msg = {'is_success': True, 'message': None, 'response_data': serializer.data}
        else:
            msg = {'is_success': False, 'message': [''], 'response_data': None}
        return Response(msg, status=status.HTTP_200_OK)


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

