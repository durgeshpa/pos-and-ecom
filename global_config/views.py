from django.shortcuts import render

# Create your views here.
from global_config.models import GlobalConfig


def get_config(key, default_value=None):
    config_object = GlobalConfig.objects.filter(key=key).last()
    if config_object is None:
        return default_value
    return config_object.value