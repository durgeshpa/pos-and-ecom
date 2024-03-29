from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.auth import login as django_login

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import CreateAPIView, ListAPIView, GenericAPIView
from rest_framework.exceptions import NotFound
from rest_framework import status

from allauth.account.adapter import get_adapter
from allauth.account.views import ConfirmEmailView
from allauth.account.utils import complete_signup
from allauth.account import app_settings as allauth_settings
from allauth.socialaccount import signals
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from allauth.socialaccount.models import SocialAccount

from rest_auth.app_settings import create_token
from rest_auth.models import Token
from rest_auth.registration.serializers import (VerifyEmailSerializer, SocialLoginSerializer, SocialAccountSerializer,
                                                SocialConnectSerializer, MlmOtpRegisterSerializer, EcomRegisterSerializer)
from rest_auth.serializers import MlmResponseSerializer, LoginResponseSerializer, api_serializer_errors
from rest_auth.utils import jwt_encode, default_create_token
from rest_auth.views import LoginView

from .app_settings import RegisterSerializer, register_permission_classes

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters('password1', 'password2')
)

APPLICATION_REGISTRATION_SERIALIZERS_MAP = {
    '0': RegisterSerializer,
    '1': MlmOtpRegisterSerializer,
    '3': EcomRegisterSerializer
}
APPLICATION_REGISTER_RESPONSE_SERIALIZERS_MAP = {
    '0': LoginResponseSerializer,
    '1': MlmResponseSerializer,
    '3': LoginResponseSerializer
}


class RegisterView(CreateAPIView):
    permission_classes = register_permission_classes()
    token_model = Token

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(RegisterView, self).dispatch(*args, **kwargs)

    def get_serializer_class(self):
        """
        Return Serializer Class Based On App Type Requested
        """
        app = self.request.data.get('app_type', '0')
        app = app if app in APPLICATION_REGISTRATION_SERIALIZERS_MAP else '0'
        return APPLICATION_REGISTRATION_SERIALIZERS_MAP[app]

    def get_response_serializer(self):
        """
        Return Response Serializer Class Based On App Type Requested
        """
        app = self.request.data.get('app_type', '0')
        app = app if app in APPLICATION_REGISTER_RESPONSE_SERIALIZERS_MAP else '0'
        return APPLICATION_REGISTER_RESPONSE_SERIALIZERS_MAP[app]

    def create(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        if serializer.is_valid():
            user, token = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return self.get_response(user, headers, token.key)
        else:
            return api_serializer_errors(serializer.errors)

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        token = jwt_encode(user) if getattr(settings, 'REST_USE_JWT', False) else default_create_token(user)
        data = serializer.data
        if 'user_exists' in data and data['user_exists'] and getattr(settings, 'REST_SESSION_LOGIN', True):
            django_login(self.request, user)
        else:
            complete_signup(self.request._request, user, allauth_settings.EMAIL_VERIFICATION, None)
        return user, token

    def get_response(self, user, headers, token):
        """
        Get Response Based on Authentication and App Type Requested
        """
        # token = token if getattr(settings, 'REST_USE_JWT', False) else user.auth_token.key
        response_serializer_class = self.get_response_serializer()
        response_serializer = response_serializer_class(instance={'user': user, 'token': token})
        return Response({'is_success': True, 'message': ['Signed Up Successfully!'],
                         'response_data': [response_serializer.data]}, status=status.HTTP_201_CREATED, headers=headers)


class VerifyEmailView(APIView, ConfirmEmailView):
    permission_classes = (AllowAny,)
    allowed_methods = ('POST', 'OPTIONS', 'HEAD')

    def get_serializer(self, *args, **kwargs):
        return VerifyEmailSerializer(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.kwargs['key'] = serializer.validated_data['key']
        confirmation = self.get_object()
        confirmation.confirm(self.request)
        return Response({'detail': _('ok')}, status=status.HTTP_200_OK)


class SocialLoginView(LoginView):
    """
    class used for social authentications
    example usage for facebook with access_token
    -------------
    from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter

    class FacebookLogin(SocialLoginView):
        adapter_class = FacebookOAuth2Adapter
    -------------

    example usage for facebook with code

    -------------
    from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
    from allauth.socialaccount.providers.oauth2.client import OAuth2Client

    class FacebookLogin(SocialLoginView):
        adapter_class = FacebookOAuth2Adapter
        client_class = OAuth2Client
        callback_url = 'localhost:8000'
    -------------
    """
    serializer_class = SocialLoginSerializer

    def process_login(self):
        get_adapter(self.request).login(self.request, self.user)


class SocialConnectView(LoginView):
    """
    class used for social account linking

    example usage for facebook with access_token
    -------------
    from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter

    class FacebookConnect(SocialConnectView):
        adapter_class = FacebookOAuth2Adapter
    -------------
    """
    serializer_class = SocialConnectSerializer
    permission_classes = (IsAuthenticated,)

    def process_login(self):
        get_adapter(self.request).login(self.request, self.user)


class SocialAccountListView(ListAPIView):
    """
    List SocialAccounts for the currently logged in user
    """
    serializer_class = SocialAccountSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user)


class SocialAccountDisconnectView(GenericAPIView):
    """
    Disconnect SocialAccount from remote service for
    the currently logged in user
    """
    serializer_class = SocialConnectSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        accounts = self.get_queryset()
        account = accounts.filter(pk=kwargs['pk']).first()
        if not account:
            raise NotFound

        get_social_adapter(self.request).validate_disconnect(account, accounts)

        account.delete()
        signals.social_account_removed.send(
            sender=SocialAccount,
            request=self.request,
            socialaccount=account
        )

        return Response(self.get_serializer(account).data)
