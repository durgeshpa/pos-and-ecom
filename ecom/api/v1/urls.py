from django.conf.urls import url

from .views import AccountView, RewardsView

urlpatterns = [
    url(r'^account/', AccountView.as_view(), name='ecom-account'),
    url(r'^rewards/', RewardsView.as_view(), name='user-rewards'),
]
