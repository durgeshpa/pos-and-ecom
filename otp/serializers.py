from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import PhoneOTP

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

class RevokeOTPSerializer(serializers.ModelSerializer):
    """
    Recreate the OTP for user
    """
    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )
