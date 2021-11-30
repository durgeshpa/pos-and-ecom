from django.conf.urls import url,include

#from .views import (PasswordResetView, PasswordResetConfirmView)

urlpatterns = [
    url(r'^v1/', include('categories.api.v2.urls')),
    url(r'^v2/', include('categories.api.v2.urls')),
]
