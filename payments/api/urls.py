from django.conf.urls import url,include

#from .views import (PasswordResetView, PasswordResetConfirmView)

urlpatterns = [
    url(r'^v1/', include('payments.api.v1.urls')),
]
