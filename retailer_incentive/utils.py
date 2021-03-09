import datetime

from retailer_incentive.models import SchemeShopMapping


def get_active_mappings(shop_id):
    """
    Returns the queryset of active mappings for the given shop
    Params:
        shop_id : id of the shop
    """
    return SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True,
                                            scheme__end_date__gte=datetime.datetime.today().date())


def get_shop_scheme_mapping(shop_id):
    shop_scheme_mapping_qs = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True,
                                                              scheme__end_date__gt=datetime.datetime.today().date())
    if shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).exists():
        return shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).last()
    return shop_scheme_mapping_qs.last()