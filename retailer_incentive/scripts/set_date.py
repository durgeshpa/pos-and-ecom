import logging
from retailer_incentive.models import Scheme, SchemeShopMapping

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


def run():
    set_start_end_date()


def set_start_end_date():
    """
    This method is used for set_start_end_date
    """
    schemes = Scheme.object.all()
    for scheme in schemes:
        scheme_shop_mapping = SchemeShopMapping.object.filter(scheme=scheme)
        for scheme_sh_map in scheme_shop_mapping:
            scheme_sh_map.start_date = scheme.start_date
            scheme_sh_map.end_date = scheme.end_date