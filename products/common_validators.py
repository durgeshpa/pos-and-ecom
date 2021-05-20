from brand.models import Brand
from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
     ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping
from categories.models import Category


VALID_IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
]


def valid_image_extension(image, extension_list=VALID_IMAGE_EXTENSIONS):
    return any([image.endswith(e) for e in extension_list])


def validate_id(queryset, id):
    if not queryset.filter(id=id).exists():
        return {'error': 'Please Provide a Valid id'}
    return {'data': queryset.filter(id=id)}


def get_validate_parent_brand(parent_brand):
    try:
        parent_brand_obj = Brand.objects.get(id=parent_brand)
    except Exception as e:
        return {'error': 'Please Provide a Valid parent_brand id'}
    return parent_brand_obj


def get_validate_product_hsn(product_hsn):
    try:
        product_hsn = Brand.objects.get(id=product_hsn)
    except Exception as e:
        return {'error': 'Please Provide a Valid parent_brand id'}
    return {'product_hsn': product_hsn}


def get_validate_category(parent_product_pro_category):
    cat_list = []
    for cat_data in parent_product_pro_category:
        try:
            category = Category.objects.get(id=cat_data['category'])
        except Exception as e:
            return {'error': '{} category not found' .format(cat_data['category'])}
        if category in cat_list:
            return {'error': '{} do not repeat same category for one product'.format(category)}
        cat_list.append(category)
    return {'category': parent_product_pro_category}


def get_validate_tax(parent_product_pro_tax):
    tax_list_type = []
    for tax_data in parent_product_pro_tax:
        try:
            tax = Tax.objects.get(id=tax_data['tax'])
        except Exception as e:
            return {'error': 'tax not found'}

        if tax.tax_type in tax_list_type:
            return {'error': '{} type tax can be filled only once'.format(tax.tax_type)}
        tax_list_type.append(tax.tax_type)
    if 'gst' not in tax_list_type:
        return {'error': 'Please fill the GST tax value'}
    return {'tax': parent_product_pro_tax}


def get_validate_images(parent_product_pro_image):
    for image in parent_product_pro_image:
        if not valid_image_extension(image.name):
            return {'error': 'Not a valid Image The URL must have an image extensions (.jpg/.jpeg/.png)'}
    return {'image': parent_product_pro_image}



