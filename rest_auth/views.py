from django.contrib.auth import (login as django_login, logout as django_logout, get_user_model)
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters

from rest_framework import status, authentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from otp.views import RequestOTPCls
from pos.common_functions import filter_pos_shop, check_pos_shop
from marketing.models import ReferralCode

from .app_settings import (UserDetailsSerializer, LoginSerializer, PasswordResetConfirmSerializer,
                           PasswordChangeSerializer, create_token)
from .serializers import (MlmOtpLoginSerializer, MlmResponseSerializer, LoginResponseSerializer,
                          PosLoginResponseSerializer, RetailUserDetailsSerializer, api_serializer_errors,
                          PosOtpLoginSerializer, EcomOtpLoginSerializer, EcomAccessSerializer)
from .models import TokenModel
from .utils import jwt_encode

UserModel = get_user_model()

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters(
        'password', 'old_password', 'new_password1', 'new_password2'
    )
)

APP_TYPES = ['0', '1', '2', '3']

APPLICATION_LOGIN_SERIALIZERS_MAP = {
    '0': LoginSerializer,
    '1': MlmOtpLoginSerializer,
    '2': PosOtpLoginSerializer,
    '3_0': LoginSerializer,
    '3_1': EcomOtpLoginSerializer
}
APPLICATION_LOGIN_RESPONSE_SERIALIZERS_MAP = {
    '0': LoginResponseSerializer,
    '1': MlmResponseSerializer,
    '2': PosLoginResponseSerializer,
    '3': LoginResponseSerializer,
}


class LoginView(GenericAPIView):
    """
    Check the credentials and return the REST Token
    if the credentials are valid and authenticated.
    Calls Django Auth login method to register User ID
    in Django session framework

    Accept POST parameters based on serializers for different applications "app_type"
    Return the REST Framework Token Object's key.
    """
    permission_classes = (AllowAny,)
    token_model = TokenModel
    queryset = TokenModel.objects.all()

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    def get_serializer_class(self):
        """
        Return Serializer Class Based On App Type Requested
        """
        app = self.request.data.get('app_type', '0')
        app = app if app in APP_TYPES else '0'
        if app == '3':
            login_with_otp = self.request.data.get('login_with_otp', '0')
            app = app + '_' + str(login_with_otp)
        return APPLICATION_LOGIN_SERIALIZERS_MAP[app]

    def get_response_serializer(self):
        """
        Return Response Serializer Class Based On App Type Requested
        """
        app = self.request.data.get('app_type', '0')
        app = app if app in APPLICATION_LOGIN_RESPONSE_SERIALIZERS_MAP else '0'
        return APPLICATION_LOGIN_RESPONSE_SERIALIZERS_MAP[app]

    def post(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=self.request.data, context={'request': request})
        if serializer.is_valid():
            user, token = self.login(serializer)
            return self.get_response(user, token)
        else:
            return api_serializer_errors(serializer.errors)

    def login(self, serializer):
        """
        General Login Process
        """
        user = serializer.validated_data['user']
        token = jwt_encode(user) if getattr(settings, 'REST_USE_JWT', False) else create_token(self.token_model, user)
        if getattr(settings, 'REST_SESSION_LOGIN', True):
            django_login(self.request, user)
        return user, token

    def get_response(self, user, token):
        """
        Get Response Based on Authentication and App Type Requested
        """
        token = token if getattr(settings, 'REST_USE_JWT', False) else user.auth_token.key
        app_type = self.request.data.get('app_type', 0)
        shop_object = None
        if app_type == '2':
            qs = filter_pos_shop(user)
            shop_object = qs.last()

        response_serializer_class = self.get_response_serializer()
        response_serializer = response_serializer_class(instance={'user': user, 'token': token,
                                                                  'shop_object': shop_object, 'action': 1})
        return Response({'is_success': True, 'message': ['Logged In Successfully!'],
                         'response_data': [response_serializer.data]}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    Calls Django logout method and delete the Token object
    assigned to the current User object.

    Accepts/Returns nothing.
    """
    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        if getattr(settings, 'ACCOUNT_LOGOUT_ON_GET', False):
            response = self.logout(request)
        else:
            response = self.http_method_not_allowed(request, *args, **kwargs)

        return self.finalize_response(request, response, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.logout(request)

    @staticmethod
    def logout(request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, ObjectDoesNotExist):
            pass

        django_logout(request)

        return Response({'is_success': True, 'message': ['Logged Out Successfully!'], 'response_data': None},
                        status=status.HTTP_200_OK)


class UserDetailsView(RetrieveUpdateAPIView):
    """
    Reads and updates UserModel fields
    Accepts GET, PUT, PATCH methods.

    Default accepted fields: username, first_name, last_name
    Default display fields: pk, username, email, first_name, last_name
    Read-only fields: pk, email

    Returns UserModel fields.
    """
    serializer_class = UserDetailsSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (authentication.TokenAuthentication,)

    def get_object(self):
        return self.request.user

    def get_queryset(self):
        """
        Adding this method since it is sometimes called when using
        django-rest-swagger
        https://github.com/Tivix/django-rest-auth/issues/275
        """
        return get_user_model().objects.none()


class PasswordResetConfirmView(GenericAPIView):
    """
    Password reset e-mail link is confirmed, therefore
    this resets the user's password.

    Accepts the following POST parameters: token, uid,
        new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(PasswordResetConfirmView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'is_success': True, 'message': ['New password has been saved.'], 'response_data': None},
                            status=status.HTTP_200_OK)
        else:
            return api_serializer_errors(serializer.errors)


class PasswordChangeView(GenericAPIView):
    """
    Calls Django Auth SetPasswordForm save method.

    Accepts the following POST parameters: new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = PasswordChangeSerializer
    permission_classes = (IsAuthenticated,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(PasswordChangeView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({'is_success': True, 'message': ['New password has been saved.'], 'response_data': None},
                            status=status.HTTP_200_OK)
        else:
            return api_serializer_errors(serializer.errors)


class RetailerUserDetailsView(GenericAPIView):
    """
    Retailer Account Info API
    """
    serializer_class = RetailUserDetailsSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (authentication.TokenAuthentication,)

    @check_pos_shop
    def get(self, request, *args, **kwargs):
        """
        request:- request object
        *args:-  non keyword argument
        **kwargs:- keyword argument
        """
        user = self.request.user
        serializer = self.serializer_class(user, context={'shop': kwargs['shop']})
        return Response(serializer.data)


class EcomAccessView(APIView):
    serializer_class = EcomAccessSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        """
            Start access to ecom
        """
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user_exists, is_ecom, is_mlm, send_otp, msg, status_code = False, False, False, False, {'is_success': True,
                                                                                                    'message': []}, status.HTTP_200_OK
            data = serializer.data
            user = UserModel.objects.filter(phone_number=data['phone_number']).last()
            # If user exists
            if user:
                user_exists, is_ecom, is_mlm, send_otp = True, user.is_ecom_user, ReferralCode.is_marketing_user(
                    user), not user.is_ecom_user
                # Send otp if first time ecom login - to validate and add pswd
                send_otp = 1 if not is_ecom else 0
            # If new user - Send otp - to validate and add pswd
            else:
                send_otp = 1
            if send_otp:
                msg, status_code = RequestOTPCls.process_otp_request(data['phone_number'], "1",'3')
            msg['response_data'] = {'user_exists': user_exists, 'is_ecom': is_ecom, 'is_mlm': is_mlm}
            return Response(msg, status_code)
        else:
            return api_serializer_errors(serializer.errors)
