import datetime
from retailer_incentive.models import SchemeShopMapping, IncentiveDashboardDetails

today_date = datetime.date.today()


def get_active_mappings(shop_id):
    """
    Returns the queryset of active mappings for the given shop
    Params:
        shop_id : id of the shop
    """
    return SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True)


def get_shop_scheme_mapping(shop_id):
    """Returns the valid Scheme mapped for given shop_id"""
    current_year = today_date.year
    current_month = today_date.month
    shop_scheme_mapping_qs = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True,
                                                              start_date__year=current_year,
                                                              start_date__month=current_month,
                                                              end_date__year=current_year,
                                                              end_date__month=current_month)
    if shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).exists():
        return shop_scheme_mapping_qs.filter(priority=SchemeShopMapping.PRIORITY_CHOICE.P1).last()
    return shop_scheme_mapping_qs.last()


def get_shop_scheme_mapping_based(shop_id, month):
    """Returns the valid Scheme mapped for given shop_id based on selected month (current_month)"""
    current_year = today_date.year
    scheme_shop_mapping_list = []
    if month == today_date.month:
        var_priority = 'priority'
        shop_scheme_mapping_qs = SchemeShopMapping.objects.filter(shop_id=shop_id, is_active=True,
                                                                  start_date__year=current_year,
                                                                  end_date__year=current_year,
                                                                  start_date__month=month,
                                                                  end_date__month=month).order_by('-start_date',
                                                                                                  var_priority)
        if shop_scheme_mapping_qs:
            start_end_date_list = []
            for scheme in shop_scheme_mapping_qs:
                start_end_date = str(scheme.start_date) + str(scheme.end_date)
                if start_end_date in start_end_date_list:
                    continue
                start_end_date_list += [start_end_date]
                scheme_shop_mapping_list.append(scheme)
        var_priority = 'scheme_priority'
        shop_scheme_mapping_qs = IncentiveDashboardDetails.objects.filter(shop_id=shop_id,
                                                                          start_date__year=current_year,
                                                                          end_date__year=current_year,
                                                                          start_date__month=month,
                                                                          end_date__month=month).order_by('-start_date',
                                                                                                          var_priority)
        if shop_scheme_mapping_qs:
            start_end_date_list = []
            for scheme in shop_scheme_mapping_qs:
                start_end_date = str(scheme.start_date) + str(scheme.end_date)
                if start_end_date in start_end_date_list:
                    continue
                start_end_date_list += [start_end_date]
                scheme_shop_mapping_list.append(scheme)
        return scheme_shop_mapping_list
    else:
        var_priority = 'scheme_priority'
        shop_scheme_mapping_qs = IncentiveDashboardDetails.objects.filter(shop_id=shop_id,
                                                                          start_date__year=current_year,
                                                                          end_date__year=current_year,
                                                                          start_date__month=month,
                                                                          end_date__month=month).order_by('-start_date',
                                                                                                          var_priority)

        if shop_scheme_mapping_qs:
            start_end_date_list = []
            scheme_shop_mapping_list = []
            for scheme in shop_scheme_mapping_qs:
                start_end_date = str(scheme.start_date) + str(scheme.end_date)
                if start_end_date in start_end_date_list:
                    continue
                start_end_date_list += [start_end_date]
                scheme_shop_mapping_list.append(scheme)
    return scheme_shop_mapping_list




