from .serializers import SendSmsOTPSerializer
from rest_framework.generics import GenericAPIView, CreateAPIView
from .models import PhoneOTP, MLMUser, Referral
from rest_framework import status
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.response import Response
import datetime
from django.utils import timezone
from rest_framework.permissions import AllowAny
from retailer_backend.messages import *
from .sms import SendSms
from django.db.models import Q
from .validation import ValidateOTP

class SendSmsOTP(CreateAPIView):
    permission_classes = (AllowAny,)
    queryset = PhoneOTP.objects.all()
    serializer_class = SendSmsOTPSerializer

    def post(self, request, format=None):
        """
               This method will take phone_number & generate unique otp.
        """
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():

            number = request.data.get("phone_number")
            phone_otp, otp = PhoneOTP.create_otp_for_number(number)
            date = datetime.datetime.now().strftime("%a(%d/%b/%y)")
            time = datetime.datetime.now().strftime("%I:%M %p")
            message = SendSms(phone=number,
                              body="%s is your One Time Password for GramFactory Account." \
                                   " Request time is %s, %s IST." % (otp, date, time))
            message.send()
            phone_otp.last_otp = timezone.now()
            phone_otp.save()
            msg = {'is_success': True,
                   'message': "otp sent",
                   'response_data': None,
                   }
            return Response(msg,
                            status=status.HTTP_200_OK
                            )
        else:
            msg = {'is_success': False,
                    'message': serializer.errors['phone_number'][0],
                    'response_data': None }
            return Response(msg,
                            status=status.HTTP_406_NOT_ACCEPTABLE)


def save_user_referral_code(phone_number):
    """
        This method will generate Referral Code & create or update user in database.
    """
    user_referral_code = Referral.generate_unique_referral_code()
    MLMUser.objects.update_or_create(phone_number=phone_number, referral_code=user_referral_code)
    return user_referral_code

class Registrations(GenericAPIView):

    def post(self, request):
        """
            This method will create user & if user already there in MLM database validate otp.
        """
        try:
            data = request.data
            phone_number = data.get('phone_number')
            referral_code = data.get('referral_code')
            otp = data.get('otp')

            if phone_number is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Phone_Number'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)
            if otp is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Enter_OTP'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)

            if referral_code:
                """
                    checking entered referral code is valid or not.
                """
                user_id = MLMUser.objects.filter(referral_code=referral_code)
                if not user_id:
                    return Response({'message': VALIDATION_ERROR_MESSAGES['Referral_code'],
                                     'is_success': False,
                                     'response_data': None},
                                    status=HTTP_400_BAD_REQUEST)

            user_phone = MLMUser.objects.filter(
                Q(phone_number=phone_number)
            )
            if user_phone.exists():
                user = user_phone.last()

                if user.status == 1:
                    return Response({'message': VALIDATION_ERROR_MESSAGES['User_Already_Exist'],
                                     'is_success': False,
                                     'response_data': None},
                                    status=status.HTTP_409_CONFLICT)

                user_referral_code_none = MLMUser.objects.filter(phone_number=phone_number, referral_code=None)

                if user_referral_code_none:
                    save_user_referral_code(phone_number)

                msg = ValidateOTP(phone_number, otp)
                return Response(msg.data, status=msg.status_code)
            else:
                user_referral_code = save_user_referral_code(phone_number)
                if referral_code:
                    Referral.store_parent_referral_user(referral_code, user_referral_code)
                msg = ValidateOTP(phone_number, otp)
                return Response(msg.data, status=msg.status_code)
        except Exception:
            return Response({'message': "Data is not valid.", 'is_success': False, 'response_data': None}, status=status.HTTP_403_FORBIDDEN)

class Login(GenericAPIView):

    def post(self, request):
        """
            This method will validate user & if user already there in MLM database validate otp.
        """
        try:
            data = request.data
            phone_number = data.get('phone_number')
            otp = data.get('otp')
            if phone_number is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Phone_Number'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)
            if otp is None:
                return Response({'message': VALIDATION_ERROR_MESSAGES['Enter_OTP'],
                                 'is_success': False, 'response_data': None},
                                status=HTTP_400_BAD_REQUEST)

            user_phone = MLMUser.objects.filter(
                Q(phone_number=phone_number)
            )
            if user_phone.exists():
                user_referral_code_none = MLMUser.objects.filter(phone_number=phone_number, referral_code=None)
                if user_referral_code_none:
                    save_user_referral_code(phone_number)
                msg = ValidateOTP(phone_number, otp)
                return Response(msg.data, status=msg.status_code)
            else:
                save_user_referral_code(phone_number)
                msg = ValidateOTP(phone_number, otp)
                return Response(msg.data, status=msg.status_code)
        except Exception:
            return Response(Exception, status=status.HTTP_403_FORBIDDEN)




