import logging
from products.models import CentralLog

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class BrandCls(object):

    @classmethod
    def create_brand_log(cls, log_obj):
        """
            Create Category Log
        """
        try:
            category_log = CentralLog.objects.create(brand=log_obj, update_at=log_obj.updated_at,
                                                     updated_by=log_obj.updated_by)
        except Exception as e:
            error_logger.info("brand update info ", e)

        dict_data = {'updated_by': log_obj.updated_by, 'updated_at': log_obj.updated_at,
                     'category': log_obj}
        info_logger.info("brand update info ", dict_data)

        return category_log
