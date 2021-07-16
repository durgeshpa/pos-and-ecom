import logging

from rest_framework import status
from rest_framework.response import Response

from addresses.models import Address
from products.models import CentralLog
from shops.models import ParentRetailerMapping, ShopDocument, ShopInvoicePattern, ShopPhoto
from shops.base64_to_file import to_file

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ShopCls(object):
    @classmethod
    def create_shop_log(cls, log_obj, action):
        """
            Create Shop Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        shop_log = CentralLog.objects.create(shop=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': shop_log.updated_by, 'updated_at': shop_log.update_at,
                     'shop': log_obj}
        info_logger.info("shop_log update info ", dict_data)

        return shop_log

    @classmethod
    def create_update_shop_address(cls, shop, addresses):
        """
            Delete existing Shop Address if not in the request
            Create / Update Shop Address
        """
        if addresses:
            ids = []
            for image in addresses:
                if 'id' in image:
                    ids.append(image['id'])

            Address.objects.filter(shop_name=shop).exclude(id__in=ids).delete()

            for address in addresses:
                address['shop_name'] = shop
                add_id = None
                if 'id' in address:
                    add_id = address.pop('id')
                Address.objects.update_or_create(defaults=address, id=add_id)

    @classmethod
    def create_upadte_shop_photos(cls, shop, existing_photos, photos):
        """
            Delete existing Shop Photos if not in the request
            Create Shop Photos
        """
        ids = []
        if existing_photos:
            for image in existing_photos:
                ids.append(image.id)

        ShopPhoto.objects.filter(shop_name=shop).exclude(id__in=ids).delete()

        if photos:
            for photo in photos:
                ShopPhoto.objects.create(shop_photo=photo, shop_name=shop)

    @classmethod
    def create_upadte_shop_docs(cls, shop, docs):
        """
            Delete existing Shop Documents if not in the request
            Create shop_docs
        """
        if docs:
            new_docs = []
            ids = []
            for image in docs:
                if 'id' in image:
                    ids.append(image['id'])
                else:
                    new_docs.append(image)

            ShopDocument.objects.filter(
                shop_name=shop).exclude(id__in=ids).delete()

            for doc in new_docs:
                ShopDocument.objects.create(shop_name=shop, **doc)

    @classmethod
    def create_upadte_shop_invoice_pattern(cls, shop, invoice_pattern):
        """
            Delete existing Shop Invoice Patterns if not in the request
            Create shop_invoice_pattern
        """
        if invoice_pattern:
            ids = []
            for ip in invoice_pattern:
                if 'id' in ip:
                    ids.append(ip['id'])

            ShopInvoicePattern.objects.filter(
                shop=shop).exclude(id__in=ids).delete()

            for invoice in invoice_pattern:
                invoice['shop'] = shop
                ip_id = None
                if 'id' in invoice:
                    ip_id = invoice.pop('id')
                ShopInvoicePattern.objects.update_or_create(
                    defaults=invoice, id=ip_id)

    @classmethod
    def update_related_users_and_favourite_products(cls, shop, related_users, favourite_products):
        """
            Update Related users of the Shop
        """
        if related_users:
            for user in related_users:
                shop.related_users.add(user)

        if favourite_products:
            for prd in favourite_products:
                shop.favourite_products.add(prd)

    @classmethod
    def update_parent_shop(cls, shop, parent_shop):
        """
            Update Parent Shop of the Shop
        """
        shop.retiler_mapping.filter(
            status=True).all().update(parent=parent_shop)

    @classmethod
    def create_parent_shop(cls, shop, parent_shop):
        """
            Update Parent Shop of the Shop
        """
        obj, created = ParentRetailerMapping.objects.update_or_create(
            retailer=shop, parent=parent_shop,
            defaults={},
        )
        return obj

        # ParentRetailerMapping.objects.create(retailer=shop, parent=parent_shop)


def created_updated_by(log_obj, action):
    if action == "created":
        create_updated_by = log_obj.created_by
    else:
        create_updated_by = log_obj.updated_by

    return action, create_updated_by


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
