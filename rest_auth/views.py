from django.contrib.auth import (
    login as django_login,
    logout as django_logout
)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters

from rest_framework import status, authentication, permissions, serializers, exceptions
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication

from django.http import JsonResponse
import json, datetime
from django.utils import timezone

from otp.sms import SendSms, SendVoiceSms

from .app_settings import (
    TokenSerializer, UserDetailsSerializer, LoginSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    PasswordChangeSerializer, JWTSerializer, create_token
)
from .serializers import PasswordResetValidateSerializer
from .models import TokenModel
from .utils import jwt_encode
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from otp.models import PhoneOTP

from accounts.tokens import account_activation_token

from django.utils.encoding import force_bytes, force_text

UserModel = get_user_model()

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters(
        'password', 'old_password', 'new_password1', 'new_password2'
    )
)


class LoginView(GenericAPIView):
    """
    Check the credentials and return the REST Token
    if the credentials are valid and authenticated.
    Calls Django Auth login method to register User ID
    in Django session framework

    Accept the following POST parameters: username, password
    Return the REST Framework Token Object's key.
    """
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer
    token_model = TokenModel
    queryset = TokenModel.objects.all()

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    def process_login(self):
        django_login(self.request, self.user)

    def get_response_serializer(self):
        if getattr(settings, 'REST_USE_JWT', False):
            response_serializer = JWTSerializer
        else:
            response_serializer = TokenSerializer
        return response_serializer

    def login(self):
        self.user = self.serializer.validated_data['user']

        if getattr(settings, 'REST_USE_JWT', False):
            self.token = jwt_encode(self.user)
        else:
            self.token = create_token(self.token_model, self.user,
                                      self.serializer)

        if getattr(settings, 'REST_SESSION_LOGIN', True):
            self.process_login()

    def get_response(self):
        serializer_class = self.get_response_serializer()

        if getattr(settings, 'REST_USE_JWT', False):
            data = {
                'user': self.user,
                'token': self.token
            }
            serializer = serializer_class(instance=data,
                                          context={'request': self.request})
        else:
            serializer = serializer_class(instance=self.token,
                                          context={'request': self.request})
        return Response({'is_success': True,
                        'message':['Successfully logged in'],
                        'response_data':[{'access_token':serializer.data['key']}]},
                        status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data,
                                              context={'request': request})

        if self.serializer.is_valid():
            self.login()
            return self.get_response()
        else:
            errors = []
            for field in self.serializer.errors:
                for error in self.serializer.errors[field]:
                    if 'non_field_errors' in field:
                        result = error
                    else:
                        result = ''.join('{} : {}'.format(field,error))
                    errors.append(result)
            msg = {'is_success': False,
                    'message': errors,
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)



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

    def logout(self, request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, ObjectDoesNotExist):
            pass

        django_logout(request)

        return Response({'is_success': True,
                        'message':['Successfully logged out'],
                        'response_data': None},
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
            return Response({'is_success': True,
                            'message':['New password has been saved.'],
                            'response_data': None},
                            status=status.HTTP_200_OK)
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
                    'message': errors,
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)


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
            return Response({'is_success': True,
                            'message':['New password has been saved.'],
                            'response_data': None},
                            status=status.HTTP_200_OK)
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
                    'message': errors,
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)
