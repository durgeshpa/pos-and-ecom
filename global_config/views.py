from django.shortcuts import render

# Create your views here.
from global_config.models import GlobalConfig
from shops.models import FOFOConfigurations,FOFOConfig



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


def get_config_fofo_shops(shop):
    if shop.shop_type.shop_sub_type.retailer_type_name == "fofo":
        config_object = FOFOConfig.objects.get(shop=shop.id)
        # if config_object is None:
        #     config_object = FOFOConfigurations.objects.filter(shop__shop_name__iexact="default fofo shop").last()
        if config_object:
            return {'open_time': config_object.shop_opening_timing,
                 'close_time': config_object.shop_closing_timing,
                 'open_days': config_object.working_days
                    }

