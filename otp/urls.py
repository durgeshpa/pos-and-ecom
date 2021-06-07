from django.conf.urls import url

from .views import (ValidateOTP, ResendSmsOTP, ResendVoiceOTP, SendSmsOTP, SendSmsOTPAnytime)

urlpatterns = [
    url(r'^validate/$', ValidateOTP.as_view(), name="validate"),
    url(r'^send/sms/$', SendSmsOTP.as_view(), name="send_sms"),

    # Todo remove all below
    url(r'^resend/voice/$', ResendVoiceOTP.as_view(), name="resend_voice"),
    url(r'^resend/sms/$', ResendSmsOTP.as_view(), name="resend_sms"),
    url(r'^send-otp-anytime/$', SendSmsOTPAnytime.as_view(), name="resend_voice"),
]
