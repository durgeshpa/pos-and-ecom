from django.conf.urls import url,include

#from .views import (PasswordResetView, PasswordResetConfirmView)

urlpatterns = [
    url(r'^v1/', include('banner.api.v1.urls')),
    url(r'^v2/', include('banner.api.v2.urls')),
]
