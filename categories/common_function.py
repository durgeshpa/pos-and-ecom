import logging
from products.models import CentralLog
from products.common_function import created_updated_by

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class CategoryCls(object):

    @classmethod
    def create_category_log(cls, log_obj, action):
        """
            Create Category Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        try:
            category_log = CentralLog.objects.create(category=log_obj, updated_by=create_updated_by, action=action)
        except Exception as e:
            error_logger.info("category update info ", e)

        dict_data = {'updated_by': category_log.updated_by, 'updated_at': category_log.update_at,
                     'category': log_obj}
        info_logger.info("category update info ", dict_data)

        return category_log
