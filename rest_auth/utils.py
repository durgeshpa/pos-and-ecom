from six import string_types
from importlib import import_module

from accounts.models import User


def import_callable(path_or_callable):
    if hasattr(path_or_callable, '__call__'):
        return path_or_callable
    else:
        assert isinstance(path_or_callable, string_types)
        package, attr = path_or_callable.rsplit('.', 1)
        return getattr(import_module(package), attr)


def default_create_token(token_model, user):
    token, _ = token_model.objects.get_or_create(user=user)
    return token


def jwt_encode(user):
    try:
        from rest_framework_jwt.settings import api_settings
    except ImportError:
        raise ImportError("djangorestframework_jwt needs to be installed")

    jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

    payload = jwt_payload_handler(user)
    return jwt_encode_handler(payload)


class AutoUser(object):

    @classmethod
    def create_update_user(cls, ph_no, email=None, name=None, is_whatsapp=None):
        user, created = User.objects.get_or_create(phone_number=ph_no)
        user.email = email if email and not user.email else user.email
        user.first_name = name if name and not user.first_name else user.first_name
        user.is_whatsapp = True if is_whatsapp else user.is_whatsapp
        user.save()
        return user