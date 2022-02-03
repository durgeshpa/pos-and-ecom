import datetime
import logging

from retailer_to_sp.models import ShopCrate

today = datetime.datetime.today()

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ShopCrateCommonFunctions(object):

    @staticmethod
    def create_update_shop_crate(shop_id, crate_id, is_available=True):
        info_logger.info(f"create_update_shop_crate|ShopCrateCommonFunctions|shop_id: {shop_id}, crate_id: {crate_id}")
        shop_crate_instance = ShopCrate.objects.update_or_create(
            shop_id=shop_id, crate_id=crate_id,
            defaults={'is_available': is_available})
        info_logger.info(f"create_update_shop_crate|ShopCrateCommonFunctions| {shop_crate_instance}")
        return shop_crate_instance

    @classmethod
    def mark_crate_used(cls, shop_id, crate_id):
        return ShopCrateCommonFunctions.create_update_shop_crate(shop_id, crate_id, False)

    @classmethod
    def mark_crate_available(cls, shop_id, crate_id):
        return ShopCrateCommonFunctions.create_update_shop_crate(shop_id, crate_id, True)

    @classmethod
    def get_filtered_shop_crate(cls, **kwargs):
        map_data = ShopCrate.objects.filter(**kwargs)
        return map_data
