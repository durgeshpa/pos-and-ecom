import logging
from products.models import CentralLog
from products.common_function import created_updated_by

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class BrandCls(object):

    @classmethod
    def create_brand_log(cls, log_obj, action):
        """
            Create Brand Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        try:
            brand_log = CentralLog.objects.create(brand=log_obj, updated_by=create_updated_by, action=action)
        except Exception as e:
            error_logger.info("brand update info ", e)

        dict_data = {'updated_by': brand_log.updated_by, 'updated_at': brand_log.update_at,
                     'brand': brand_log.brand}
        info_logger.info("brand update info ", dict_data)

        return brand_log
