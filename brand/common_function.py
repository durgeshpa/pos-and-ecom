import logging
from products.models import CentralLog
from products.common_function import change_message_action

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class BrandCls(object):

    @classmethod
    def create_brand_log(cls, log_obj, changed_data, action):
        """
            Create Brand Log
        """

        change_message, action, create_updated_by = change_message_action(log_obj, changed_data, action)
        try:
            brand_log = CentralLog.objects.create(brand=log_obj, updated_by=log_obj.updated_by,
                                                  changed_fields=change_message, action="updated")
        except Exception as e:
            error_logger.info("brand update info ", e)

        dict_data = {'updated_by': brand_log.updated_by, 'updated_at': brand_log.update_at,
                     'brand': brand_log.brand, "changed_fields": change_message}
        info_logger.info("brand update info ", dict_data)

        return brand_log
