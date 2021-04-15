import logging
import json

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def validate_data_format(request):
    """
        Validating Entered data,
        Convert python data(request.data) in to a JSON string,
    """
    try:
        # Checking if Entered Data is in the Right Format except images
        # the result is a JSON string, which is valid Data
        json.dumps(request.data, default=lambda skip_image: 'images')
    except Exception as e:
        error_logger.error(e)
        msg = {'is_success': False,
               'error_message': f"Please provide valid Data",
               'response_data': None}
        return msg