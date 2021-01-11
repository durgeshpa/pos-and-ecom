from django.conf.urls import url
from .views import (Registrations, SendSmsOTP, Login)


urlpatterns = [
    url(r'^send/sms/$', SendSmsOTP.as_view(), name="send_sms"),
    url(r'^user/$', Registrations.as_view(), name="user"),
    url(r'^login/$', Login.as_view(), name="login"),
    ]