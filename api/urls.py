from django.conf.urls import url
from django.urls import path
from api.views import TestAuthView
urlpatterns = [
    path('test_auth/', TestAuthView.as_view(), name='test_auth', ),

]
