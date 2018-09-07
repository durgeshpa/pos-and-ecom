from django.conf.urls import url

from .views import ValidateOTP

urlpatterns = [
    url(r'^validate/$', ValidateOTP.as_view(), name="validate"),
    ]
