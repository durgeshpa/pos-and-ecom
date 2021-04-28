import datetime
from retailer_incentive.models import SchemeShopMapping, IncentiveDashboardDetails


def get_active_mappings(shop_id):
    """
    Returns the queryset of active mappings for the given shop
    Params:
        shop_id : id of the shop
    """
    return SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True)


def get_shop_scheme_mapping(shop_id):
    """Returns the valid Scheme mapped for given shop_id"""
    shop_scheme_mapping_qs = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True,
                                                              scheme__start_date__lte=datetime.datetime.today(),
                                                              scheme__end_date__gte=datetime.datetime.today())
    if shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).exists():
        return shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).last()
    return shop_scheme_mapping_qs.last()


def get_shop_scheme_mapping_based_on_month(shop_id, month):
    """Returns the valid Scheme mapped for given shop_id based on selected month (current_month)"""
    shop_scheme_mapping_qs = SchemeShopMapping.objects.filter(shop_id=shop_id,
                                                              start_date__month=month,
                                                              end_date__month=month)
    if shop_scheme_mapping_qs:
        scheme_shop_mapping_list = []
        if shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).exists():
            shop_scheme_mapping = shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1)
            for shop_scheme_map in shop_scheme_mapping:
                scheme_shop_mapping_list.append(shop_scheme_map)
            return scheme_shop_mapping_list
        else:
            for shop_scheme in shop_scheme_mapping_qs:
                scheme_shop_mapping_list.append(shop_scheme)
            return scheme_shop_mapping_list
    return shop_scheme_mapping_qs


def get_shop_scheme_mapping_based_on_month_from_db(shop_id, month):
    """Returns the valid Scheme mapped for given shop_id based on selected month from DB"""
    scheme_shop_mapping_list = []
    shop_scheme_mapping_qs = IncentiveDashboardDetails.objects.filter(shop_id=shop_id,
                                                                      start_date__month=month,
                                                                      end_date__month=month)
    if shop_scheme_mapping_qs:
        for shop_scheme in shop_scheme_mapping_qs:
            scheme_shop_mapping_list.append(shop_scheme)
        return scheme_shop_mapping_list
    return shop_scheme_mapping_qs


