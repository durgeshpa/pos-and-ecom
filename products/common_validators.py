import logging
from brand.models import Brand
from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
     ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping
from categories.models import Category

# Get an instance of a logger
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


def validate_id(queryset, id):
    """ validation only ids that belong to a selected related model """
    if not queryset.filter(id=id).exists():
        return {'error': 'Please Provide a Valid id'}
    return {'data': queryset.filter(id=id)}


def get_validate_parent_brand(parent_brand):
    """ validate id that belong to a Brand model if not through error """
    try:
        parent_brand_obj = Brand.objects.get(id=parent_brand)
    except Exception as e:
        logger.error(e)
        return {'error': 'Please Provide a Valid parent_brand id'}
    return {'parent_brand': parent_brand_obj}


def get_validate_product_hsn(product_hsn):
    """ validate id that belong to a ProductHSN model if not through error """
    try:
        product_hsn = ProductHSN.objects.get(id=product_hsn)
    except Exception as e:
        logger.error(e)
        return {'error': 'Please Provide a Valid parent_brand id'}
    return {'product_hsn': product_hsn}


def get_validate_category(parent_product_pro_category):
    """ validate ids that belong to a Category model also
    checking category shouldn't repeat else through error """
    cat_list = []
    for cat_data in parent_product_pro_category:
        try:
            category = Category.objects.get(id=cat_data['category'])
        except Exception as e:
            logger.error(e)
            return {'error': '{} category not found' .format(cat_data['category'])}
        if category in cat_list:
            return {'error': '{} do not repeat same category for one product'.format(category)}
        cat_list.append(category)
    return {'category': parent_product_pro_category}


def get_validate_tax(parent_product_pro_tax):
    """ validate ids that belong to a Tax model also
        checking tax type 'gst' should be selected """
    tax_list_type = []
    for tax_data in parent_product_pro_tax:
        try:
            tax = Tax.objects.get(id=tax_data['tax'])
        except Exception as e:
            logger.error(e)
            return {'error': 'tax not found'}

        if tax.tax_type in tax_list_type:
            return {'error': '{} type tax can be filled only once'.format(tax.tax_type)}
        tax_list_type.append(tax.tax_type)
    if 'gst' not in tax_list_type:
        return {'error': 'Please fill the GST tax value'}
    return {'tax': parent_product_pro_tax}


def get_validate_images(parent_product_pro_image):
    """ ValidationError will be raised in case of invalid type or extension """
    for image in parent_product_pro_image:
        if not valid_image_extension(image.name):
            return {'error': 'Not a valid Image The URL must have an image extensions (.jpg/.jpeg/.png)'}
    return {'image': parent_product_pro_image}


def is_ptr_applicable_validation(data):
    if not data.get('ptr_type'):
        return {'error': 'Invalid PTR Type'}
    elif not data.get('ptr_percent'):
        return {'error': 'Invalid PTR Percentage'}
    return data





