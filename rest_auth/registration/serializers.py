from requests.exceptions import HTTPError

from django.http import HttpRequest
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from rest_framework import serializers

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

from marketing.models import ReferralCode
from shops.models import Shop
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from otp.models import PhoneOTP
from otp.views import ValidateOTPInternal
UserModel = get_user_model()


class SocialAccountSerializer(serializers.ModelSerializer):
    """
    serialize allauth SocialAccounts for use with a REST API
    """
    class Meta:
        model = SocialAccount
        fields = (
            'id',
            'provider',
            'uid',
            'last_login',
            'date_joined',
        )


class SocialLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True)

    def _get_request(self):
        request = self.context.get('request')
        if not isinstance(request, HttpRequest):
            request = request._request
        return request

    def get_social_login(self, adapter, app, token, response):
        """
        :param adapter: allauth.socialaccount Adapter subclass.
            Usually OAuthAdapter or Auth2Adapter
        :param app: `allauth.socialaccount.SocialApp` instance
        :param token: `allauth.socialaccount.SocialToken` instance
        :param response: Provider's response for OAuth1. Not used in the
        :returns: A populated instance of the
            `allauth.socialaccount.SocialLoginView` instance
        """
        request = self._get_request()
        social_login = adapter.complete_login(request, app, token, response=response)
        social_login.token = token
        return social_login

    def validate(self, attrs):
        view = self.context.get('view')
        request = self._get_request()

        if not view:
            raise serializers.ValidationError(
                _("View is not defined, pass it as a context variable")
            )

        adapter_class = getattr(view, 'adapter_class', None)
        if not adapter_class:
            raise serializers.ValidationError(_("Define adapter_class in view"))

        adapter = adapter_class(request)
        app = adapter.get_provider().get_app(request)

        # More info on code vs access_token
        # http://stackoverflow.com/questions/8666316/facebook-oauth-2-0-code-and-token

        # Case 1: We received the access_token
        if attrs.get('access_token'):
            access_token = attrs.get('access_token')

        # Case 2: We received the authorization code
        elif attrs.get('code'):
            self.callback_url = getattr(view, 'callback_url', None)
            self.client_class = getattr(view, 'client_class', None)

            if not self.callback_url:
                raise serializers.ValidationError(
                    _("Define callback_url in view")
                )
            if not self.client_class:
                raise serializers.ValidationError(
                    _("Define client_class in view")
                )

            code = attrs.get('code')

            provider = adapter.get_provider()
            scope = provider.get_scope(request)
            client = self.client_class(
                request,
                app.client_id,
                app.secret,
                adapter.access_token_method,
                adapter.access_token_url,
                self.callback_url,
                scope
            )
            token = client.get_access_token(code)
            access_token = token['access_token']

        else:
            raise serializers.ValidationError(
                _("Incorrect input. access_token or code is required."))

        social_token = adapter.parse_token({'access_token': access_token})
        social_token.app = app

        try:
            login = self.get_social_login(adapter, app, social_token, access_token)
            complete_social_login(request, login)
        except HTTPError:
            raise serializers.ValidationError(_("Incorrect value"))

        if not login.is_existing:
            # We have an account already signed up in a different flow
            # with the same email address: raise an exception.
            # This needs to be handled in the frontend. We can not just
            # link up the accounts due to security constraints
            if allauth_settings.UNIQUE_EMAIL:
                # Do we have an account already with this email address?
                account_exists = get_user_model().objects.filter(
                    email=login.user.email,
                ).exists()
                if account_exists:
                    raise serializers.ValidationError(
                        _("User is already registered with this e-mail address.")
                    )

            login.lookup()
            login.save(request, connect=True)

        attrs['user'] = login.account.user

        return attrs


class SocialConnectMixin(object):
    def get_social_login(self, *args, **kwargs):
        """
        Set the social login process state to connect rather than login
        Refer to the implementation of get_social_login in base class and to the
        allauth.socialaccount.helpers module complete_social_login function.
        """
        social_login = super(SocialConnectMixin, self).get_social_login(*args, **kwargs)
        social_login.state['process'] = AuthProcess.CONNECT
        return social_login


class SocialConnectSerializer(SocialConnectMixin, SocialLoginSerializer):
    pass


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=allauth_settings.USERNAME_REQUIRED
    )
    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED, allow_blank=True)
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    password1 = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    imei_no = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_username(self, username):
        username = get_adapter().clean_username(username)
        return username

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    _("A user is already registered with this e-mail address."))
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        """
        Check For Password Fields Match and OTP verification
        """
        if data['password1'] != data['password2']:
            raise serializers.ValidationError(_("The two password fields didn't match."))

        # OTP should be verified when registering with phone number
        number = data['username']
        user_otp = PhoneOTP.objects.filter(phone_number=number).last()
        if user_otp and user_otp.is_verified:
            pass
        else:
            raise serializers.ValidationError(_("Please verify your mobile number first!"))
        return data

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'imei_no': self.validated_data.get('imei_no', '')
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        return user


class MlmOtpRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=allauth_settings.USERNAME_REQUIRED
    )
    user_exists = serializers.CharField(default=False)
    otp = serializers.CharField(required=True, max_length=6, min_length=6)
    referral_code = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)

    def validate(self, data):
        data['user_exists'] = False
        existing_user = UserModel.objects.filter(phone_number=data['username']).last()
        if existing_user:
            data['user_exists'] = True
            if ReferralCode.is_marketing_user(existing_user):
                raise serializers.ValidationError("You are already registered for rewards! Please login.")

        phone_otp = PhoneOTP.objects.filter(phone_number=data['username']).last()
        if phone_otp:
            to_verify_otp = ValidateOTPInternal()
            msg, status_code = to_verify_otp.verify(data['otp'], phone_otp)
            if status_code != 200:
                message = msg['message'] if 'message' in msg else "Some error occurred. Please try again later"
                raise serializers.ValidationError(message)
        else:
            raise serializers.ValidationError("Invalid OTP")
        return data

    @staticmethod
    def validate_referral_code(value):
        if value:
            user_ref_code = ReferralCode.objects.filter(referral_code=value).last()
            if not user_ref_code:
                raise serializers.ValidationError(VALIDATION_ERROR_MESSAGES['Referral_code'])
        return value

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'imei_no': self.validated_data.get('imei_no', '')
        }

    def save(self, request):
        user = UserModel.objects.filter(phone_number=self.validated_data.get('username', '')).last()
        if not user:
            adapter = get_adapter()
            user = adapter.new_user(request)
            self.cleaned_data = self.get_cleaned_data()
            adapter.save_user(request, user, self)
            setup_user_email(request, user, [])

        ReferralCode.register_user_for_mlm(user, user, self.validated_data.get('referral_code', ''))
        return user


class VerifyEmailSerializer(serializers.Serializer):
    key = serializers.CharField()


class EcomRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=get_username_max_length(), min_length=allauth_settings.USERNAME_MIN_LENGTH, required=allauth_settings.USERNAME_REQUIRED)
    first_name = serializers.CharField(required=True, write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    password1 = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    def validate_username(self, username):
        username = get_adapter().clean_username(username)
        return username

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError(_("The two password fields didn't match."))
        user_otp = PhoneOTP.objects.filter(phone_number=data['username']).last()
        if not user_otp or not user_otp.is_verified:
            raise serializers.ValidationError(_("Please verify your mobile number first!"))
        return data

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'imei_no': self.validated_data.get('imei_no', '')
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        setup_user_email(request, user, [])

        ReferralCode.register_user_for_mlm(user, user, self.validated_data.get('referral_code', ''))
        return user
