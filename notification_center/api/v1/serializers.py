from rest_framework import serializers
from notification_center.models import (Notification)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'