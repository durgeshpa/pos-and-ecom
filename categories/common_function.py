import logging
from products.models import CentralLog

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class CategoryCls(object):

    @classmethod
    def create_category_log(cls, log_obj):
        """
            Create Category Log
        """
        parent_product_log = CentralLog.objects.create(category=log_obj, update_at=log_obj.updated_at,
                                                       updated_by=log_obj.updated_by)

        dict_data = {'updated_by': log_obj.updated_by, 'updated_at': log_obj.updated_at,
                     'category': log_obj}
        info_logger.info("category update info ", dict_data)

        return parent_product_log
