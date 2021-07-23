import logging
import json
import re

from django.core.exceptions import ValidationError

from django.contrib.auth import get_user_model

from shops.models import ParentRetailerMapping, Product, Shop, ShopDocument, ShopInvoicePattern, ShopPhoto, \
    ShopType, ShopUserMapping, RetailerType
from addresses.models import City, Pincode, State
from addresses.models import address_type_choices
from django.contrib.auth.models import Group
from shops.common_functions import convert_base64_to_image
from shops.base64_to_file import to_file
from products.common_validators import get_csv_file_data, check_headers

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
        raise {'error': 'Please enter valid GSTIN'}
    return {'document_num': document_num}


def get_validate_shop_documents(shop_documents):
    """ validate shop_documents that belong to a ShopDocument model"""
    shop_doc_list = []
    for shop_doc in shop_documents:
        shop_doc_obj = shop_doc
        try:
            if 'shop_document_photo' in shop_doc and shop_doc['shop_document_photo']:
                if 'id' not in shop_doc:
                    shop_doc_photo = to_file(shop_doc['shop_document_photo'])
                    shop_doc_obj['shop_document_photo'] = shop_doc_photo
            if 'shop_document_type' in shop_doc:
                shop_doc_type = validate_shop_doc_type(
                    shop_doc['shop_document_type'])
                if 'error' in shop_doc_type:
                    return shop_doc_type
                shop_doc_obj['shop_document_type'] = shop_doc_type['shop_type']
            if 'shop_document_number' in shop_doc and 'shop_document_type' in shop_doc and shop_doc['shop_document_type'] == ShopDocument.GSTIN:
                shop_doc_num = validate_gstin_number(
                    shop_doc['shop_document_number'])
                if 'error' in shop_doc_num:
                    return shop_doc_num
                shop_doc_obj['shop_document_number'] = shop_doc_num['document_num']
            shop_doc_list.append(shop_doc_obj)
        except Exception as e:
            logger.error(e)
            return {'error': 'please provide a valid shop_document id'}
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
            related_user = get_user_model().objects.get(id=int(related_users_data['id']))
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
    if 'shipping' not in values_of_key:
        raise ValidationError("Please add at least one shipping address")
    return {'addresses': addresses_obj}


def get_validate_shop_invoice_pattern(shop_invoice_patterns):
    """ 
    validate address's state, city, pincode
    """
    for sip_data in shop_invoice_patterns:
        if 'start_date' in sip_data and sip_data['start_date'] and 'end_date' in sip_data and sip_data['end_date']:
            if sip_data['start_date'] < sip_data['end_date']:
                return {'error': 'Please select a valid start and end date of Invoice Pattern.'}

        if not ('status' in sip_data and (any(sip_data['status'] in i for i in ShopInvoicePattern.SHOP_INVOICE_CHOICES))):
            return {'error': 'Please select a valid status of Invoice Pattern.'}
    return {'shop_invoice_pattern': shop_invoice_patterns}


def get_validated_parent_shop(id):
    """ Validate Parent Shop id """
    shop = ParentRetailerMapping.objects.filter(parent__id=id).exists()
    if not shop:
        return {'error': 'please provide a valid parent id'}
    return {'data': shop}


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
    state = State.objects.get(id=id)
    if not state:
        return {'error': 'please provide a valid state id'}
    return {'data': state}


def get_validate_city_id(id):
    """ validate id that belong to State model """
    city = City.objects.get(id=id)
    if not city:
        return {'error': 'please provide a valid city id'}
    return {'data': city}


def get_validate_address_type(add_type):
    """validate Address Type """
    if not (any(add_type in i for i in address_type_choices)):
        return {'error': 'please provide a valid address type'}
    return {'data': add_type}


def get_validate_pin_code(id):
    """ validate id that belong to State model """
    pincode = Pincode.objects.get(id=id)
    if not pincode:
        return {'error': 'please provide a valid pincode id'}
    return {'data': pincode}


def validate_shop_owner_id(queryset, id):
    """ validation only shop_owner id that belong to a selected related model """
    if not queryset.filter(shop_owner__id=id).exists():
        return {'error': 'please provide a valid shop_owner id'}
    return {'data': queryset.filter(shop_owner__id=id)}


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
        shop_obj = Shop.objects.get(id=shop_id)
    except Exception as e:
        logger.error(e)
        return {'error': '{} shop not found'.format(shop_id)}
    return {'data': shop_obj}


def validate_manager(manager_id):
    """validate manager id"""
    try:
        shop_obj = ShopUserMapping.objects.get(id=manager_id)
    except Exception as e:
        logger.error(e)
        return {'error': '{} manager not found'.format(manager_id)}
    return {'data': shop_obj}


def validate_employee(emp_id):
    """validate employee """
    try:
        shop_obj = User.objects.get(id=emp_id)
    except Exception as e:
        logger.error(e)
        return {'error': '{} employee not found'.format(emp_id)}
    return {'data': shop_obj}


