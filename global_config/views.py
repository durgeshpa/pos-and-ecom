from django.shortcuts import render

# Create your views here.
from global_config.models import GlobalConfig
from shops.models import FOFOConfigurations,FOFOConfig, Shop



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
    if type(shop) == type(int(1)):
        shop = Shop.objects.get(id=shop)

    if shop.shop_type.shop_sub_type.retailer_type_name == "fofo":
        obj ,_ = FOFOConfig.objects.get_or_create(shop=shop)
        # if config_object is None:
        #     config_object = FOFOConfigurations.objects.filter(shop__shop_name__iexact="default fofo shop").last()
        if _:
           obj.save()
    return {'open_time': obj.shop_opening_timing,
                     'close_time': obj.shop_closing_timing,
                     'working_off_start_date': obj.working_off_start_date,
                     'working_off_end_date': obj.working_off_end_date,
                     'delivery_redius': obj.delivery_redius,
                     'min_order_value': obj.min_order_value,
                     'delivery_time':obj.delivery_time
                        }
