from rest_framework import serializers
from notification_center.models import (Notification,
	UserNotification
	)

from fcm.utils import get_device_model
Device = get_device_model()
# from fcm.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('dev_id','reg_id','name','is_active', 'user')
        extra_kwargs = {'user':{'required':False}}
        


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'



class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = '__all__'        