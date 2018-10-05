from django.conf.urls import url

from .views import ValidateOTP, ResendSmsOTP, ResendVoiceOTP, \
                    SendSmsOTP

urlpatterns = [
    url(r'^validate/$', ValidateOTP.as_view(), name="validate"),
    url(r'^resend/sms/$', ResendSmsOTP.as_view(), name="resend_sms"),
    url(r'^send/sms/$', SendSmsOTP.as_view(), name="send_sms"),
    url(r'^resend/voice/$', ResendVoiceOTP.as_view(), name="resend_voice"),


    ]
