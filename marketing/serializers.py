from rest_framework import serializers
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


class SendSmsOTPSerializer(serializers.ModelSerializer):
    """
    Send OTP SMS to number
    """

    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )
