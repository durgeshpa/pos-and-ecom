import logging
import json
import re
import traceback
from datetime import datetime
from django.core.exceptions import ValidationError

from django.contrib.auth import get_user_model

from shops.models import DayBeatPlanning, ParentRetailerMapping, Product, Shop, ShopDocument, ShopInvoicePattern, ShopPhoto, \
    ShopType, ShopUserMapping, RetailerType
from addresses.models import City, Pincode, State
from addresses.models import address_type_choices
from django.contrib.auth.models import Group
from shops.base64_to_file import to_file
from products.common_validators import get_csv_file_data, check_headers
from addresses.models import Address
from django.contrib.auth import get_user_model
from shops.models import PosShopUserMapping, Shop, USER_TYPE_CHOICES

logger = logging.getLogger(__name__)

User = get_user_model()

VALID_IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
]


def valid_image_extension(image, extension_list=VALID_IMAGE_EXTENSIONS):
    """ checking image extension """
    return any([image.endswith(e) for e in extension_list])


def get_validate_images(images):
    """ ValidationError will be raised in case of invalid type or extension """
    for image in images:
        if not valid_image_extension(image.name):
            return {'error': 'Not a valid Image The URL must have an image extensions (.jpg/.jpeg/.png)'}
    return {'image': images}


def valid_file_extension(file, extension_list=['.csv']):
    """ checking file extension """
    return any([file.endswith(e) for e in extension_list])


def get_validate_csv_file(files):
    """ ValidationError will be raised in case of invalid type or extension """
    for file in files:
        if not valid_file_extension(file.name):
            return {'error': 'Not a valid File, The URL must have an image extensions (.csv)'}
    return {'image': files}


def validate_shop_doc_photo(shop_photo):
    """validate shop photo"""
    filename = shop_photo.split('/')[-1:][0]
    resp = get_validate_images(filename)
    if 'error' in resp:
        return resp
    return {'shop_photo': shop_photo}


def get_validate_approval_status(approval_status):
    """validate shop approval status"""
    if not (any(approval_status in i for i in Shop.APPROVAL_STATUS_CHOICES)):
        return {'error': 'please provide a valid shop approval status'}
    return {'data': approval_status}


def validate_shop_doc_type(shop_type):
    """validate shop document type"""
    if not (any(shop_type in i for i in ShopDocument.SHOP_DOCUMENTS_TYPE_CHOICES)):
        return {'error': 'please provide a valid shop_document type'}
    return {'shop_type': shop_type}


def validate_gstin_number(document_num):
    """validate GSTIN Number"""
    gst_regex = "^([0]{1}[1-9]{1}|[1-2]{1}[0-9]{1}|[3]{1}[0-7]{1})([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$"
    if not re.match(gst_regex, document_num):
        return {'error': 'Please enter valid GSTIN'}
    return {'document_num': document_num}


def get_validate_shop_documents(shop_documents):
    """ validate shop_documents that belong to a ShopDocument model"""
    shop_doc_list = []
    for shop_doc in shop_documents:
        shop_doc_obj = shop_doc
        try:
            if 'shop_document_photo' not in shop_doc or not shop_doc['shop_document_photo'] :
                return {'error': "'shop_document_photo' | This field is required."}

            if 'shop_document_type' not in shop_doc or not shop_doc['shop_document_type'] :
                return {'error': "'shop_document_type' | This field is required."}

            if 'shop_document_number' not in shop_doc or not shop_doc['shop_document_number'] :
                return {'error': "'shop_document_number' | This field is required."}

            if 'id' not in shop_doc:
                try:
                    shop_doc_photo = to_file(shop_doc['shop_document_photo'])
                    shop_doc_obj['shop_document_photo'] = shop_doc_photo
                except:
                    return {'error': 'invalid shop document photo.'}

            shop_doc_type = validate_shop_doc_type(
                shop_doc['shop_document_type'])
            if 'error' in shop_doc_type:
                return shop_doc_type
            shop_doc_obj['shop_document_type'] = shop_doc_type['shop_type']

            if shop_doc['shop_document_type'] == ShopDocument.GSTIN:
                shop_doc_num = validate_gstin_number(
                    shop_doc['shop_document_number'])
                if 'error' in shop_doc_num:
                    return shop_doc_num
                # shop_doc_obj['shop_document_number'] = shop_doc_num['document_num']

            shop_doc_list.append(shop_doc_obj)
        except Exception as e:
            logger.error(e)
            # return {'error': 'please provide a valid shop_document id'}
            return {'error': "Something went wrong, msg: " + str(e)} 
    return {'data': shop_doc_list}


