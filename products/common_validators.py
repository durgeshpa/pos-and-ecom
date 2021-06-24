import logging
import json

from brand.models import Brand, Vendor
from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
    ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping, ProductImage
from categories.models import Category
from shops.models import Shop

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
        return {'error': 'please provide a valid id'}
    return {'data': queryset.filter(id=id)}


def get_validate_parent_brand(parent_brand):
    """ validate id that belong to a Brand model if not through error """
    try:
        parent_brand_obj = Brand.objects.get(id=parent_brand)
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid parent_brand id'}
    return {'parent_brand': parent_brand_obj}


def get_validate_product_hsn(product_hsn):
    """ validate id that belong to a ProductHSN model if not through error """
    try:
        product_hsn = ProductHSN.objects.get(id=product_hsn)
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid parent_brand id'}
    return {'product_hsn': product_hsn}


def get_validate_categorys(parent_product_pro_category):
    """ validate ids that belong to a Category model also
    checking category shouldn't repeat else through error """
    cat_list = []
    for cat_data in parent_product_pro_category:
        try:
            category = Category.objects.get(id=cat_data['category'])
        except Exception as e:
            logger.error(e)
            return {'error': '{} category not found'.format(cat_data['category'])}
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


def get_validate_images(product_images):
    """ ValidationError will be raised in case of invalid type or extension """
    for image in product_images:
        if not valid_image_extension(image.name):
            return {'error': 'Not a valid Image The URL must have an image extensions (.jpg/.jpeg/.png)'}
    return {'image': product_images}


def is_ptr_applicable_validation(data):
    """ id is_ptr_applicable check ptr_type & ptr_percent"""
    if not data.get('ptr_type'):
        return {'error': 'Invalid PTR Type'}
    elif not data.get('ptr_percent'):
        return {'error': 'Invalid PTR Percentage'}
    return data


def get_validate_parent_product_image_ids(product, img_ids):
    """ validate parent product id that belong to a ParentProduct model"""
    for img_id in img_ids:
        try:
            validated_image = ParentProductImage.objects.get(parent_product=product, id=img_id['id'])
        except Exception as e:
            logger.error(e)
            return {'error': 'please provide a valid parent_product_pro_image id'}
    return {'image': validated_image}


def get_validate_child_product_image_ids(product, img_ids):
    """ validate parent product id that belong to a ParentProduct model"""
    for img_id in img_ids:
        try:
            validated_image = ProductImage.objects.get(product=product, id=img_id['id'])
        except Exception as e:
            logger.error(e)
            return {'error': 'please provide a valid product_pro_image id'}
    return {'image': validated_image}


def get_validate_parent_product(product):
    """ validate parent product id that belong to a ParentProduct model"""
    try:
        parent_product = ParentProduct.objects.get(id=product)
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid parent product id'}
    return {'parent_product': parent_product}


def get_validate_product(product):
    """ validate product id that belong to a Product model"""
    try:
        product = Product.objects.get(id=product)
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid product id'}
    return {'product': product}


def get_validate_vendor(vendor):
    """ validate vendor id that belong to a Vendor model"""
    try:
        vendor = Vendor.objects.get(id=vendor)
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid vendor id'}
    return {'vendor': vendor}


def get_validate_seller_shop(seller_shop):
    """ validate seller_shop id that belong to a Shop model also
        checking shop_type 'sp' should be selected """
    try:
        seller_shop = Shop.objects.get(id=seller_shop, shop_type__shop_type='sp')
    except Exception as e:
        logger.error(e)
        return {'error': 'please provide a valid seller_shop id'}
    return {'seller_shop': seller_shop}


def check_active_capping(seller_shop, product):
    """ check capping is active for the selected sku and warehouse """
    if ProductCapping.objects.filter(seller_shop=seller_shop,
                                     product=product,
                                     status=True).exists():
        return {'error': 'Another Capping is Active for the selected SKU or selected Warehouse.'}
    return {'seller_shop': seller_shop, 'product': product}


def validate_tax_type(parent_product, tax_type):
    parent_product = ParentProductTaxMapping.objects.filter(parent_product=parent_product, tax__tax_type=tax_type)
    if parent_product.exists():
        return "{} %".format(parent_product.last().tax.tax_percentage)
    return ''


def validate_data_format(request):
    # Validate product data
    try:
        data = json.loads(request.data["data"])
    except Exception as e:
        return {'error': "Invalid Data Format", }

    if request.FILES.getlist('product_images'):
        data['product_images'] = request.FILES.getlist('product_images')

    return data


def get_validate_packing_material(packing_material):
    """ validate id that belong to a ProductPackingMapping model """
    for pack_mat_data in packing_material:
        try:
            product = Product.objects.get(id=pack_mat_data['packing_sku'], repackaging_type='packing_material')
        except Exception as e:
            logger.error(e)
            return {'error': '{} product not found'.format(pack_mat_data['packing_sku'])}

    return {'packing_material_product': product}


def get_source_product(source_product_pro):
    """ validate id that belong to a ProductPackingMapping model """
    for pack_mat_data in source_product_pro:
        try:
            product = Product.objects.get(id=pack_mat_data['source_sku'], repackaging_type='source')
        except Exception as e:
            logger.error(e)
            return {'error': '{} product not found'.format(pack_mat_data['source_sku'])}

    return {'source_product': product}


def product_category(obj):
    try:
        if obj.parent_product_pro_category.exists():
            cats = [str(cat.category) for cat in obj.parent_product_pro_category.filter(status=True)]
            return "\n".join(cats)
        return ''
    except:
        return ''


def product_gst(obj):
    product_gst = validate_tax_type(obj, 'gst')
    return product_gst


def product_cess(obj):
    product_cess = validate_tax_type(obj, 'cess')
    return product_cess


def product_surcharge(obj):
    product_surcharge = validate_tax_type(obj, 'surcharge')
    return product_surcharge


def product_image(obj):
    if obj.parent_product_pro_image.exists():
        return "{}".format(obj.parent_product_pro_image.last().image.url)
    else:
        return '-'


def validate_bulk_data_format(request):
    # Validate product data
    try:
        data = json.loads(request.data["data"])
    except Exception as e:
        return {'error': "Invalid Data Format", }

    if request.FILES.getlist('file'):
        data['file'] = request.FILES['file']

    return data

