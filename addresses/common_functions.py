import codecs
import csv
import logging

from rest_framework import status
from rest_framework.response import Response

from addresses.common_validators import get_csv_file_data

# Logger
from addresses.models import ShopRoute

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


def serializer_error_batch(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for error_s in serializer.errors:
        for field in error_s:
            for error in error_s[field]:
                if 'non_field_errors' in field:
                    result = error
                else:
                    result = ''.join('{} : {}'.format(field, error))
                errors.append(result)
    return errors


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True, "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": []}

    return Response(result, status=status_code)


class ShopRouteCommonFunction(object):

    @classmethod
    def create_shop_route(cls, validated_data):
        csv_file = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
        # Converting headers into lowercase
        csv_file_headers = [str(ele).split(' ')[0].strip().lower() for ele in csv_file_header_list]
        uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
        try:
            info_logger.info('Method Start to create / update Shop Route')
            for row in uploaded_data_by_user_list:
                shop_route_object, created = ShopRoute.objects.update_or_create(
                    shop_id=int(row['shop_id']), defaults={'route_id': int(row['route_id'])})
            info_logger.info("Method complete to create Shop Route from csv file")
        except Exception as e:
            import traceback; traceback.print_exc()
            error_logger.info(f"Something went wrong, while working with create Shop Route {str(e)}")
