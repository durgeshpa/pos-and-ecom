import logging
import json
import re
from shops.models import ShopDocument
logger = logging.getLogger(__name__)

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


def validate_shop_doc_type(shop_type):
    """validate shop type"""
    if not (any(shop_type in i for i in ShopDocument.SHOP_DOCUMENTS_TYPE_CHOICES)):
        return {'error': 'please provide a valid shop_document type'}
    return {'shop_type': shop_type}


def validate_gstin_number(document_num):
    """validate GSTIN Number"""
    gst_regex = "^([0]{1}[1-9]{1}|[1-2]{1}[0-9]{1}|[3]{1}[0-7]{1})([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$"
    if not re.match(gst_regex, document_num):
        raise {'error': 'Please enter valid GSTIN'}
    return {'document_num': document_num}


def get_validate_shop_documents(shop, shop_documents):
    """ validate shop_documents that belong to a ShopDocument model"""
    for shop_doc in shop_documents:
        try:
            # if 'id' in shop_doc:
            #     validated_document = ShopDocument.objects.get(shop=shop, id=shop_doc['id'])
            if 'shop_document_type' in shop_doc:
                shop_doc_type = validate_shop_doc_type(shop_doc['shop_document_type'])
                if 'error' in shop_doc_type:
                    return shop_doc_type
            if 'shop_document_number' in shop_doc and 'shop_document_type' in shop_doc and shop_doc['shop_document_type']  == ShopDocument.GSTIN:
                shop_doc_num = validate_gstin_number(shop_doc['shop_document_number'])
                if 'error' in shop_doc_num:
                    return shop_doc_num
        except Exception as e:
            logger.error(e)
            return {'error': 'please provide a valid shop_document id'}
    return {'data': shop_documents}


def validate_data_format(request):
    """ Validate shop data  """
    try:
        data = json.loads(request.data["data"])
    except Exception as e:
        return {'error': "Invalid Data Format", }

    if request.FILES.getlist('shop_photos'):
        data['shop_photos'] = request.FILES.getlist('shop_photos')

    return data


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


def validate_shop_owner_id(queryset, id):
    """ validation only shop_owner id that belong to a selected related model """
    if not queryset.filter(shop_owner__id=id).exists():
        return {'error': 'please provide a valid shop_owner id'}
    return {'data': queryset.filter(shop_owner__id=id)}
