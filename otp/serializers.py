from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status

from .models import PhoneOTP
from pos.common_functions import filter_pos_shop
from marketing.models import ReferralCode

UserModel = get_user_model()


class PhoneOTPValidateSerializer(serializers.ModelSerializer):
    """
    validate the otp sent to number
    """

    class Meta:
        model = PhoneOTP
        fields = ('phone_number', 'otp')


class SendSmsOTPSerializer(serializers.ModelSerializer):
    """
    Send OTP SMS to number
    """

    class Meta:
        model = PhoneOTP
        fields = ('phone_number', 'action', 'app_type')

    action = serializers.IntegerField(default=0)
    app_type = serializers.IntegerField(default=0)

    def validate(self, attrs):
        """
        OTP should not be sent to existing user from registration screen
        """
        number = attrs.get('phone_number')
        action = attrs.get('action')
        app_type = attrs.get('app_type')
        user = UserModel.objects.filter(phone_number=number).last()

        # Marketing
        if app_type == 1:
            # Registering
            if action == 0 and user and ReferralCode.is_marketing_user(user):
                raise serializers.ValidationError("You are already registered for rewards! Please login.")
            # Login
            elif action == 1 and (not user or not ReferralCode.is_marketing_user(user)):
                raise serializers.ValidationError("You are not registered for rewards. Please register first.")

        # POS Login
        elif app_type == 2:
            # Registering
            if action == 0:
                pass
            # Login
            elif action == 1:
                if not user:
                    raise serializers.ValidationError("You are not registered on GramFactory.")
                # Check Shop
                qs = filter_pos_shop(user)
                if not qs.exists():
                    raise serializers.ValidationError("You do not have any shop registered for GramFactory POS.")
        # Retailer App
        elif app_type == 0:
            # Registering
            if action == 0 and user:
                raise serializers.ValidationError("User already registered! Please login.")
            # Login
            elif action == 1 and not user:
                raise serializers.ValidationError("User not registered. Please register first.")
        return attrs


def api_serializer_errors(s_errors):
    """
        Invalid request payload
    """
    errors = []
    for field in s_errors:
        for error in s_errors[field]:
            errors.append(error if 'non_field_errors' in field else ''.join('{} : {}'.format(field, error)))
    return Response({'is_success': False, 'message': errors, 'response_data': None},
                    status=status.HTTP_406_NOT_ACCEPTABLE)


# Todo remove
class ResendSmsOTPSerializer(serializers.ModelSerializer):
    """
    Resend OTP SMS to number
    """

    class Meta:
        model = PhoneOTP
        fields = ('phone_number',)


# Todo remove
class ResendVoiceOTPSerializer(serializers.ModelSerializer):
    """
    Resend OTP voice call to number
    """

    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )
