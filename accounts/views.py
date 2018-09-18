from django.shortcuts import render

# Create your views here.

from allauth.account.signals import user_signed_up, email_confirmed
@receiver(user_signed_up)
def user_signed_up_(request, user, **kwargs):
    print("user signed up")
