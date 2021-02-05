from django.conf import settings

from rest_framework.authtoken.models import Token as DefaultTokenModel

from .utils import import_callable

# Register your models here.

APPLICATIONS = (
    (0, 'Default'),
    (1, 'Retailer App'),
    (2, 'Rewards PepperTap'),
)
USER_VERIFIED = 1

TokenModel = import_callable(
    getattr(settings, 'REST_AUTH_TOKEN_MODEL', DefaultTokenModel))
