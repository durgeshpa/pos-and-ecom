import logging
from products.models import CentralLog

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class BrandCls(object):

    @classmethod
    def create_brand_log(cls, log_obj):
        """
            Create Brand Log
        """
        try:
            brand_log = CentralLog.objects.create(brand=log_obj, updated_by=log_obj.updated_by)
        except Exception as e:
            error_logger.info("brand update info ", e)

        dict_data = {'updated_by': brand_log.updated_by, 'updated_at': brand_log.update_at,
                     'brand': brand_log.brand}
        info_logger.info("brand update info ", dict_data)

        return brand_log
