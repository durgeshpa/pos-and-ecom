import datetime

from django.contrib.auth import (login as django_login, logout as django_logout)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.db.models import Q

from rest_framework import status, authentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication

from otp.sms import SendSms
from otp.models import PhoneOTP
from accounts.tokens import account_activation_token
from shops.models import Shop

from .app_settings import (UserDetailsSerializer, LoginSerializer, PasswordResetSerializer,
                           PasswordResetConfirmSerializer, PasswordChangeSerializer, create_token)
from .serializers import (PasswordResetValidateSerializer, OtpLoginSerializer, MlmResponseSerializer,
                          LoginResponseSerializer, PosLoginResponseSerializer, RetailUserDetailsSerializer,
                          api_serializer_errors)
from .models import TokenModel
from .utils import jwt_encode

UserModel = get_user_model()

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters(
        'password', 'old_password', 'new_password1', 'new_password2'
    )
)

APPLICATION_LOGIN_SERIALIZERS_MAP = {
    '0': LoginSerializer,
    '1': OtpLoginSerializer,
    '2': OtpLoginSerializer
}
APPLICATION_LOGIN_RESPONSE_SERIALIZERS_MAP = {
    '0': LoginResponseSerializer,
    '1': MlmResponseSerializer,
    '2': PosLoginResponseSerializer
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
        app = app if app in APPLICATION_LOGIN_SERIALIZERS_MAP else '0'
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
        token = jwt_encode(user) if getattr(settings, 'REST_USE_JWT', False) else create_token(self.token_model, user,
                                                                                               serializer)
        if getattr(settings, 'REST_SESSION_LOGIN', True):
            django_login(self.request, user)
        return user, token

    def get_response(self, user, token):
        """
        Get Response Based on Authentication and App Type Requested
        """
        token = token if getattr(settings, 'REST_USE_JWT', False) else user.auth_token.key
        app_type = self.request.data.get('app_type', 0)
        shop_object = Shop.objects.filter(Q(shop_owner=user) | Q(related_users=user),
                                          shop_type__shop_type='f').last() if app_type == '2' else None

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
    authentication_classes = (TokenAuthentication,)

    def get_object(self):
        return self.request.user

    def get_queryset(self):
        """
        Adding this method since it is sometimes called when using
        django-rest-swagger
        https://github.com/Tivix/django-rest-auth/issues/275
        """
        return get_user_model().objects.none()
        

# Todo remove
class PasswordResetView(GenericAPIView):
    """
    Accepts the following POST parameters: mobile number

    Returns the success/fail message.
    """
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = PasswordResetSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            number = request.data.get("phone_number")
            user = UserModel.objects.filter(phone_number=number)
            if user.exists():
                phone_otp, otp = PhoneOTP.update_otp_for_number(number)
                date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
                time = datetime.datetime.now().strftime("%I:%M %p")
                
                #data = {}
                #data['otp'] = otp
                #data['date'] = date
                #data['time'] = time

                #user_id = user.id
                activity_type = "PASSWORD_CHANGE"
                # from notification_center.utils import SendNotification
                # SendNotification(user_id=user_id, activity_type=activity_type, data=data).send()    

                message = SendSms(phone=number,
                                  body="%s is your One Time Password for GramFactory Account."\
                                       " Request time is %s, %s IST." % (otp,date,time))
                #status_code, reason = message.send()
                message.send()
                #if 'success' in reason:
                phone_otp.last_otp = timezone.now()
                phone_otp.save()
                msg = {'is_success': True,
                        'message': ['You will receive an OTP shortly'],
                        'response_data': None,
                        'user_exists': True }
                return Response(msg,
                    status=status.HTTP_200_OK
                )
                # else:
                #     msg = {'is_success': False,
                #             'message': [reason],
                #             'response_data': None,
                #             'user_exists': False }
                #     return Response(msg,
                #         status=status.HTTP_406_NOT_ACCEPTABLE
                #     )
            else:
                msg = {'is_success': False,
                        'message': ['Mobile No. not registered :('],
                        'response_data': None,
                        'user_exists': False }
                return Response(msg,
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        else:
            return api_serializer_errors(serializer.errors)


# Todo remove
class PasswordResetValidateView(GenericAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = PasswordResetValidateSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            number = request.data.get("phone_number")
            otp = request.data.get("otp")
            user = PhoneOTP.objects.filter(phone_number=number)
            if user.exists():
                user = user.last()
                msg, status_code = self.verify(otp, user)
                return Response(msg,
                    status=status_code
                )
            else:
                msg = {'is_success': False,
                        'message': ['Invalid Data'],
                        'response_data': None }
                return Response(msg,
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
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

    def expired(self, user):
        current_time = datetime.datetime.now()
        expiry_time = datetime.timedelta(seconds=user.expires_in)
        created_time = user.created_at
        if current_time - created_time <= expiry_time:
            return False
        else:
            return True

    def max_attempts(self, user, attempts):
        if user.attempts <= getattr(settings, 'OTP_ATTEMPTS', attempts):
            return False
        else:
            return True

    def verify(self, otp, user):
        if otp == user.otp:
            if not self.expired(user) and not self.max_attempts(user, 5):
                user = UserModel.objects.get(phone_number=user.phone_number)
                uid=urlsafe_base64_encode(force_bytes(user.pk))
                token = account_activation_token.make_token(user)
                msg = {'is_success': True,
                        'message': ['User verified'],
                        'response_data': [{'uid':uid, 'token':token}] }
                status_code=status.HTTP_200_OK
                return msg, status_code
            elif self.max_attempts(user, 5):
                msg = {'is_success': False,
                        'message': ['You have exceeded maximum attempts'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code
            elif self.expired(user):
                msg = {'is_success': False,
                        'message': ['OTP expired! Please request a new OTP'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code

        else:
            if self.max_attempts(user, 5):
                msg = {'is_success': False,
                        'message': ['You have exceeded maximum attempts'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code
            elif self.expired(user):
                msg = {'is_success': False,
                        'message': ['OTP expired! Please request a new OTP'],
                        'response_data': None }
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return msg, status_code
            user.attempts += 1
            user.save()
            reason = "OTP doesn't matched"
            msg = {'is_success': False,
                    'message': ["OTP doesn't matched"],
                    'response_data': None }
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            return msg, status_code


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
    authentication_classes = (TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        """
        request:- request object
        *args:-  non keyword argument
        **kwargs:- keyword argument
        """
        serializer = self.serializer_class(UserModel.objects.prefetch_related('shop_owner_shop').get(id=request.user.id))
        return Response(serializer.data)
