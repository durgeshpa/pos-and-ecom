from addresses.models import Address
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
    def create_update_shop_address(cls, shop, addresses):
        """
        Create / Update Shop Address
        """
        ids = []
        if addresses:
            for image in addresses:
                if 'id' in image:
                    ids.append(image['id'])

        Address.objects.filter(shop_name=shop).exclude(id__in=ids).delete()
        if addresses:
            for address in addresses:
                address['shop_name'] = shop
                add_id = None
                if 'id' in address:
                    add_id = address.pop('id')
                Address.objects.update_or_create(defaults=address, id=add_id)

    @classmethod
    def upload_shop_photos(cls, shop, photos):
        """
            Create shop_photos
        """
        if photos:
            for photo in photos:
                ShopPhoto.objects.create(shop_photo=photo, shop_name=shop)

    @classmethod
    def create_shop_docs(cls, shop, docs):
        """
            Create shop_docs
        """
        if docs:
            for doc in docs:
                ShopDocument.objects.create(shop_document_photo=doc['shop_document_photo'],
                                            shop_document_number=doc['shop_document_number'],
                                            shop_document_type=doc['shop_document_type'],
                                            shop_name=shop)

    @classmethod
    def create_shop_invoice_pattern(cls, shop, invoice_pattern):
        """
            Create shop_invoice_pattern
        """
        if invoice_pattern:
            for invoice in invoice_pattern:
                invoice.pop('shop')
                ShopInvoicePattern.objects.create(shop=shop, **invoice)


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


def convert_base64_to_image(data):
    from django.core.files.base import ContentFile
    import base64
    import six
    import uuid

    # Check if this is a base64 string
    if isinstance(data, six.string_types):
        # Check if the base64 string is in the "data:" format
        if 'data:' in data and ';base64,' in data:
            # Break out the header from the base64 content
            header, data = data.split(';base64,')

        # Try to decode the file. Return validation error if it fails.
        try:
            decoded_file = base64.b64decode(data)
        except TypeError:
            raise Exception('invalid_image')

        # Generate file name:
        # 12 characters are more than enough.
        file_name = str(uuid.uuid4())[:12]
        # Get the file name extension:
        file_extension = get_file_extension(file_name, decoded_file)

        complete_file_name = "%s.%s" % (file_name, file_extension, )

        data = ContentFile(decoded_file, name=complete_file_name)

    return data


def get_file_extension(file_name, decoded_file):
    import imghdr

    extension = imghdr.what(file_name, decoded_file)
    extension = "jpg" if extension == "jpeg" else extension

    return extension
