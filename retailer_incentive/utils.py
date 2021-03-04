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