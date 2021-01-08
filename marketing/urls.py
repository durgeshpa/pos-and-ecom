from django.conf.urls import include, url
from .views import GetUniqueReferralCode

urlpatterns = [
    url(r'^get-referral-code/(?P<id>\d+)/$', GetUniqueReferralCode.as_view(), name='get-referral-code'),
]