def get_validate_existing_shop_photos(photos):
    """ 
    validate ids that belong to a User model also
    checking shop_photo shouldn't repeat else through error 
    """
    photos_list = []
    photos_obj = []
    for photos_data in photos:
        try:
            shop_photo = ShopPhoto.objects.get(id=int(photos_data['id']))
        except Exception as e:
            logger.error(e)
            return {'error': '{} shop_photo not found'.format(photos_data['id'])}
        photos_obj.append(shop_photo)
        if shop_photo in photos_list:
            return {'error': '{} do not repeat same shop_photo for one shop'.format(shop_photo)}
        photos_list.append(shop_photo)
    return {'photos': photos_obj}


def get_validate_related_users(related_users):
    """ 
    validate ids that belong to a User model also
    checking related_user shouldn't repeat else through error 
    """
    related_users_list = []
    related_users_obj = []
    for related_users_data in related_users:
        try:
            related_user = get_user_model().objects.get(
                id=int(related_users_data['id']))
        except Exception as e:
            logger.error(e)
            return {'error': '{} related_user not found'.format(related_users_data['id'])}
        related_users_obj.append(related_user)
        if related_user in related_users_list:
            return {'error': '{} do not repeat same related_user for one shop'.format(related_user)}
        related_users_list.append(related_user)
    return {'related_users': related_users_obj}


def get_validate_favourite_products(favourite_products):
    """ 
    validate ids that belong to a User model also
    checking related_user shouldn't repeat else through error 
    """
    favourite_products_list = []
    favourite_products_obj = []
    for favourite_products_data in favourite_products:
        try:
            favourite_product = Product.objects.get(
                id=favourite_products_data['id'])
        except Exception as e:
            logger.error(e)
            return {'error': '{} favourite_product not found'.format(favourite_products_data['id'])}
        favourite_products_obj.append(favourite_product)
        if favourite_product in favourite_products_list:
            return {'error': '{} do not repeat same favourite_product for one shop'.format(favourite_product)}
        favourite_products_list.append(favourite_product)
    return {'favourite_products': favourite_products_obj}


def get_validate_shop_address(addresses):
    """ 
    validate address's state, city, pincode
    """
    addresses_obj = []
    for address_data in addresses:
        # mandatory_fields = ['nick_name', 'address_line1', 'address_contact_name', 'address_contact_number',
        #                     'address_type', 'state', 'city', 'pincode', ]
        # for field in mandatory_fields:
        #     if field not in address_data:
        #         raise ValidationError(f"{mandatory_fields} are the essential fields and cannot be empty ")

        if 'nick_name' not in address_data:
            raise ValidationError("nick_name can't be empty")
        if 'address_contact_name' not in address_data:
            raise ValidationError("address_contact_name can't be empty")
        if 'address_contact_number' not in address_data:
            raise ValidationError("address_contact_number can't be empty")
        if 'address_contact_number' in address_data and len(address_data['address_contact_number']) != 10:
            raise ValidationError(
                "address_contact_number must be of 10 digit.")
        if 'address_type' not in address_data:
            raise ValidationError("address_type can't be empty")
        if 'address_line1' not in address_data:
            raise ValidationError("address_line1 can't be empty")
        if 'state' not in address_data:
            raise ValidationError("state can't be empty")
        if 'city' not in address_data:
            raise ValidationError("city can't be empty")
        if 'pincode_link' not in address_data:
            raise ValidationError("pincode_link can't be empty")

        add_type = get_validate_address_type(address_data['address_type'])
        if 'error' in add_type:
            return add_type
        address_data['address_type'] = add_type['data']

        state = get_validate_state_id(address_data['state'])
        if 'error' in state:
            return state
        address_data['state'] = state['data']

        city = get_validate_city_id(address_data['city'])
        if 'error' in city:
            return city
        address_data['city'] = city['data']

        pincode = get_validate_pin_code(address_data['pincode_link'])
        if 'error' in pincode:
            return pincode
        address_data['pincode_link'] = pincode['data']
        address_data['pincode'] = pincode['data'].pincode

        addresses_obj.append(address_data)

    values_of_key = [a_dict["address_type"] for a_dict in addresses_obj]
    if 'shipping' not in values_of_key or 'billing' not in values_of_key:
        raise ValidationError("Please add at least one shipping and one billing address")
    return {'addresses': addresses_obj}


