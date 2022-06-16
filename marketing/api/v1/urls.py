from django.conf.urls import url

from .views import RewardsDashboard, UploadProfile, RatingFeedback, Wishlist

urlpatterns = [
    url(r'^rewards/$', RewardsDashboard.as_view(), name="rewards"),
    url(r'^profile/$', UploadProfile.as_view(), name="profile"),
    url(r'^rating/$', RatingFeedback.as_view(), name="rating"),
    url(r'^wishlist/$', Wishlist.as_view(), name="wishlist"),
]