def validate_employee_group(emp_grp_id):
    """validate employee group id"""
    try:
        shop_obj = Group.objects.get(id=emp_grp_id)
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
    if ShopType.objects.filter(shop_type__iexact=shop_type_name, shop_sub_type__retailer_type_name=shop_sub_type_name, status=True)\
            .exclude(id=shop_type_id).exists():
        return {'error': 'shop type with this sub shop type mapping already exists'}


def validate_shop_name(s_name, s_id):
    """ validate shop name already exist in Shop Model  """
    if Shop.objects.filter(shop_name__iexact=s_name, status=True).exclude(id=s_id).exists():
        return {'error': 'shop with this shop name already exists'}


# Bulk Upload
def read_file(csv_file):
    """
        Template Validation (Checking, whether the csv file uploaded by user is correct or not!)
    """
    csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
    csv_file_headers = [str(ele).lower() for ele in csv_file_header_list] # Converting headers into lowercase
    required_header_list = ['shop_id', 'shop_name', 'manager', 'employee', 'employee_group', 'employee_group_name', ]

    check_headers(csv_file_headers, required_header_list)
    uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
    # Checking, whether the user uploaded the data below the headings or not!
    if uploaded_data_by_user_list:
        check_mandatory_columns(uploaded_data_by_user_list, csv_file_headers)
    else:
        raise ValidationError("Please add some data below the headers to upload it!")


def check_mandatory_columns(uploaded_data_list, header_list,):
    row_num = 1
    mandatory_columns = ['shop_id', 'employee', 'employee_group', ]
    for ele in mandatory_columns:
        if ele not in header_list:
            raise ValidationError(f"{mandatory_columns} are mandatory columns for 'Create Shop User Mapping'")
    for row in uploaded_data_list:
        row_num += 1
        if 'shop_id' not in row.keys():
            raise ValidationError(f"Row {row_num} | 'shop_id can't be empty")
        if 'shop_id' in row.keys() and row['shop_id'] == '':
            raise ValidationError(f"Row {row_num} | 'shop_id' can't be empty")
        if 'employee' not in row.keys():
            raise ValidationError(f"Row {row_num} | 'employee' can't be empty")
        if 'employee' in row.keys() and row['employee'] == '':
            raise ValidationError(f"Row {row_num} | 'employee' can't be empty")
        if 'employee_group' not in row.keys():
            raise ValidationError(f"Row {row_num} | 'employee_group' can't be empty")
        if 'employee_group' in row.keys() and row['employee_group'] == '':
            raise ValidationError(f"Row {row_num} | 'employee_group' can't be empty")

    validate_row(uploaded_data_list, header_list)


def validate_row(uploaded_data_list, header_list):
    """
        This method will check that Data uploaded by user is valid or not.
    """
    try:
        row_num = 1
        for row in uploaded_data_list:
            row_num += 1

            if 'shop_name' in header_list and 'shop_name' in row.keys() and row['shop_name'] != '':
                if not Shop.objects.filter(shop_name__iexact=str(row['shop_name']).strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['shop_name']} | 'shop_name' doesn't exist in the "
                                          f"system ")
            if 'shop_id' in header_list and 'shop_id' in row.keys() and row['shop_id'] != '':
                if not Shop.objects.filter(id=int(row['shop_id'])).exists():
                    raise ValidationError(f"Row {row_num} | {row['shop_id']} | 'shop_id' doesn't exist in the system ")

            if 'employee' in header_list and 'employee' in row.keys() and row['employee'] != '':
                if not get_user_model().objects.filter(phone_number=row['employee'].strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['employee']} | 'employee' doesn't exist in the system ")

            if 'employee_group' in header_list and 'employee_group' in row.keys() and row['employee_group'] != '':
                if not Group.objects.filter(id=row['employee_group'].strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['employee_group']} | 'employee group' doesn't "
                                          f"exist in the system ")

            if 'employee_group_name' in header_list and 'employee_group_name' in row.keys() and row['employee_group_name'] != '':
                if not Group.objects.filter(name__iexact=row['employee_group_name'].strip()).exists():
                    raise ValidationError(f"Row {row_num} | {row['employee_group_name']} | 'employee group name' "
                                          f"doesn't exist in the system ")

            if 'manager' in header_list and 'manager' in row.keys() and row['manager'] != '':
                if not ShopUserMapping.objects.filter(employee__phone_number=row['manager'].strip(),
                                                      employee__user_type=7, status=True).exists():
                    raise ValidationError(f"Row {row_num} | {row['manager']} | 'manager' doesn't exist in the system ")
                elif row['manager'] == row['employee']:
                    raise ValidationError('Manager and Employee cannot be same')

    except ValueError as e:
        raise ValidationError(f"Row {row_num} | ValueError : {e} | Please Enter valid Data")
    except KeyError as e:
        raise ValidationError(f"Row {row_num} | KeyError : {e} | Something went wrong while checking csv data "
                              f"from dictionary")