def get_validate_dispatch_center_cities(cities):
    """
    validate city
    """
    cities_list = []
    cities_obj = []
    for city_data in cities:
        if 'city' not in city_data:
            raise ValidationError("city can't be empty")

        city = get_validate_city_id(city_data['city'])
        if 'error' in city:
            return city
        if city['data'] in cities_list:
            return {'error': "pincodes can't be duplicate."}
        cities_list.append(city['data'])

        city_data['city'] = city['data']
        cities_obj.append(city_data)

    if cities_obj:
        return {'data': cities_obj}
    else:
        return {'error': 'Please add at least one city of dispatch center'}


def get_validate_dispatch_center_pincodes(pincodes):
    """
    validate pincodes
    """
    pincodes_list = []
    pincodes_obj = []
    for pincode_data in pincodes:
        if 'pincode' not in pincode_data:
            return {'error': "pincode can't be empty"}

        pincode = get_validate_pin_code(pincode_data['pincode'])
        if 'error' in pincode:
            return pincode
        if pincode['data'] in pincodes_list:
            return {'error': "pincodes can't be duplicate."}
        pincodes_list.append(pincode['data'])

        pincode_data['pincode'] = pincode['data']
        pincodes_obj.append(pincode_data)
    if pincodes_obj:
        return {'data': pincodes_obj}
    else:
        return {'error': 'Please add at least one pincode of dispatch center'}


def get_validate_shop_invoice_pattern(shop_invoice_patterns):
    """ 
    validate address's state, city, pincode
    """
    for sip_data in shop_invoice_patterns:
        if 'start_date' in sip_data and sip_data['start_date'] and 'end_date' in sip_data and sip_data['end_date']:
            if sip_data['start_date'] < sip_data['end_date']:
                return {'error': 'Please select a valid start and end date of Invoice Pattern.'}

        if not ('status' in sip_data and (
                any(sip_data['status'] in i for i in ShopInvoicePattern.SHOP_INVOICE_CHOICES))):
            return {'error': 'Please select a valid status of Invoice Pattern.'}
    return {'shop_invoice_pattern': shop_invoice_patterns}


def get_validated_parent_shop(id):
    """ Validate Parent Shop id """
    shop = ParentRetailerMapping.objects.filter(parent__id=id).exists()
    if not shop:
        return {'error': 'please provide a valid parent id'}
    return {'data': shop}


def validate_beat_planning_data_format(request):
    """ Validate shop data  """

    if not request.FILES.getlist('file'):
        return {'error': 'Please select a csv file.'}

    file = get_validate_csv_file(
        request.FILES.getlist('file'))['image']
    return {'data': file}


def validate_data_format(request):
    """ Validate shop data  """
    try:
        data = json.loads(request.data["data"])
    except Exception as e:
        return {'error': "Invalid Data Format", }

    if request.FILES.getlist('shop_images'):
        data['shop_images'] = get_validate_images(
            request.FILES.getlist('shop_images'))['image']

    return data


def get_validated_shop(shop_id):
    """Validate Shop by Id"""
    try:
        shop = Shop.objects.get(id=shop_id)
    except:
        return {'error': 'please provide a valid id'}
    return {'data': shop}


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def validate_shop_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'please provide a valid id'}
    return {'data': queryset.get(id=id)}


def validate_state_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(state__id=id).exists():
        return {'error': 'please provide a valid state id'}
    return {'data': queryset.filter(state__id=id)}


def validate_city_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(city__id=id).exists():
        return {'error': 'please provide a valid city id'}
    return {'data': queryset.filter(city__id=id)}


