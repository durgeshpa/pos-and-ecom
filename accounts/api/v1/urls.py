from django.conf.urls import url
from django.urls import path
from accounts.api.v1.views import UserID
urlpatterns = [
    path('user-id/', UserID.as_view(), name='get_user_id', ),
]
