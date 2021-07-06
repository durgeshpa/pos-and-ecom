import logging
from products.models import CentralLog
from products.common_function import change_message_action

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class CategoryCls(object):

    @classmethod
    def create_category_log(cls, log_obj, changed_data, action):
        """
            Create Category Log
        """
        change_message, action, create_updated_by = change_message_action(log_obj, changed_data, action)
        try:
            category_log = CentralLog.objects.create(category=log_obj, updated_by=create_updated_by,
                                                     changed_fields=change_message, action=action)

        except Exception as e:
            error_logger.info("category update info ", e)

        dict_data = {'updated_by': category_log.updated_by, 'updated_at': category_log.update_at,
                     'category': log_obj, "changed_fields": change_message}
        info_logger.info("category update info ", dict_data)

        return category_log
