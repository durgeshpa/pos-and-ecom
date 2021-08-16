from django.conf.urls import url,include

from rest_auth.views import (LoginView, LogoutView, UserDetailsView, PasswordChangeView,
                             PasswordResetView, PasswordResetConfirmView, PasswordResetValidateView,
                             RetailerUserDetailsView)

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^password/reset/confirm/$', PasswordResetConfirmView.as_view(), name='rest_password_reset_confirm'),
    url(r'^login/$', LoginView.as_view(), name='rest_login'),
    # Todo remove
    url(r'^password/reset/$', PasswordResetView.as_view(),
        name='rest_password_reset'),
    # Todo remove
    url(r'^password/reset/validate/$', PasswordResetValidateView.as_view(),
        name='rest_password_reset_validate'),
    # URLs that require a user to be logged in with a valid session / token.
    url(r'^logout/$', LogoutView.as_view(), name='rest_logout'),
    url(r'^user/$', UserDetailsView.as_view(), name='rest_user_details'),
    url(r'^password/change/$', PasswordChangeView.as_view(), name='rest_password_change'),
    url(r'^retailer-user/$', RetailerUserDetailsView.as_view(), name='retailer_user_details')
]
