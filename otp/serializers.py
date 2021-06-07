from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status

from retailer_to_sp.models import Shop
from .models import PhoneOTP

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
        # If registration specific otp
        if action != 1:
            # If user already exists
            if user.exists():
                raise serializers.ValidationError("User already exists! Please login")
        # If login specific otp and user does not exists
        elif not user.exists():
            raise serializers.ValidationError("User does not exists! Please Register")
        # If user exists and pos login request
        elif app_type == 2:
            # check shop for pos login
            if not (Shop.objects.filter(shop_owner=user.last(), shop_type__shop_type='f').exists() or
                    Shop.objects.filter(related_users=user.last(), shop_type__shop_type='f').exists()):
                raise serializers.ValidationError("Shop Doesn't Exist!")
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
