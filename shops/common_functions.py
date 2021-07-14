import logging

from rest_framework import status
from rest_framework.response import Response

from products.models import CentralLog
from shops.models import ShopDocument, ShopInvoicePattern, ShopPhoto

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ShopCls(object):
    @classmethod
    def create_shop_log(cls, log_obj):
        """
            Create Weight Log
        """
        shop_log = CentralLog.objects.create(
            shop=log_obj, updated_by=log_obj.updated_by)
        dict_data = {'updated_by': log_obj.updated_by, 'updated_at': log_obj.modified_at,
                     'shop': log_obj}
        info_logger.info("shop_log update info ", dict_data)

        return shop_log

    @classmethod
    def upload_shop_photos(cls, shop, photos):
        """
            Create shop_photos
        """
        if photos:
            for photo in photos:
                print(photo)
                ShopPhoto.objects.create(shop_photo=photo, shop_name=shop)

    @classmethod
    def create_shop_docs(cls, shop, docs):
        """
            Create shop_docs
        """
        for doc in docs:
            ShopDocument.objects.create(shop_document_photo=doc['shop_document_photo'],
                                        shop_document_number=doc['shop_document_number'],
                                        shop_document_type=doc['shop_document_type'],
                                        shop_name=shop)

    @classmethod
    def create_shop_invoice_pattern(cls, shop, invoice_pattern, s_date, e_date, i_status):
        """
            Create shop_invoice_pattern
        """
        for invoice in invoice_pattern:
            ShopInvoicePattern.objects.create(
                pattern=invoice, start_date=s_date, end_date=e_date, status=i_status, shop=shop)


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True,
                      "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": []}

    return Response(result, status=status_code)


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


def get_excel_file_data(excel_file):
    headers = excel_file.pop(0)  # headers of the uploaded excel file
    # Converting headers into lowercase
    excelFile_headers = [str(ele).lower() for ele in headers]

    uploaded_data_by_user_list = []
    excel_dict = {}
    count = 0
    for row in excel_file:
        for ele in row:
            excel_dict[excelFile_headers[count]] = ele
            count += 1
        uploaded_data_by_user_list.append(excel_dict)
        excel_dict = {}
        count = 0

    return uploaded_data_by_user_list, excelFile_headers
