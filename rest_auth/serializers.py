import logging
from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode as uid_decoder
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text
from django.core.validators import RegexValidator
from rest_framework import serializers, exceptions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status

try:
    from allauth.account import app_settings as allauth_settings
    from allauth.utils import (email_address_exists,
                               get_username_max_length)
    from allauth.account.adapter import get_adapter
    from allauth.account.utils import setup_user_email
    from allauth.socialaccount.helpers import complete_social_login
    from allauth.socialaccount.models import SocialAccount
    from allauth.socialaccount.providers.base import AuthProcess
except ImportError:
    raise ImportError("allauth needs to be added to INSTALLED_APPS.")

from .models import TokenModel
from .utils import import_callable

from otp.models import PhoneOTP
from otp.views import ValidateOTPInternal
from marketing.models import ReferralCode, RewardPoint, Referral, Profile
from pos.common_functions import filter_pos_shop

# Get the UserModel
UserModel = get_user_model()

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

class LoginSerializer(serializers.Serializer):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    username = serializers.CharField(
        validators=[phone_regex],
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=True
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def _validate_email(self, email, password):

        if email and password:
            user = authenticate(email=email, password=password)
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg)

        return user

    def _validate_username(self, username, password):

        if username and password:
            user = authenticate(username=username, password=password)
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg)
        return user

    def _validate_username_email(self, username, email, password):

        if email and password:
            user = authenticate(email=email, password=password)
        elif username and password:
            user = authenticate(username=username, password=password)
        else:
            msg = _('Must include either "username" or "email" and "password".')
            raise serializers.ValidationError(msg)
        return user

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')

        user = None

        if 'allauth' in settings.INSTALLED_APPS:
            from allauth.account import app_settings

            # Authentication through email
            if app_settings.AUTHENTICATION_METHOD == app_settings.AuthenticationMethod.EMAIL:
                user = self._validate_email(email, password)

            # Authentication through username
            elif app_settings.AUTHENTICATION_METHOD == app_settings.AuthenticationMethod.USERNAME:
                user = self._validate_username(username, password)

            # Authentication through either username or email
            else:
                user = self._validate_username_email(username, email, password)

        else:
            # Authentication without using allauth
            if email:
                try:
                    username = UserModel.objects.get(email__iexact=email).get_username()
                except UserModel.DoesNotExist:
                    pass

            if username:
                user = self._validate_username_email(username, '', password)

        # Did we get back an active user?
        if user:
            if not user.is_active:
                msg = _('User account is disabled.')
                raise serializers.ValidationError(msg)
        else:
            msg = _('Invalid username or password.')
            raise exceptions.ValidationError(msg)

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
            from allauth.account import app_settings
            if app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY:
                email_address = user.emailaddress_set.get(email=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(_('E-mail is not verified.'))
        attrs['user'] = user
        return attrs


class MlmOtpLoginSerializer(serializers.Serializer):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    username = serializers.CharField(
        validators=[phone_regex],
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=True
    )
    otp = serializers.CharField(max_length=10)

    def validate(self, attrs):
        number = attrs.get('username')

        user = UserModel.objects.filter(phone_number=number).last()
        if not user or (user and not ReferralCode.is_marketing_user(user)):
            raise serializers.ValidationError("You are not registered for rewards. Please register first.")

        phone_otp = PhoneOTP.objects.filter(phone_number=number).last()
        if phone_otp:
            # verify if entered otp was sent to the user
            to_verify_otp = ValidateOTPInternal()
            msg, status_code = to_verify_otp.verify(attrs.get('otp'), phone_otp)
            if status_code != 200:
                message = msg['message'] if 'message' in msg else "Some error occurred. Please try again later"
                raise serializers.ValidationError(message)
        else:
            raise serializers.ValidationError("Invalid data")

        attrs['user'] = user
        return attrs


class PosOtpLoginSerializer(serializers.Serializer):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    username = serializers.CharField(
        validators=[phone_regex],
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=True
    )
    otp = serializers.CharField(max_length=10)
    app_type = serializers.IntegerField(required=False)

    def validate(self, attrs):
        """
        Verify entered otp and user for login
        """

        number = attrs.get('username')
        user = UserModel.objects.filter(phone_number=number).last()
        if not user:
            raise serializers.ValidationError("You are not registered on GramFactory.")
        # Check Shop
        qs = filter_pos_shop(user)
        if not qs.exists():
            raise serializers.ValidationError("You do not have any shop registered for GramFactory POS.")

        phone_otp = PhoneOTP.objects.filter(phone_number=number).last()
        if phone_otp:
            # verify if entered otp was sent to the user
            to_verify_otp = ValidateOTPInternal()
            msg, status_code = to_verify_otp.verify(attrs.get('otp'), phone_otp)
            if status_code != 200:
                message = msg['message'] if 'message' in msg else "Some error occured. Please try again later"
                raise serializers.ValidationError(message)
        else:
            raise serializers.ValidationError("Invalid data")

        attrs['user'] = user
        return attrs


class MlmResponseSerializer(serializers.Serializer):
    access_token = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    referral_code = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    email_id = serializers.SerializerMethodField()

    @staticmethod
    def get_access_token(obj):
        return obj['token']

    @staticmethod
    def get_phone_number(obj):
        return obj['user'].phone_number

    @staticmethod
    def get_referral_code(obj):
        referral_code_obj = ReferralCode.objects.filter(user_id=obj['user']).last()
        return referral_code_obj.referral_code if referral_code_obj else ''

    @staticmethod
    def get_name(obj):
        return obj['user'].first_name.capitalize() if obj['user'].first_name else ''

    @staticmethod
    def get_email_id(obj):
        return obj['user'].email if obj['user'].email else ''


class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.SerializerMethodField()

    def get_access_token(self, obj):
        return obj['token']


class PosLoginResponseSerializer(serializers.Serializer):
    access_token = serializers.SerializerMethodField()
    shop_id = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()

    @staticmethod
    def get_access_token(obj):
        return obj['token']

    @staticmethod
    def get_shop_id(obj):
        return obj['shop_object'].id if obj['shop_object'] else ''

    @staticmethod
    def get_shop_name(obj):
        return obj['shop_object'].shop_name if obj['shop_object'] else ''


class TokenSerializer(serializers.ModelSerializer):
    """
    Serializer for Token model.
    """

    class Meta:
        model = TokenModel
        fields = ('key',)


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    User model w/o password
    """

    class Meta:
        model = UserModel
        fields = ('pk', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('email',)


class RetailUserDetailsSerializer(serializers.ModelSerializer):
    """
    Retailer User Serializer
    """
    shop_name = serializers.SerializerMethodField()
    shop_image = serializers.SerializerMethodField()
    shop_owner_name = serializers.SerializerMethodField()
    shop_shipping_address = serializers.SerializerMethodField()

    def get_shop_name(self, obj):
        """
        obj:-User object
        return:- shop name
        """
        shop = self.context.get('shop')
        return shop.shop_name

    def get_shop_image(self, obj):
        """
        obj:-User object
        return:- shop image
        """
        shop = self.context.get('shop')
        try:
            return shop.shop_name_photos.all()[0].shop_photo.url
        except Exception as e:
            error_logger.info(e)
        return None

    def get_shop_owner_name(self, obj):
        """
        obj:-User object
        return:- owner name
        """
        shop = self.context.get('shop')
        try:
            return shop.shop_owner.first_name + ' ' + shop.shop_owner.last_name
        except Exception as e:
            error_logger.info(e)
        return None

    def get_shop_shipping_address(self, obj):
        """
        obj:-User object
        return:- shipping address
        """
        shop = self.context.get('shop')
        try:
            return shop.get_shop_shipping_address
        except Exception as e:
            error_logger.info(e)
        return None

    class Meta:
        model = UserModel
        fields = ('pk', 'email', 'first_name', 'last_name', 'shop_name', 'shop_image',
                  'shop_owner_name', 'shop_shipping_address',)


class JWTSerializer(serializers.Serializer):
    """
    Serializer for JWT authentication.
    """
    token = serializers.CharField()
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        """
        Required to allow using custom USER_DETAILS_SERIALIZER in
        JWTSerializer. Defining it here to avoid circular imports
        """
        rest_auth_serializers = getattr(settings, 'REST_AUTH_SERIALIZERS', {})
        JWTUserDetailsSerializer = import_callable(
            rest_auth_serializers.get('USER_DETAILS_SERIALIZER', UserDetailsSerializer)
        )
        user_data = JWTUserDetailsSerializer(obj['user'], context=self.context).data
        return user_data


# Todo remove
class PasswordResetSerializer(serializers.ModelSerializer):
    """
    Serializer for requesting an OTP for password reset.
    """

    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )


# Todo remove
class PasswordResetValidateSerializer(serializers.ModelSerializer):
    """
    Validate the otp send to mobile number for password reset
    """

    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
            'otp'
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset e-mail.
    """
    new_password1 = serializers.CharField(max_length=128)
    new_password2 = serializers.CharField(max_length=128)
    uid = serializers.CharField()
    token = serializers.CharField()

    set_password_form_class = SetPasswordForm

    def custom_validation(self, attrs):
        pass

    def validate(self, attrs):
        self._errors = {}

        # Decode the uidb64 to uid to get User object
        try:
            uid = force_text(uid_decoder(attrs['uid']))
            self.user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            raise ValidationError({'uid': ['Invalid value']})

        self.custom_validation(attrs)
        # Construct SetPasswordForm instance
        self.set_password_form = self.set_password_form_class(
            user=self.user, data=attrs
        )
        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)
        if not default_token_generator.check_token(self.user, attrs['token']):
            raise ValidationError({'token': ['Invalid value']})

        return attrs

    def save(self):
        return self.set_password_form.save()


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128)
    new_password1 = serializers.CharField(max_length=128)
    new_password2 = serializers.CharField(max_length=128)

    set_password_form_class = SetPasswordForm

    def __init__(self, *args, **kwargs):
        self.old_password_field_enabled = getattr(
            settings, 'OLD_PASSWORD_FIELD_ENABLED', False
        )
        self.logout_on_password_change = getattr(
            settings, 'LOGOUT_ON_PASSWORD_CHANGE', False
        )
        super(PasswordChangeSerializer, self).__init__(*args, **kwargs)

        if not self.old_password_field_enabled:
            self.fields.pop('old_password')

        self.request = self.context.get('request')
        self.user = getattr(self.request, 'user', None)

    def validate_old_password(self, value):
        invalid_password_conditions = (
            self.old_password_field_enabled,
            self.user,
            not self.user.check_password(value)
        )

        if all(invalid_password_conditions):
            raise serializers.ValidationError('Invalid password')
        return value

    def validate(self, attrs):
        self.set_password_form = self.set_password_form_class(
            user=self.user, data=attrs
        )

        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)
        return attrs

    def save(self):
        self.set_password_form.save()
        if not self.logout_on_password_change:
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(self.request, self.user)


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
