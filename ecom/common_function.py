import logging
from ecom.models import ShopUserLocationMappedLog


info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


def create_shop_user_mapping(shop, user):
    shop_user_log = ShopUserLocationMappedLog.objects.filter(user=user).last()
    if not shop_user_log or shop_user_log.shop != shop:
        ShopUserLocationMappedLog.objects.create(shop=shop, user=user)
        info_logger.info(f"create_shop_user_mapping | ShopUserLocationMappedLog | created | "
                         f"shop {shop} | user {user}.")
