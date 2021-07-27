import logging
import codecs
import csv
from datetime import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.response import Response

from django.db import transaction
from products.common_validators import get_csv_file_data
from addresses.models import Address, State, City, Pincode
from products.models import CentralLog
from shops.models import BeatPlanning, DayBeatPlanning, ParentRetailerMapping, ShopDocument, ShopInvoicePattern, ShopPhoto, ShopUserMapping, Shop
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
    def create_shop_type_log(cls, log_obj, action):
        """
            Create Shop Type Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        shop_type_log = CentralLog.objects.create(shop_type=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': shop_type_log.updated_by, 'updated_at': shop_type_log.update_at,
                     'shop_type': log_obj}
        info_logger.info("shop_type log update info ", dict_data)

        return shop_type_log

    @classmethod
    def create_shop_user_map_log(cls, log_obj, action):
        """
              Create Shop User Mapping Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        shop_user_map_log = CentralLog.objects.create(shop_user_map=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': shop_user_map_log.updated_by, 'updated_at': shop_user_map_log.update_at,
                     'shop_user_map': log_obj}
        info_logger.info("shop_log update info ", dict_data)

        return shop_user_map_log

    @classmethod
    def create_shop_user_mapping(cls, validated_data):
        csv_file = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
        # Converting headers into lowercase
        csv_file_headers = [str(ele).lower() for ele in csv_file_header_list]
        uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
        try:
            info_logger.info('Method Start to create Shop User Mapping')
            for row in uploaded_data_by_user_list:
                shop_user_map = ShopUserMapping.objects.create(
                    shop=Shop.objects.filter(id=row['shop_id'].strip()).last(),
                    manager=ShopUserMapping.objects.filter(employee__phone_number=row['manager'].strip(),
                                                           employee__user_type=7, status=True).last(),
                    employee=get_user_model().objects.filter(phone_number=row['employee'].strip()).last(),
                    employee_group=Group.objects.filter(id=row['employee_group'].strip()).last(),
                    created_by=validated_data['created_by'])
                ShopCls.create_shop_user_map_log(shop_user_map, "created")

            info_logger.info("Method complete to create Shop User Mapping from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with createS hop User Mapping  "
                              f" + {str(e)}")

    @classmethod
    def create_beat_planning(cls, validated_data):
        csv_file = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
        # Converting headers into lowercase
        csv_file_headers = [str(ele).lower() for ele in csv_file_header_list]
        uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
        try:
            info_logger.info('Method Start to create Beat Planning')
            """
            Update existing beat planning status to False
            """
            executive_user = get_user_model().objects.filter(
                    phone_number=uploaded_data_by_user_list[0]['employee_phone_number'])
            ShopCls.update_status_existing_beat_planning(executive_user[0])
            
            """
            Upload New Beat Planning
            """
            beat_plan_object = BeatPlanning.objects.get_or_create(
                executive=executive_user[0], status=True, manager=validated_data['created_by'])
            for row in uploaded_data_by_user_list:
                try:
                    date = datetime.strptime(str(row['date']).strip(), '%d/%m/%y').strftime("%Y-%m-%d")
                except:
                    date = datetime.strptime(str(row['date']).strip(), '%d/%m/%Y').strftime("%Y-%m-%d")
                day_beat_plan_object, created = DayBeatPlanning.objects.get_or_create(
                            beat_plan=beat_plan_object[0], shop_id=int(row['shop_id']), 
                            beat_plan_date=date, shop_category=str(row['category']).strip(),
                            next_plan_date=date)
                
            info_logger.info("Method complete to create Beat Planning from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with createS hop User Mapping  "
                              f" + {str(e)}")
    
    def update_status_existing_beat_planning(executive_user):
        """
        Set status = False for all existing Beat Planning against executive
        """
        beat_planning_objs = BeatPlanning.objects.filter(executive=executive_user)
        if beat_planning_objs:
            beat_planning_objs.update(status = False)
        


    @classmethod
    def update_shop(cls, validated_data):
        csv_file = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
        # Converting headers into lowercase
        csv_file_headers = [str(ele).lower() for ele in csv_file_header_list]
        uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
        info_logger.info('Method Start to Update Shop')
        count = 0
        row_num = 1
        with transaction.atomic():
            for row in uploaded_data_by_user_list:
                row_num += 1
                count += 1
                try:
                    shop_obj = Shop.objects.filter(id=int(row['shop_id']))
                    address = Address.objects.filter(shop_name=shop_obj.last(), id=int(row['address_id']))
                    if address.exists():
                        state_id = State.objects.get(state_name=str(row['state']).strip()).id
                        city_id = City.objects.get(city_name=str(row['city']).strip()).id
                        pincode_id = Pincode.objects.get(pincode=int(row['pincode']),
                                                         city_id=city_id).id
                        address.update(nick_name=str(row['nick_name']),
                                       address_line1=str(row['address']),
                                       address_contact_name=str(row['contact_person']),
                                       address_contact_number=int(row['contact_number']),
                                       pincode_link_id=pincode_id,
                                       state_id=state_id,
                                       city_id=city_id,
                                       address_type=str(row['address_type'].lower()))
                        shipping_address = Address.objects.filter(shop_name_id=int(row['shop_id']),
                                                                  address_type='shipping')
                        if not shipping_address.exists():
                            raise Exception('Atleast one shipping address is required')
                        Shop.objects.filter(id=int(row['shop_id'])).update(shop_name=str(row['shop_name']),
                                                                           status=row['shop_activated'])
                        shop_obj.update(updated_by=validated_data['updated_by'])
                    ShopCls.create_shop_log(shop_obj.last(), "updated")

                    info_logger.info("Method complete to create Shop User Mapping from csv file")
                except Exception as e:
                    error_logger.info(f"Something went wrong, while working with createS hop User Mapping  "
                                      f" + {str(e)}")

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
