import logging
import json
import re
import traceback

from django.contrib.auth import get_user_model

from shops.models import ParentRetailerMapping, Product, Shop, ShopDocument, ShopInvoicePattern, ShopPhoto, ShopType, ShopUserMapping
from addresses.models import City, Pincode, State
from addresses.models import address_type_choices
from django.contrib.auth.models import Group
from shops.common_functions import convert_base64_to_image
from shops.base64_to_file import to_file

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
            shop_photo = ShopPhoto.objects.get(id=photos_data['id'])
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
                id=related_users_data['id'])
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
        addresses_obj.append(address_data)
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
        user = get_user_model().objects.get(id=user_id)
    except Exception as e:
        logger.error(e)
        return {'error': '{} user not found'.format(user_id)}
    return {'data': user}


def get_validate_shop_type(id):
    """validate shop type"""
    try:
        shop_type = ShopType.objects.get(id=id)
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
