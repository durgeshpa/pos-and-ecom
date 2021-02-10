from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import PhoneOTP
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
            'phone_number', 'action'
        )
    action = serializers.CharField(required=False)

    def validate(self, attrs):
        """
        OTP should not be sent to existing user from registration screen
        """
        number = attrs.get('phone_number')
        action = attrs.get('action')
        user = UserModel.objects.filter(phone_number=number)
        if action != 'login':
            if user.exists():
                raise serializers.ValidationError("User already exists! Please login")
        elif not user.exists():
            raise serializers.ValidationError("User does not exists! Please Register")
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