def validate_pin_code(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(pincode_link__id=id).exists():
        return {'error': 'please provide a valid pincode id'}
    return {'data': queryset.filter(pincode_link__id=id)}


def get_validate_state_id(id):
    """ validate id that belong to State model """
    try:
        state = State.objects.get(id=id)
    except:
        return {'error': 'please provide a valid state id'}
    return {'data': state}


def get_validate_city_id(id):
    """ validate id that belong to State model """
    try:
        city = City.objects.get(id=id)
    except:
        return {'error': 'please provide a valid city id'}

    return {'data': city}


def get_validate_address_type(add_type):
    """validate Address Type """
    if not (any(add_type in i for i in address_type_choices)):
        return {'error': 'please provide a valid address type'}
    return {'data': add_type}


def get_validate_pin_code(id):
    """ validate id that belong to State model """
    try:
        pincode = Pincode.objects.get(id=id)
    except:
        return {'error': 'please provide a valid pincode id'}
    return {'data': pincode}


def validate_shop_owner_id(queryset, id):
    """ validation only shop_owner id that belong to a selected related model """
    if not queryset.filter(shop_owner__id=id).exists():
        return {'error': 'please provide a valid shop_owner id'}
    return {'data': queryset.filter(shop_owner__id=id)}


def validate_psu_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    try:
        return {'data': queryset.get(id=id)}
    except:
        return {'error': 'please provide a valid id'}


def validate_psu_put(data):
    """ validation only ids that belong to a selected related model """
    try:
        instance = PosShopUserMapping.objects.get(id=data['id'])
        if 'shop' in data:
            if not instance.shop.id == data['shop']:
                return {'error': 'Invalid shop for mapped id.'}
        if 'user' in data:
            if not instance.user.id == data['user']:
                return {'error': 'Invalid user for mapped id.'}
        return {'data': instance}
    except:
        return {'error': 'please provide a valid id'}


def validate_data_format_without_json(request):
    """ Validate shop data  """
    try:
        data = request.data["data"]
    except Exception as e:
        return {'error': "Invalid Data Format", }

    return data


def get_validate_user(user_id):
    try:
        user = get_user_model().objects.get(id=int(user_id))
    except Exception as e:
        logger.error(e)
        return {'error': '{} user not found'.format(user_id)}
    return {'data': user}


def get_validate_shop_type(st_id):
    """validate shop type"""
    try:
        shop_type = ShopType.objects.get(id=int(st_id))
    except Exception as e:
        logger.error(e)
        return {'error': '{} shop_type not found'.format(id)}
    return {'data': shop_type}


def validate_shop(shop_id):
    """validate shop id"""
    try:
        shop_obj = Shop.objects.get(id=int(shop_id))
    except Exception as e:
        logger.error(e)
        return {'error': '{} shop not found'.format(shop_id)}
    return {'data': shop_obj}


def validate_manager(manager_id):
    """validate manager id"""
    try:
        shop_obj = ShopUserMapping.objects.get(id=int(manager_id))
    except Exception as e:
        logger.error(e)
        return {'error': '{} manager not found'.format(manager_id)}
    return {'data': shop_obj}


def validate_employee(emp_id):
    """validate employee """
    try:
        shop_obj = User.objects.get(id=int(emp_id))
    except Exception as e:
        logger.error(e)
        return {'error': '{} employee not found'.format(emp_id)}
    return {'data': shop_obj}


def validate_employee_group(emp_grp_id):
    """validate employee group id"""
    try:
        shop_obj = Group.objects.get(id=int(emp_grp_id))
    except Exception as e:
        logger.error(e)
        return {'error': '{} employee group not found'.format(emp_grp_id)}
    return {'data': shop_obj}


def validate_shop_sub_type(shop_id_id):
    """validate shop_sub_type id"""
    try:
        shop_type_obj = RetailerType.objects.get(id=shop_id_id)
    except Exception as e:
        logger.error(e)
        return {'error': '{} shop type not found'.format(shop_id_id)}
    return {'data': shop_type_obj}


def validate_shop_and_sub_shop_type(shop_type_name, shop_sub_type_name, shop_type_id):
    """ validate shop type with sub shop type mapping ShopType Model  """
    if ShopType.objects.filter(shop_type__iexact=shop_type_name, shop_sub_type__retailer_type_name=shop_sub_type_name,
                               status=True) \
            .exclude(id=shop_type_id).exists():
        return {'error': 'shop type with this sub shop type mapping already exists'}


def validate_shop_name(s_name, s_id):
    """ validate shop name already exist in Shop Model  """
    if Shop.objects.filter(shop_name__iexact=s_name, status=True).exclude(id=s_id).exists():
        return {'error': 'shop with this shop name already exists'}


def validate__existing_shop_with_name_owner(shop_name, shop_owner, shop_id):
    """ validate shop name already exist in Shop Model  """
    if Shop.objects.filter(shop_name__iexact=shop_name, shop_owner=shop_owner, status=True).exclude(id=shop_id).exists():
        return {'error': 'shop with this shop name and shop owner already exists'}


# Bulk Upload
def read_file(csv_file, upload_type):
    """
        Template Validation (Checking, whether the csv file uploaded by user is correct or not!)
    """
    csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
    # Converting headers into lowercase
    csv_file_headers = [str(ele).lower() for ele in csv_file_header_list]
    if upload_type == "shop_user_map":
        required_header_list = ['shop_id', 'shop_name', 'manager', 'employee', 'employee_group',
                                'employee_group_name', ]
    elif upload_type == "shop_update":
        required_header_list = ['shop_id', 'shop_name', 'shop_type', 'shop_owner', 'shop_activated', 'imei_no',
                                'address_id', 'nick_name', 'address', 'contact_person', 'contact_number',
                                'pincode', 'state', 'city', 'address_type', 'parent_shop_name', 'shop_created_at']

    check_headers(csv_file_headers, required_header_list)
    uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
    # Checking, whether the user uploaded the data below the headings or not!
    if uploaded_data_by_user_list:
        check_mandatory_columns(
            uploaded_data_by_user_list, csv_file_headers, upload_type)
    else:
        raise ValidationError("Please add some data below the headers to upload it!")


def check_mandatory_columns(uploaded_data_list, header_list, upload_type):
    row_num = 1
    if upload_type == "shop_user_map":
        mandatory_columns = ['shop_id', 'employee', 'employee_group', ]
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(f"{mandatory_columns} are mandatory columns for 'Create Shop User Mapping'")
        for row in uploaded_data_list:
            row_num += 1
            if 'shop_id' not in row.keys():
                raise ValidationError(
                    f"Row {row_num} | 'shop_id can't be empty")
            if 'shop_id' in row.keys() and row['shop_id'] == '':
                raise ValidationError(
                    f"Row {row_num} | 'shop_id' can't be empty")
            if 'employee' not in row.keys():
                raise ValidationError(
                    f"Row {row_num} | 'employee' can't be empty")
            if 'employee' in row.keys() and row['employee'] == '':
                raise ValidationError(
                    f"Row {row_num} | 'employee' can't be empty")
            if 'employee_group' not in row.keys():
                raise ValidationError(
                    f"Row {row_num} | 'employee_group' can't be empty")
            if 'employee_group' in row.keys() and row['employee_group'] == '':
                raise ValidationError(
                    f"Row {row_num} | 'employee_group' can't be empty")
    if upload_type == "shop_update":
        mandatory_columns = ['shop_id', 'shop_name', ]
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(
                    f"{mandatory_columns} are mandatory columns for 'Create Shop User Mapping'")
        for row in uploaded_data_list:
            row_num += 1
            if 'shop_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'shop_id can't be empty")
            if 'shop_id' in row.keys() and row['shop_id'] == '':
                raise ValidationError(
                    f"Row {row_num} | 'shop_id' can't be empty")

            if 'shop_name' not in row.keys():
                raise ValidationError(
                    f"Row {row_num} | 'shop_name' can't be empty")
            if 'shop_name' in row.keys() and row['shop_name'] == '':
                raise ValidationError(
                    f"Row {row_num} | 'shop_name' can't be empty")
            # if 'shop_name' in row.keys() and row['shop_name']:
            #     if Shop.objects.filter(shop_name__iexact=str(row['shop_name'].strip()), approval_status=2)\
            #             .exclude(id=int(row['shop_id'])).exists():
            #         raise ValidationError(f"Row {row_num} | {row['shop_name']} | 'shop_name' already exist in the "
            #                               f"system ")
            if 'address_id' not in row.keys():
                raise ValidationError(
                    f"Row {row_num} | 'address_id' can't be empty")
            if 'address_id' in row.keys() and row['address_id'] == '':
                raise ValidationError(
                    f"Row {row_num} | 'address_id' can't be empty")
            if 'address_id' in row.keys() and row['address_id']:
                if not Address.objects.filter(id=int(row['address_id'])).exists():
                    raise ValidationError(f"Row {row_num} | {row['address_id']} | 'address_id' doesn't in the "
                                          f"system ")

    validate_row(uploaded_data_list, header_list)


def validate_row(uploaded_data_list, header_list):
    """
        This method will check that Data uploaded by user is valid or not.
    """
    try:
        row_num = 1
        for row in uploaded_data_list:
            row_num += 1

            if 'address_id' in header_list and 'address_id' in row.keys() and row['address_id'] != '':
                if not Address.objects.filter(id=int(row['address_id'])).exists():
                    raise ValidationError(f"Row {row_num} | {row['address_id']} | 'address_id' doesn't exist in "
                                          f"the system ")
                mandatory_fields = ['city', 'state', 'pincode', ]
                if 'city' not in row.keys() or row['city'] == '':
                    raise ValidationError(
                        f"Row {row_num} | 'city' can't be empty ")
                if 'state' not in row.keys() or row['state'] == '':
                    raise ValidationError(
                        f"Row {row_num} | 'state' can't be empty ")
                if 'pincode' not in row.keys() or row['pincode'] == '':
                    raise ValidationError(
                        f"Row {row_num} | 'pincode' can't be empty ")
                for field in mandatory_fields:
                    if field not in header_list:
                        raise ValidationError(f"{mandatory_fields} are the essential headers and cannot be empty "
                                              f"when address_id is there")
                    if row[field] == '':
                        raise ValidationError(
                            f"Row {row_num} | {row[field]} | {field} cannot be empty {mandatory_fields} "
                            f" are the essential fields when address_id is there")

            if 'city' in header_list and 'city' in row.keys() and row['city'] != '':
                if not City.objects.filter(city_name__iexact=str(row['city']).strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['city']} | 'city' doesn't exist in "
                                          f"the system ")
            if 'state' in header_list and 'state' in row.keys() and row['state'] != '':
                if not State.objects.filter(state_name__iexact=str(row['state']).strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['state']} | 'state' doesn't exist in "
                                          f"the system ")
            if 'pincode' in header_list and 'pincode' in row.keys() and row['pincode'] != '':
                if not re.match('^[1-9][0-9]{5}$', str(int(row['pincode']))):
                    raise Exception('pincode must be of 6 digits')
                elif not Pincode.objects.filter(pincode=int(row['pincode'])).exists():
                    raise ValidationError(f"Row {row_num} | {row['pincode']} | 'pincode' doesn't exist in "
                                          f"the system ")
            if 'contact_number' in header_list and 'contact_number' in row.keys() and row['contact_number'] != '':
                if not re.match('^[6-9]\d{9}$', str(int(row['contact_number']))):
                    raise Exception('Mobile no. must be of 10 digits')

            if 'city' in header_list and 'state' in header_list and row['city'] and row['state']:
                state_id = State.objects.filter(state_name__iexact=str(row['state']).strip()).last()
                if not City.objects.filter(city_name__iexact=str(row['city']).strip(), state=state_id).exists():
                    raise ValidationError(f"Row {row_num} | {row['city']} | 'city' doesn't exist for given state"
                                          f"in the system ")

            if 'pincode' in header_list and 'state' in header_list and row['state'] and row['pincode']:
                city_id = City.objects.filter(
                    city_name__iexact=str(row['city']).strip()).last()
                if not Pincode.objects.filter(pincode=int(row['pincode']), city=city_id).exists():
                    raise ValidationError(f"Row {row_num} | {row['pincode']} | 'pincode' doesn't exist for given city"
                                          f"the system ")

            if 'shop_type' in header_list and 'shop_type' in row.keys() and row['shop_type'] != '':
                if not ShopType.objects.filter(shop_type__iexact=str(row['shop_type'].lower()).strip()).exists():
                    raise ValidationError(
                        f"Row {row_num} | {row['shop_id']} | 'shop_type' doesn't exist in the system ")

            if 'address_type' in header_list and 'address_type' in row.keys() and row['address_type'] != '':
                if not (any(str(row['address_type']).lower() in i for i in address_type_choices)):
                    raise ValidationError(f"Row {row_num} | {row['shop_id']} | 'address_type' doesn't exist in the "
                                          f"system ")

            if 'shop_id' in header_list and 'shop_id' in row.keys() and row['shop_id'] != '':
                if not Shop.objects.filter(id=int(row['shop_id'])).exists():
                    raise ValidationError(f"Row {row_num} | {row['shop_id']} | 'shop_id' doesn't exist in the system ")

            if 'shop_id' in header_list and 'shop_id' in row.keys() and row['shop_id'] != '':
                if not Shop.objects.filter(id=int(row['shop_id']), approval_status=2).exists():
                    raise ValidationError(f"Row {row_num} | {row['shop_id']} | 'shop' is not approved")

            if 'shop_name' in header_list and 'shop_name' in row.keys() and row['shop_name'] != '':
                if not Shop.objects.filter(shop_name__iexact=str(row['shop_name']).strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['shop_name']} | 'shop_name' doesn't exist in the "
                                          f"system ")

            if 'employee_group' in header_list and 'employee_group' in row.keys() and row['employee_group'] != '':
                if not Group.objects.filter(id=row['employee_group'].strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['employee_group']} | 'employee group' doesn't "
                                          f"exist in the system ")

            if 'employee' in header_list and 'employee' in row.keys() and row['employee'] != '':
                if not get_user_model().objects.filter(phone_number=row['employee'].strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['employee']} | 'employee' doesn't exist in the system ")

            if 'employee_group' in header_list and 'employee_group' in row.keys() and 'employee' in header_list and \
                    'employee' in row.keys():
                if row['employee_group'] != '' and row['employee'] != '':
                    emp_group = Group.objects.filter(id=row['employee_group'].strip())
                    if emp_group.last().name == "Sales Manager":
                        if not get_user_model().objects.filter(phone_number=row['employee'].strip(), user_type=7).exists():
                            raise ValidationError(f"Row {row_num} | {row['employee']} | "
                                                  f"'employee' Type is not Sales Manager  ")

            if 'employee_group' in header_list and 'employee_group' in row.keys() and row['employee_group'] != '':
                if not Group.objects.filter(id=row['employee_group'].strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['employee_group']} | 'employee group' doesn't "
                                          f"exist in the system ")

            if 'employee_group_name' in header_list and 'employee_group_name' in row.keys() and \
                    row['employee_group_name'] != '':
                if not Group.objects.filter(name__iexact=row['employee_group_name'].strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['employee_group_name']} | 'employee group name' "
                                          f"doesn't exist in the system ")

            if 'manager' in header_list and 'manager' in row.keys() and row['manager'] != '':
                if not ShopUserMapping.objects.filter(employee__phone_number=row['manager'].strip(),
                                                      employee__user_type=7, status=True).exists():
                    raise ValidationError(
                        f"Row {row_num} | {row['manager']} | 'manager' doesn't exist in the system ")
                elif row['manager'] == row['employee']:
                    raise ValidationError('Manager and Employee cannot be same')

    except ValueError as e:
        raise ValidationError(
            f"Row {row_num} | ValueError : {e} | Please Enter valid Data")
    except KeyError as e:
        raise ValidationError(f"Row {row_num} | KeyError : {e} | Something went wrong while checking csv data "
                              f"from dictionary")


