from django.conf.urls import url
from .views import (Registrations, SendSmsOTP, Login, RewardsDashboard, Logout, UploadProfile)
from marketing.filters import MlmUserAutocomplete


urlpatterns = [
    url(r'^send/sms/$', SendSmsOTP.as_view(), name="send_sms"),
    url(r'^user/$', Registrations.as_view(), name="user"),
    url(r'^login/$', Login.as_view(), name="login"),
    url(r'^rewards/$', RewardsDashboard.as_view(), name="rewards"),
    url(r'^logout/$', Logout.as_view(), name="logout"),
    url(r'^profile/$', UploadProfile.as_view(), name="profile"),
    url(r'^mlm-user-autocomplete/$', MlmUserAutocomplete.as_view(), name='mlm-user-autocomplete'),
    ]