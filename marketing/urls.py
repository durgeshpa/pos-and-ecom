from django.conf.urls import url
<<<<<<< HEAD
from .views import (Registrations, ValidateOTP, SendSmsOTP,Login, RewardsDashboard)
=======
from .views import (Registrations, SendSmsOTP, Login)
>>>>>>> 9827cf96ef2457e9c2f379db5c1eb01cf1f110f7


urlpatterns = [
    url(r'^send/sms/$', SendSmsOTP.as_view(), name="send_sms"),
    url(r'^user/$', Registrations.as_view(), name="user"),
    url(r'^login/$', Login.as_view(), name="login"),
    url(r'^validate/$', ValidateOTP.as_view(), name="validate"),
    url(r'^rewards', RewardsDashboard.as_view(), name="rewards")
    ]