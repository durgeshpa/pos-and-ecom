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
            Create Parent Product Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        offer_page_product_log = OfferLog.objects.create(offer_page=log_obj, updated_by=create_updated_by,
                                                         action=action)
        dict_data = {'updated_by': offer_page_product_log.updated_by, 'updated_at': offer_page_product_log.update_at,
                     'offer_page': log_obj, }
        info_logger.info("offer page update info ", dict_data)

        return offer_page_product_log

    @classmethod
    def create_offer_banner_slot_log(cls, log_obj, action):
        """
            Create Parent Product Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        offer_page_product_log = OfferLog.objects.create(offer_banner_slot=log_obj, updated_by=create_updated_by,
                                                         action=action)
        dict_data = {'updated_by': offer_page_product_log.updated_by, 'updated_at': offer_page_product_log.update_at,
                     'offer_page': log_obj, }
        info_logger.info("offer page update info ", dict_data)

        return offer_page_product_log