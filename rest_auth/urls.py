from django.conf.urls import url,include

from rest_auth.views import (LoginView, LogoutView, UserDetailsView, PasswordChangeView, PasswordResetConfirmView,
                             RetailerUserDetailsView, EcomAccessView)

urlpatterns = [
    # User logged in
    url(r'^logout/$', LogoutView.as_view(), name='rest_logout'),
    url(r'^user/$', UserDetailsView.as_view(), name='rest_user_details'),
    url(r'^password/change/$', PasswordChangeView.as_view(), name='rest_password_change'),
    url(r'^retailer-user/$', RetailerUserDetailsView.as_view(), name='retailer_user_details'),

    # User not logged in
    url(r'^login/$', LoginView.as_view(), name='rest_login'),
    url(r'^ecom/access/$', EcomAccessView.as_view(), name='ecom-access'),
    url(r'^password/reset/confirm/$', PasswordResetConfirmView.as_view(), name='rest_password_reset_confirm'),
]
