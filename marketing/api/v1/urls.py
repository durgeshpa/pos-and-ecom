from django.conf.urls import url

from .views import RewardsDashboard, UploadProfile, RatingFeedback

urlpatterns = [
    url(r'^rewards/$', RewardsDashboard.as_view(), name="rewards"),
    url(r'^profile/$', UploadProfile.as_view(), name="profile"),
    url(r'^rating/$', RatingFeedback.as_view(), name="rating"),
]
