from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated)
from rest_framework.generics import CreateAPIView, ListAPIView, GenericAPIView
from rest_framework.exceptions import NotFound
from rest_framework import status

from accounts.models import User
from allauth.account.adapter import get_adapter
from allauth.account.views import ConfirmEmailView
from allauth.account.utils import complete_signup
from allauth.account import app_settings as allauth_settings
from allauth.socialaccount import signals
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from allauth.socialaccount.models import SocialAccount
from global_config.models import GlobalConfig
from marketing.models import Referral, ReferralCode, RewardPoint
from marketing.views import save_user_referral_code

from rest_auth.app_settings import (TokenSerializer,
                                    JWTSerializer,
                                    create_token)
from rest_auth.models import TokenModel
from rest_auth.registration.serializers import (VerifyEmailSerializer,
                                                SocialLoginSerializer,
                                                SocialAccountSerializer,
                                                SocialConnectSerializer,
                                                MlmRegisterSerializer
                                                )
from rest_auth.utils import jwt_encode
from rest_auth.views import LoginView
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from .app_settings import RegisterSerializer, register_permission_classes

from otp.models import PhoneOTP

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters('password1', 'password2')
)

APPLICATION_REGISTRATION_SERIALIZERS_MAP = {
    '0' : RegisterSerializer,
    '1' : MlmRegisterSerializer
}


class RegisterView(CreateAPIView):
    permission_classes = register_permission_classes()
    token_model = TokenModel

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(RegisterView, self).dispatch(*args, **kwargs)

    def get_serializer_class(self):
        app = self.request.data.get('app_type', '0')
        app = app if app in APPLICATION_REGISTRATION_SERIALIZERS_MAP else '0'
        return APPLICATION_REGISTRATION_SERIALIZERS_MAP[app]

    def get_response_data(self, user):
        if allauth_settings.EMAIL_VERIFICATION == \
                allauth_settings.EmailVerificationMethod.MANDATORY:
            return {"detail": _("Verification e-mail sent.")}

        if getattr(settings, 'REST_USE_JWT', False):
            data = {
                'user': user,
                'token': self.token
            }
            return JWTSerializer(data).data
        else:
            return TokenSerializer(user.auth_token).data

    def mlm_user_registration(self, data):
        phone_number = data.get('username')
        referral_code = data.get('referral_code')

        user_referral_code = save_user_referral_code(phone_number)

        referred = 1 if referral_code else 0
        user_obj = User.objects.get(phone_number=phone_number)
        RewardPoint.welcome_reward(user_obj, referred)
        if referral_code:
            Referral.store_parent_referral_user(referral_code, user_referral_code)

        user_id = User.objects.values('id').filter(phone_number=phone_number)
        email_id = data.get('email')
        mail_id = email_id if email_id else ''
        referral_code = ReferralCode.objects.values('referral_code').filter(user_id_id=user_id[0]['id'])
        # to get reward from global configuration
        reward = GlobalConfig.objects.filter(key='welcome_reward_points_referral').last().value
        # to get discount from global configuration
        discount = int(reward / GlobalConfig.objects.filter(key='used_reward_factor').last().value)
        mlm_response_data = {'referral_code': referral_code[0]['referral_code'],
                             'phone_number': phone_number,
                             'email_id': mail_id,
                             'reward': reward,
                             'discount': discount}
        return mlm_response_data

    def create(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        if serializer.is_valid():
            number = request.data.get('username')
            user_otp = PhoneOTP.objects.filter(phone_number=number).last()
            if user_otp and user_otp.is_verified:
                user = self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                if serializer_class == MlmRegisterSerializer:
                    response_data = self.mlm_user_registration(request.data)
                    msg = {'is_success': True,
                           'message': 'Successfully signed up!',
                           'response_data': [{'access_token': self.get_response_data(user)['key'],
                                              'referral_code': response_data.get('referral_code'),
                                              'phone_number': response_data.get('phone_number'),
                                              'email_id': response_data.get('email_id'),
                                              'reward': response_data.get('reward'),
                                              'discount': response_data.get('discount')
                                              }]
                           }
                    return Response(msg,
                                    status=status.HTTP_201_CREATED,
                                    headers=headers)
                msg = {'is_success': True,
                       'message': ['Successfully signed up!'],
                       'response_data': [{'access_token': self.get_response_data(user)['key']}]}
                return Response(msg,
                                status=status.HTTP_201_CREATED,
                                headers=headers)
            else:
                msg = {'is_success': False,
                       'message': ['Please verify your mobile number first!'],
                       'response_data': None}
                return Response(msg,
                                status=status.HTTP_406_NOT_ACCEPTABLE)
            user = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            msg = {'is_success': True,
                    'message': ['Successfully signed up!'],
                    'response_data':[{'access_token':self.get_response_data(user)['key']}] }
            return Response(msg,
                            status=status.HTTP_201_CREATED,
                            headers=headers)

        else:
            errors = []
            for field in serializer.errors:
                for error in serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': [error for error in errors],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        if getattr(settings, 'REST_USE_JWT', False):
            self.token = jwt_encode(user)
        else:
            create_token(self.token_model, user, serializer)

        complete_signup(self.request._request, user,
                        allauth_settings.EMAIL_VERIFICATION,
                        None)
        return user

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
