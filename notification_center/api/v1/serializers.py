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
        
    def get_serializer_context(self):
        return {"user": self.kwargs['user']}

    def create(self, validated_data):
        user = self.context["user"]
        dev_id = validated_data.get('dev_id', None)
        reg_id = validated_data.get('reg_id', None)

        device, created = Device.objects.update_or_create(
            dev_id=dev_id,
            defaults={'user': user, 'reg_id':reg_id})
        return device



class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'



class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = '__all__'        