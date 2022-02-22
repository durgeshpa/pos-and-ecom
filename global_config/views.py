from django.shortcuts import render

# Create your views here.
from global_config.models import GlobalConfig
from shops.models import FOFOConfigurations


def get_config(key, default_value=None):
    config_object = GlobalConfig.objects.filter(key=key).last()
    if config_object is None:
        return default_value
    return config_object.value


def get_config_fofo_shop(key, shop_id=None):
    config_object = FOFOConfigurations.objects.filter(key__name__iexact=key, shop_id=shop_id).last()
    if config_object is None:
        config_object = FOFOConfigurations.objects.filter(key__name__iexact=key,
                                                          shop__shop_name__iexact="default fofo shop").last()
    if config_object:
        return config_object.value
    return None


