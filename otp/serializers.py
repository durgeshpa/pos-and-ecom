from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import PhoneOTP
from retailer_to_sp.models import Shop
UserModel = get_user_model()

class PhoneOTPValidateSerializer(serializers.ModelSerializer):
    """
    validate the otp send to number
    """
    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
            'otp'
        )

class SendSmsOTPSerializer(serializers.ModelSerializer):
    """
    Send OTP SMS to number
    """
    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number', 'action', 'app_type'
        )
    action = serializers.IntegerField(required=False)
    app_type = serializers.IntegerField(required=False)

    def validate(self, attrs):
        """
        OTP should not be sent to existing user from registration screen
        """
        number = attrs.get('phone_number')
        action = attrs.get('action')
        app_type = attrs.get('app_type')
        user = UserModel.objects.filter(phone_number=number)
        if action != 1:
            if user.exists():
                raise serializers.ValidationError("User already exists! Please login")
        elif not user.exists():
            raise serializers.ValidationError("User does not exists! Please Register")
        elif app_type == 2:
            if not (Shop.objects.filter(shop_owner=user.last(), shop_type__shop_type='f').exists() or
                                           Shop.objects.filter(related_users=user.last(), shop_type__shop_type='f').exists()):
                raise serializers.ValidationError("Shop Doesn't Exist!")
        return attrs

class ResendSmsOTPSerializer(serializers.ModelSerializer):
    """
    Resend OTP SMS to number
    """
    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )

class ResendVoiceOTPSerializer(serializers.ModelSerializer):
    """
    Resend OTP voice call to number
    """
    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )
