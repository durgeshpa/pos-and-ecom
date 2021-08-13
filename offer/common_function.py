import logging

from offer.models import OfferLog
from products.common_function import created_updated_by

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class OfferCls(object):
    @classmethod
    def create_offer_page_log(cls, log_obj, action):
        """
            Create Offer Page Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        offer_page_log = OfferLog.objects.create(offer_page=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': offer_page_log.updated_by, 'updated_at': offer_page_log.update_at,
                     'offer_page': log_obj, }
        info_logger.info("offer page update info ", dict_data)

        return offer_page_log

    @classmethod
    def create_offer_banner_slot_log(cls, log_obj, action):
        """
            Create Offer Banner Slot Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        offer_banner_slot_log = OfferLog.objects.create(offer_banner_slot=log_obj, updated_by=create_updated_by,
                                                        action=action)
        dict_data = {'updated_by': offer_banner_slot_log.updated_by, 'updated_at': offer_banner_slot_log.update_at,
                     'offer_banner_slot': log_obj, }
        info_logger.info("offer banner slot update info ", dict_data)

        return offer_banner_slot_log

    @classmethod
    def create_offer_banner_log(cls, log_obj, action):
        """
            Create Offer Banner Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        offer_banner_log = OfferLog.objects.create(offer_banner=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': offer_banner_log.updated_by, 'updated_at': offer_banner_log.update_at,
                     'offer_banner': log_obj, }
        info_logger.info("offer banner update info ", dict_data)

        return offer_banner_log

    @classmethod
    def create_top_sku_log(cls, log_obj, action):
        """
            Create Top Sku Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        top_sku_log = OfferLog.objects.create(top_sku=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': top_sku_log.updated_by, 'updated_at': top_sku_log.update_at,
                     'top_sku': log_obj, }
        info_logger.info("top sku update info ", dict_data)

        return top_sku_log

    @classmethod
    def create_top_sku_log(cls, log_obj, action):
        """
            Create TOP SKU Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        top_sku_log = OfferLog.objects.create(top_sku=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': top_sku_log.updated_by, 'updated_at': top_sku_log.update_at,
                     'top_sku': log_obj, }
        info_logger.info("top sku update info ", dict_data)

        return top_sku_log