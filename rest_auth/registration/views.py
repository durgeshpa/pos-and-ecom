from django.conf import settings
from django.db.models import Q
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

from allauth.account.adapter import get_adapter
from allauth.account.views import ConfirmEmailView
from allauth.account.utils import complete_signup
from allauth.account import app_settings as allauth_settings
from allauth.socialaccount import signals
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from allauth.socialaccount.models import SocialAccount
from marketing.models import MLMUser, Referral
from marketing.validation import ValidateOTP
from marketing.views import save_user_referral_code

from rest_auth.app_settings import (TokenSerializer,
                                    JWTSerializer,
                                    create_token)
from rest_auth.models import TokenModel
from rest_auth.registration.serializers import (VerifyEmailSerializer,
                                                SocialLoginSerializer,
                                                SocialAccountSerializer,
                                                SocialConnectSerializer
                                                )
from rest_auth.utils import jwt_encode
from rest_auth.views import LoginView
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from .app_settings import RegisterSerializer, register_permission_classes

from otp.models import PhoneOTP

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters('password1', 'password2')
)


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = register_permission_classes()
    token_model = TokenModel

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(RegisterView, self).dispatch(*args, **kwargs)

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
        try:
            phone_number = data.get('username')
            # otp = data.get('otp')
            referral_code = data.get('referral_code')

            # if otp is None:
            #     return Response({'message': VALIDATION_ERROR_MESSAGES['Enter_OTP'],
            #                      'is_success': False, 'response_data': None},
            #                     status=status.HTTP_400_BAD_REQUEST)
            if referral_code:
                """
                    checking whether REFERRAL CODE is valid or not.
                """
                user_id = MLMUser.objects.filter(referral_code=referral_code)
                if not user_id:
                    return Response({'message': VALIDATION_ERROR_MESSAGES['Referral_code'],
                                     'is_success': False,
                                     'response_data': None},
                                    status=status.HTTP_400_BAD_REQUEST)
            user_phone = MLMUser.objects.filter(Q(phone_number=phone_number))
            if user_phone.exists():
                user = user_phone.last()
                if user.status == 1:
                    return Response({'message': VALIDATION_ERROR_MESSAGES['User_Already_Exist'],
                                     'is_success': False,
                                     'response_data': None},
                                    status=status.HTTP_409_CONFLICT)

                if not user.referral_code or user.referral_code == '':
                    save_user_referral_code(phone_number)
                user_referral_code = user.referral_code
            else:
                user_referral_code = save_user_referral_code(phone_number)

            referred = 1 if referral_code else 0
            msg = ValidateOTP(phone_number, otp, referred)
            if referral_code:
                Referral.store_parent_referral_user(referral_code, user_referral_code)
            return Response(msg.data, status=msg.status_code)

        except Exception as e:
            return Response({'message': "Data is not valid.", 'is_success': False, 'response_data': None},
                            status=status.HTTP_403_FORBIDDEN)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            app_name = request.query_params['app']
            if app_name == '2':
                self.mlm_user_registration(request.data)
            number = request.data.get('username')
            user_otp = PhoneOTP.objects.filter(phone_number=number).last()
            if user_otp and user_otp.is_verified:
                user = self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                msg = {'is_success': True,
                        'message': ['Successfully signed up!'],
                        'response_data':[{'access_token':self.get_response_data(user)['key']}] }
                return Response(msg,
                                status=status.HTTP_201_CREATED,
                                headers=headers)
            else:
                msg = {'is_success': False,
                        'message': ['Please verify your mobile number first!'],
                        'response_data': None }
                return Response(msg,
                                status=status.HTTP_406_NOT_ACCEPTABLE)

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
