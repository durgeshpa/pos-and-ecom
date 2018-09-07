from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from django.conf import settings


from .models import PhoneOTP
from .serializers import PhoneOTPValidateSerializer

class ValidateOTP(CreateAPIView):
    queryset = PhoneOTP.objects.all()
    serializer_class = PhoneOTPValidateSerializer

    def post(self, request, format=None):
        ser = self.serializer_class(
            data=request.data, context={'request': request}
        )
        if ser.is_valid():
            number = request.data.get("phone_number")
            otp = request.data.get("otp")
            try:
                user = PhoneOTP.objects.get(phone_number=number)
                if user:
                    import pdb;
                    #pdb.set_trace()
                    reason, status_code = self.verify(otp, user)
                    return Response(
                        {'reason': reason},
                        status=status_code
                    )
            except ObjectDoesNotExist:
                return Response(
                    {'reason': 'User does not exist'},
                    status=status.HTTP_406_NOT_ACCEPTABLE
                )
        return Response(
            {'reason': ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)

    def expired(self, user):
        import datetime
        current_time = datetime.datetime.now()
        expiry_time = datetime.timedelta(seconds=user.expires_in)
        created_time = user.created_at
        if current_time - created_time <= expiry_time:
            return False
        else:
            return True

    def max_attempts(self, otp, user, attempts):
        if user.attempts <= getattr(settings, 'OTP_ATTEMPTS', attempts):
            return False
        else:
            return True

    def verify(self, otp, user):
        if otp == user.otp:
            if not self.expired(user) and not self.max_attempts(otp, user, 5):
                user.is_verified = 1
                user.save()
                reason = "User Verified"
                status_code=status.HTTP_200_OK
                return reason, status_code
            elif self.max_attempts(otp, user, 5):
                reason = "You have exceeded maximum attempts"
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return reason, status_code
            elif self.expired(user):
                reason = "OTP has been expired"
                status_code = status.HTTP_406_NOT_ACCEPTABLE
                return reason, status_code

        else:
            user.attempts += 1
            user.save()
            reason = "OTP doesn't matched"
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            return reason, status_code
