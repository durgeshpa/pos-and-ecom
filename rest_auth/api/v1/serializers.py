from rest_framework import serializers

from accounts.models import User


class UserProfileSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'phone_number',)