# Beat Planning
def read_beat_planning_file(executive, csv_file, upload_type):
    """
        Template Validation (Checking, whether the csv file uploaded by user is correct or not!)
    """
    csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
    # Converting headers into lowercase
    csv_file_headers = [str(ele).split(' ')[0].strip().lower() for ele in csv_file_header_list]
    if upload_type == "beat_planning":
        required_header_list = ['employee_phone_number', 'employee_first_name', 'shop_name', 'shop_id', 'address_contact_number', 'address_line1',
                                'pincode', 'priority', 'date']

    check_headers(csv_file_headers, required_header_list)
    uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
    # Checking, whether the user uploaded the data below the headings or not!
    if uploaded_data_by_user_list:
        check_beat_planning_mandatory_columns(
            executive, uploaded_data_by_user_list, csv_file_headers, upload_type)
    else:
        raise ValidationError(
            "Please add some data below the headers to upload it!")


def check_beat_planning_mandatory_columns(executive, uploaded_data_list, header_list, upload_type):
    """
        This method will check that Data uploaded by user is not empty for mandatory fields.
    """
    shop_ids = get_executive_shops(executive)
    if not shop_ids:
        raise ValidationError("No shop mapped to the selected Sales executive.")
    row_num = 1
    if upload_type == "beat_planning":
        mandatory_columns = ['employee_phone_number',
                             'shop_id', 'priority', 'date']
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(
                    f"{mandatory_columns} are mandatory columns for 'Create Beat Planning'")
        for row in uploaded_data_list:
            row_num += 1
            if 'employee_phone_number' not in row.keys() or str(row['employee_phone_number']).strip() == '':
                raise ValidationError(
                    f"Row {row_num} | 'employee_phone_number can't be empty")
            if str(row['employee_phone_number']).strip() != executive.phone_number:
                raise ValidationError(f"Row {row_num} | Please upload beat planning for the selected executive.")

            if 'shop_id' not in row.keys() or str(row['shop_id']).strip() == '':
                raise ValidationError(
                    f"Row {row_num} | 'shop_id' can't be empty")
            if int(str(row['shop_id']).strip()) not in shop_ids:
                raise ValidationError(
                    f"Row {row_num} | {row['shop_id']} | Shop not mapped to the selected Sales executive")

            if 'priority' not in row.keys() or str(row['priority']).strip() == '':
                raise ValidationError(
                    f"Row {row_num} | 'priority' can't be empty")
            if not (any(str(row['priority']).strip() in i for i in DayBeatPlanning.shop_category_choice)):
                raise ValidationError(f"Row {row_num} | {row['priority']} | 'priority' doesn't exist in the "
                                      f"system.")

            if 'date' not in row.keys() or row['date'] == '':
                raise ValidationError(f"Row {row_num} | 'date' can't be empty")
            try:
                try:
                    datetime.strptime(str(row['date']), '%d/%m/%y').strftime("%Y-%m-%d")
                except:
                    datetime.strptime(str(row['date']), '%d/%m/%Y').strftime("%Y-%m-%d")
            except:
                raise ValidationError(
                    f"Row {row_num} | {row['date']} | 'date' Invalid date format, acceptable (dd/mm/yy).")


def get_executive_shops(executive):
    shop_ids = []
    shops = Shop.objects.filter(shop_user__employee=executive).only('id').values('id')
    if shops:
        shop_ids = [sp['id'] for sp in shops]
    return shop_ids


def get_validate_shop(shop_id):
    try:
        shop = Shop.objects.get(id=shop_id)
    except Exception as e:
        return {'error': '{} shop not found'.format(shop_id)}
    return {'data': shop}


def get_validate_user_type(user_type):
    """validate shop user type"""
    if not (any(user_type in i for i in USER_TYPE_CHOICES)):
        return {'error': 'please provide a valid User Type'}
    return {'data': user_type}


def validate_mapping(data, shop):
    if 'user' in data and data['user'] and \
            'user_type' in data and data['user_type']:
        return get_psu_mapping(data['user'], shop)
    else:
        return {'error': "Missing mandatory field/s 'user' and 'user_type'."} 


def get_psu_mapping(user, shop):
    if PosShopUserMapping.objects.filter(user=user, shop=shop).exists():
        return {'error': 'Shop User mapping already exist with the provided shop and user.'}
    else:
        return {'data': "No mapping found"}
