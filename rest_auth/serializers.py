from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode as uid_decoder
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text
from django.core.validators import RegexValidator
from rest_framework import serializers, exceptions
from rest_framework.exceptions import ValidationError

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
from otp.views import ValidateOTP
from marketing.models import ReferralCode, RewardPoint, Referral, Profile
from global_config.models import GlobalConfig
from marketing.views import generate_user_referral_code

# Get the UserModel
UserModel = get_user_model()

class LoginSerializer(serializers.Serializer):
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    username = serializers.CharField(
        validators = [phone_regex],
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=True
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def _validate_email(self, email, password):
        user = None

        if email and password:
            user = authenticate(email=email, password=password)
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg)

        return user

    def _validate_username(self, username, password):
        user = None

        if username and password:
            user = authenticate(username=username, password=password)
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg)
        return user


    def _validate_username_email(self, username, email, password):
        user = None

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


class MlmLoginSerializer(serializers.Serializer):
    """
    Serializer for login with phone number and OTP
    """
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$', message="Phone number is not valid")
    username = serializers.CharField(
        validators=[phone_regex],
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=True
    )
    otp = serializers.CharField(max_length=10)

    def validate(self, attrs):
        """
        Verify entered otp and user for login
        """
        number = attrs.get('username')
        otp = attrs.get('otp')
        user = None

        phone_otps = PhoneOTP.objects.filter(phone_number=number)
        if phone_otps.exists():
            phone_otp = phone_otps.last()
            # verify if entered otp was sent to the user
            to_verify_otp = ValidateOTP()
            msg, status_code = to_verify_otp.verify(otp, phone_otp)
            if status_code == 200:
                user = UserModel.objects.filter(phone_number=number).last()
                if not user:
                    raise serializers.ValidationError("User does not exist. Please sign up!")
            else:
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
    reward = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()

    def get_access_token(self, obj):
        return obj['token']

    def get_phone_number(self, obj):
        return obj['user'].phone_number

    def get_referral_code(self, obj):
        if obj['action'] == 'register':
            # generate unique referral code on registration
            user_referral_code = generate_user_referral_code(obj['user'])
            # welcome reward for new user
            referral_code = obj['referral_code']
            referred = 1 if obj['referral_code'] != '' else 0
            RewardPoint.welcome_reward(obj['user'], referred)
            # add parent referrer if referral code provided
            if referral_code != '':
                Referral.store_parent_referral_user(referral_code, user_referral_code)
            # create new profile for user
            Profile.objects.get_or_create(user=obj['user'])
        referral_code_obj = ReferralCode.objects.filter(user_id=obj['user']).last()
        return referral_code_obj.referral_code if referral_code_obj else ''

    def get_name(self, obj):
        return obj['user'].first_name.capitalize() if obj['user'].first_name else ''

    def get_email_id(self, obj):
        return obj['user'].email if obj['user'].email else ''

    def get_reward(self, obj):
        return GlobalConfig.objects.filter(key='welcome_reward_points_referral').last().value

    def get_discount(self, obj):
        reward =  GlobalConfig.objects.filter(key='welcome_reward_points_referral').last().value
        return int(reward / GlobalConfig.objects.filter(key='used_reward_factor').last().value)


class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.SerializerMethodField()

    def get_access_token(self, obj):
        return obj['token']


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
        read_only_fields = ('email', )


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


class PasswordResetSerializer(serializers.ModelSerializer):
    """
    Serializer for requesting an OTP for password reset.
    """
    class Meta:
        model = PhoneOTP
        fields = (
            'phone_number',
        )

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
