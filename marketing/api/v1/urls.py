from django.conf.urls import url

from .views import RewardsDashboard, UploadProfile

urlpatterns = [
    url(r'^rewards/$', RewardsDashboard.as_view(), name="rewards"),
    url(r'^profile/$', UploadProfile.as_view(), name="profile"),
]
