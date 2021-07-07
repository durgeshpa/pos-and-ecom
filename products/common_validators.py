import logging
import json
import re
from django.core.exceptions import ValidationError

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


def get_validate_categories(parent_product_pro_category):
    """ validate ids that belong to a Category model also
    checking category shouldn't repeat else through error """
    cat_list = []
    cat_obj = []
    for cat_data in parent_product_pro_category:
        try:
            category = Category.objects.get(id=cat_data['category'])
        except Exception as e:
            logger.error(e)
            return {'error': '{} category not found'.format(cat_data['category'])}
        cat_obj.append(category)
        if category in cat_list:
            return {'error': '{} do not repeat same category for one product'.format(category)}
        cat_list.append(category)
    return {'category': cat_obj}


def get_validate_tax(parent_product_pro_tax):
    """ validate ids that belong to a Tax model also
        checking tax type 'gst' should be selected """
    tax_list_type = []
    tax_obj = []
    for tax_data in parent_product_pro_tax:
        try:
            tax = Tax.objects.get(id=tax_data['tax'])
        except Exception as e:
            logger.error(e)
            return {'error': 'tax not found'}
        tax_obj.append(tax)
        if tax.tax_type in tax_list_type:
            return {'error': '{} type tax can be filled only once'.format(tax.tax_type)}
        tax_list_type.append(tax.tax_type)
    if 'gst' not in tax_list_type:
        return {'error': 'Please fill the GST tax value'}
    return {'tax': tax_obj}


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
            return {'error': '{} packing_sku not found'.format(pack_mat_data['packing_sku'])}

    return {'packing_material_product': product}


def get_source_product(source_product_pro):
    """ validate id that belong to a ProductPackingMapping model """
    for pack_mat_data in source_product_pro:
        try:
            product = Product.objects.get(id=pack_mat_data['source_sku'], repackaging_type='source')
        except Exception as e:
            logger.error(e)
            return {'error': '{} source_sku not found'.format(pack_mat_data['source_sku'])}

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


def get_csv_file_data(csv_file, csv_file_headers):

    uploaded_data_by_user_list = []
    excel_dict = {}
    count = 0
    for row in csv_file:
        for ele in row:
            excel_dict[csv_file_headers[count]] = ele
            count += 1
        uploaded_data_by_user_list.append(excel_dict)
        excel_dict = {}
        count = 0

    return uploaded_data_by_user_list


def read_file(csv_file, upload_master_data, category):
    """
        Template Validation (Checking, whether the csv file uploaded by user is correct or not!)
    """
    excel_file_header_list = next(csv_file)  # headers of the uploaded excel file
    # Converting headers into lowercase
    excel_file_headers = [str(ele).lower() for ele in
                          excel_file_header_list]

    if upload_master_data == "sub_brand_with_brand":
        required_header_list = ['brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name']

    if upload_master_data == "sub_category_with_category":
        required_header_list = ['category_id', 'category_name', 'sub_category_id', 'sub_category_name']

    if upload_master_data == "inactive_status":
        required_header_list = ['sku_id', 'sku_name', 'mrp', 'status']

    if upload_master_data == "parent_data":
        required_header_list = ['parent_id', 'parent_name', 'product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)',
                                'tax_3(surcharge)', 'inner_case_size', 'brand_id', 'brand_name', 'sub_brand_id',
                                'sub_brand_name', 'category_id', 'category_name', 'sub_category_id',
                                'sub_category_name', 'status', 'is_ptr_applicable', 'ptr_type', 'ptr_percent',
                                'is_ars_applicable', 'max_inventory_in_days', 'is_lead_time_applicable']

    if upload_master_data == "child_data":
        required_header_list = ['sku_id', 'sku_name', 'ean', 'mrp', 'weight_unit', 'weight_value',
                                'status', 'repackaging_type', 'source_sku_id', 'source_sku_name',
                                'raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour',
                                'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost', 'conversion_cost']

    if upload_master_data == "child_parent":
        required_header_list = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'status']

    check_headers(excel_file_headers, required_header_list)
    uploaded_data_by_user_list = get_csv_file_data(csv_file, excel_file_headers)
    # Checking, whether the user uploaded the data below the headings or not!
    if uploaded_data_by_user_list:
        check_mandatory_columns(uploaded_data_by_user_list, excel_file_headers, upload_master_data, category)
    else:
        raise ValidationError("Please add some data below the headers to upload it!")


def check_headers(excel_file_headers, required_header_list):
    for head in excel_file_headers:
        if not head in required_header_list:
            raise ValidationError((f"Invalid Header | {head} | Allowable headers for the upload "
                                   f"are: {required_header_list}"))


def check_mandatory_columns(uploaded_data_list, header_list, upload_master_data, category):
    if upload_master_data == "sub_brand_with_brand":
        row_num = 1
        mandatory_columns = ['brand_id', 'brand_name']
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(f"{mandatory_columns} are mandatory columns for 'Sub Brand and Brand Mapping'")
        for row in uploaded_data_list:
            row_num += 1
            if 'brand_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Brand_ID can't be empty")
            if 'brand_id' in row.keys() and row['brand_id'] == '':
                raise ValidationError(f"Row {row_num} | 'Brand_ID' can't be empty")
            if 'brand_name' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Brand_Name' can't be empty")
            if 'brand_name' in row.keys() and row['brand_name'] == '':
                raise ValidationError(f"Row {row_num} | 'Brand_Name' can't be empty")

    if upload_master_data == "sub_category_with_category":
        row_num = 1
        mandatory_columns = ['category_id', 'category_name']
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(f"{mandatory_columns} are mandatory columns"
                                      f" for 'Sub Category and Category Mapping'")
        for row in uploaded_data_list:
            row_num += 1
            if 'category_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Sub_Category_ID' can't be empty")
            if 'category_id' in row.keys() and row['category_id'] == '':
                raise ValidationError(f"Row {row_num} | 'Category_ID' can't be empty")
            if 'category_name' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Category_Name' can't be empty")
            if 'category_name' in row.keys() and row['category_name'] == '':
                raise ValidationError(f"Row {row_num} | 'Category_Name' can't be empty")

    if upload_master_data == "inactive_status":
        row_num = 1
        mandatory_columns = ['sku_id', 'sku_name', 'status']
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(f"{mandatory_columns} are mandatory columns for 'Set Inactive Status'")
        for row in uploaded_data_list:
            row_num += 1
            if 'status' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                      'Status cannot be empty')
            if 'status' in row.keys() and row['sku_id'] == '':
                raise ValidationError(f"Row {row_num} | 'Status' can't be empty")
            if 'sku_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'SKU_ID' can't be empty")
            if 'sku_id' in row.keys() and row['sku_id'] == '':
                raise ValidationError(f"Row {row_num} | 'SKU_ID' can't be empty")
            if 'sku_name' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'SKU_Name' can't be empty")
            if 'sku_name' in row.keys() and row['sku_name'] == '':
                raise ValidationError(f"Row {row_num} | 'SKU_Name' can't be empty")

    if upload_master_data == "parent_data":
        row_num = 1
        mandatory_columns = ['parent_id', 'parent_name', 'status']
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(f"{mandatory_columns} are mandatory columns for 'Set Parent Data'")
        for row in uploaded_data_list:
            row_num += 1
            if 'parent_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Parent_ID' is a mandatory field")
            if 'parent_id' in row.keys() and row['parent_id'] == '':
                raise ValidationError(f"Row {row_num} | 'Parent_ID' can't be empty")
            if 'parent_name' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Parent_Name' is a mandatory field")
            if 'parent_name' in row.keys() and row['parent_name'] == '':
                raise ValidationError(f"Row {row_num} | 'Parent_Name' can't be empty")
            if 'status' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                      'Status cannot be empty')
            if 'status' in row.keys() and row['status'] == '':
                raise ValidationError(f"Row {row_num} | 'Status' can't be empty")

    if upload_master_data == "child_data":
        mandatory_columns = ['sku_id', 'sku_name', 'status']
        row_num = 1
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(f"{mandatory_columns} are mandatory columns for 'Set Child Data'")
        for row in uploaded_data_list:
            row_num += 1
            if 'status' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Status can either be 'Active' or 'Deactivated'!" |
                                      'Status cannot be empty')
            if 'status' in row.keys() and row['sku_id'] == '':
                raise ValidationError(f"Row {row_num} | 'Status' can't be empty")
            if 'sku_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'SKU_ID' can't be empty")
            if 'sku_id' in row.keys() and row['sku_id'] == '':
                raise ValidationError(f"Row {row_num} | 'SKU_ID' can't be empty")
            if 'sku_name' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'SKU_Name' can't be empty")
            if 'sku_name' in row.keys() and row['sku_name'] == '':
                raise ValidationError(f"Row {row_num} | 'SKU_Name' can't be empty")

    if upload_master_data == "child_parent":
        row_num = 1
        mandatory_columns = ['sku_id', 'parent_id', 'status']
        for ele in mandatory_columns:
            if ele not in header_list:
                raise ValidationError(f"{mandatory_columns} are mandatory column for 'Child and Parent Mapping'")
        for row in uploaded_data_list:
            row_num += 1
            if 'sku_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'SKU_ID' can't be empty")
            if 'sku_id' in row.keys() and row['sku_id'] == '':
                raise ValidationError(f"Row {row_num} | 'SKU_ID' can't be empty")
            if 'parent_id' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Parent_ID' can't be empty")
            if 'parent_id' in row.keys() and row['parent_id'] == '':
                raise ValidationError(f"Row {row_num} | 'Parent_ID' can't be empty")
            if 'status' not in row.keys():
                raise ValidationError(f"Row {row_num} | 'Status can either be 'Active', 'Pending Approval' "
                                      f"or 'Deactivated'!" | 'Status cannot be empty')
            if 'status' in row.keys() and row['status'] == '':
                raise ValidationError(f"Row {row_num} | 'Status' can't be empty")

    validate_row(uploaded_data_list, header_list, category)


def validate_row(uploaded_data_list, header_list, category):
    """
        This method will check that Data uploaded by user is valid or not.
    """
    try:
        brand = Brand.objects.all()
        category = Category.objects.all()
        child_product = Product.objects.all()
        parent_products = ParentProduct.objects.all()
        product_hsn = ProductHSN.objects.all()
        tax = Tax.objects.all()
        row_num = 1
        for row in uploaded_data_list:
            row_num += 1
            if 'brand_id' in header_list and 'brand_id' in row.keys() and row['brand_id'] != '':
                if not brand.filter(id=row['brand_id']).exists():
                    raise ValidationError(f"Row {row_num} | {row['brand_id']} | "
                                          f"'Brand_ID' doesn't exist in the system ")

            if 'brand_name' in header_list and 'brand_name' in row.keys() and row['brand_name'] != '':
                if not brand.filter(brand_name=row['brand_name']).exists():
                    raise ValidationError(f"Row {row_num} | {row['brand_name']} | "
                                          f"'Brand_Name' doesn't exist in the system ")

            if 'sub_brand_id' in header_list and 'sub_brand_id' in row.keys() and row['sub_brand_id'] != '':
                if not brand.filter(id=row['sub_brand_id']).exists():
                    raise ValidationError(f"Row {row_num} | {row['sub_brand_id']} | "
                                          f"'Sub_Brand_ID' doesn't exist in the system ")

            if 'sub_brand_name' in header_list and 'sub_brand_id' in row.keys() and row['sub_brand_name'] != '':
                if not brand.filter(brand_name=row['sub_brand_name']).exists():
                    raise ValidationError(f"Row {row_num} | {row['sub_brand_name']} | "
                                          f"'Sub_Brand_Name' doesn't exist in the system ")

            if 'category_id' in header_list and 'category_id' in row.keys() and row['category_id'] != '':
                if not category.filter(id=row['category_id']).exists():
                    raise ValidationError(f"Row {row_num} | {row['category_id']} | "
                                          f"'Category_ID' doesn't exist in the system ")

            if 'category_name' in header_list and 'category_name' in row.keys() and row['category_name'] != '':
                if not category.filter(category_name=row['category_name']).exists():
                    raise ValidationError(f"Row {row_num} | {row['category_name']} | "
                                          f"'Category_Name' doesn't exist in the system ")

            if 'sub_category_id' in header_list and 'sub_category_id' in row.keys() and row['sub_category_id'] != '':
                if not category.filter(id=row['sub_category_id']).exists():
                    raise ValidationError(f"Row {row_num} | {row['sub_category_id']} | "
                                          f"'Sub_Category_ID' doesn't exist in the system ")

            if 'sub_category_name' in header_list and 'sub_category_name' in row.keys() and row['sub_category_name'] != '':
                if not category.filter(category_name=row['sub_category_name']).exists():
                    raise ValidationError(f"Row {row_num} | {row['sub_category_name']} | "
                                          f"'Sub_Category_Name' doesn't exist in the system ")

            if 'sku_id' in header_list and 'sku_id' in row.keys():
                if row['sku_id'] != '':
                    if not child_product.filter(product_sku=row['sku_id']).exists():
                        raise ValidationError(f"Row {row_num} | {row['sku_id']} | 'SKU ID' doesn't exist.")
                product = child_product.filter(product_sku=row['sku_id'])
                if not child_product.filter(id=product[0].id, parent_product__parent_product_pro_category__category__category_name__icontains=
                                            category.category_name).exists():
                    raise ValidationError(f"Row {row_num} | Please upload Products of Category "
                                          f"({category.category_name}) that you have selected in Dropdown Only! ")

            if 'sku_name' in header_list and 'sku_name' in row.keys() and row['sku_name'] != '':
                if not child_product.filter(product_name=row['sku_name']).exists():
                    raise ValidationError(f"Row {row_num} | {row['sku_name']} | 'SKU Name' doesn't exist in the system.")

            if 'status' in header_list and 'status' in row.keys() and row['status'] != '':
                status_list = ['active', 'deactivated', 'pending_approval']
                if row['status'] not in status_list:
                    raise ValidationError(f"Row {row_num} | {row['status']} | 'Status can either be 'Active', "
                                          f"'Pending Approval' or 'Deactivated'!")

            if 'parent_id' in header_list and 'parent_id' in row.keys():
                if row['parent_id'] != '':
                    if not parent_products.filter(parent_id=row['parent_id']).exists():
                        raise ValidationError(f"Row {row_num} | {row['parent_id']} | 'Parent ID' doesn't exist.")
                parent_product = parent_products.filter(parent_id=row['parent_id'])
                if 'sku_id' not in row.keys():
                    if not ParentProductCategory.objects.filter(category=category.id,
                                                                parent_product=parent_product[0].id).exists():
                        category = Category.objects.values('category_name').filter(id=category.category_name)
                        raise ValidationError(f"Row {row_num} | Please upload Products of Category "
                                              f"{category.category_name}) that you have selected in Dropdown Only! ")

            if 'parent_name' in header_list and 'parent_name' in row.keys() and row['parent_name'] != '':
                if not parent_products.filter(name=row['parent_name']).exists():
                    raise ValidationError(f"Row {row_num} | {row['parent_name']} | 'Parent Name' doesn't exist.")

            if 'hsn' in header_list and 'hsn' in row.keys() and row['hsn'] != '':
                if not product_hsn.filter(product_hsn_code=row['hsn']).exists() and not product_hsn.filter(
                        product_hsn_code='0' + str(row['hsn'])).exists():
                    raise ValidationError(f"Row {row_num} | {row['hsn']} | 'HSN' doesn't exist in the system.")

            if 'tax_1(gst)' in header_list and 'tax_1(gst)' in row.keys() and row['tax_1(gst)'] != '':
                if not tax.filter(tax_name=row['tax_1(gst)']).exists():
                    raise ValidationError(f"Row {row_num} | {row['tax_1(gst)']} | Invalid Tax(GST)!")

            if 'tax_2(cess)' in header_list and 'tax_2(cess)' in row.keys() and row['tax_2(cess)'] != '':
                if not tax.filter(tax_name=row['tax_2(cess)']).exists():
                    raise ValidationError(f"Row {row_num} | {row['tax_2(cess)']} Invalid Tax(CESS)!")

            if 'tax_3(surcharge)' in header_list and 'tax_3(surcharge)' in row.keys() and row['tax_3(surcharge)'] != '':
                if not tax.filter(tax_name=row['tax_3(surcharge)']).exists():
                    raise ValidationError(f"Row {row_num} | {row['tax_3(surcharge)']} Invalid Tax(Surcharge)!")

            if 'inner_case_size' in header_list and 'inner_case_size' in row.keys() and row['inner_case_size'] != '':
                if not re.match("^\d+$", str(row['inner_case_size'])):
                    raise ValidationError(f"Row {row_num} | {row['inner_case_size']} "
                                          f"'Inner Case Size' can only be a numeric value.")

            if 'max_inventory_in_days' in header_list and 'max_inventory_in_days' in row.keys() \
                    and row['max_inventory_in_days'] != '':
                if not re.match("^\d+$", str(row['max_inventory_in_days'])) or row['max_inventory_in_days'] < 1 \
                        or row['max_inventory_in_days'] > 999:
                    raise ValidationError(f"Row {row_num} | {row['max_inventory_in_days']} |"
                                          f"'Max Inventory In Days' is invalid.")

            if 'is_ars_applicable' in header_list and 'is_ars_applicable' in row.keys() and row['is_ars_applicable'] != '':
                if str(row['is_ars_applicable']).lower() not in ['yes', 'no']:
                    raise ValidationError(f"Row {row_num} | {row['is_ars_applicable']} | "
                                          f"'is_ars_applicable' can only be 'Yes' or 'No' ")

            if 'is_lead_time_applicable' in header_list and 'is_lead_time_applicable' in row.keys() and \
                    row['is_lead_time_applicable'] != '':
                if str(row['is_lead_time_applicable']).lower() not in ['yes', 'no']:
                    raise ValidationError(f"Row {row_num} | {row['is_lead_time_applicable']} |"
                          f"'is_lead_time_applicable' can only be 'Yes' or 'No' ")

            if 'is_ptr_applicable' in header_list and 'is_ptr_applicable' in row.keys():
                if row['is_ptr_applicable'] != '' and str(row['is_ptr_applicable']).lower() not in ['yes', 'no']:
                    raise ValidationError(f"Row {row_num} | {row['is_ptr_applicable']} | "
                                          f"'is_ptr_applicable' can only be 'Yes' or 'No' ")
                elif row['is_ptr_applicable'].lower() == 'yes' and \
                        ('ptr_type' not in row.keys() or row['ptr_type'] == '' or row['ptr_type'].lower() not in [
                            'mark up', 'mark down']):
                    raise ValidationError(f"Row {row_num} | 'ptr_type' can either be 'Mark Up' or 'Mark Down' ")
                elif row['is_ptr_applicable'].lower() == 'yes' \
                        and ('ptr_percent' not in row.keys() or row['ptr_percent'] == '' or 100 < row['ptr_percent']
                             or row['ptr_percent'] < 0):
                    raise ValidationError(f"Row {row_num} | 'ptr_percent' is invalid")

            if 'product_type' in header_list and 'product_type' in row.keys() and row['product_type'] != '':
                product_type_list = ['b2b', 'b2c', 'both']
                if row['product_type'] not in product_type_list:
                    raise ValidationError(f"Row {row_num} | {row['product_type']} | 'Product Type can either be "
                                          f"'b2b', 'b2c' or 'both'!")

            if 'mrp' in header_list and 'mrp' in row.keys() and row['mrp'] != '':
                if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
                    raise ValidationError(f"Row {row_num} | 'Product MRP' can only be a numeric value.")

            if 'weight_unit' in header_list and 'weight_unit' in row.keys() and row['weight_unit'] != '':
                if str(row['weight_unit']).lower() not in ['gm']:
                    raise ValidationError(f"Row {row_num} | 'Weight Unit' can only be 'gm'.")

            if 'weight_value' in header_list and 'weight_value' in row.keys() and row['weight_value'] != '':
                if not re.match("^\d+[.]?[\d]{0,2}$", str(row['weight_value'])):
                    raise ValidationError(f"Row {row_num} |' Weight Value' can only be a numeric value.")

            if 'repackaging_type' in header_list and 'repackaging_type' in row.keys() and row['repackaging_type'] != '':
                repack_type = ['none', 'source', 'destination', 'packing_material']
                if row['repackaging_type'] not in repack_type:
                    raise ValidationError(f"Row {row_num} | {row['repackaging_type']} | 'Repackaging Type can either be "
                                          f"'none','source', 'destination' or 'packing_material'!")

            if 'repackaging_type' in header_list and 'repackaging_type' in row.keys() and row['repackaging_type'] == 'destination':
                mandatory_fields = ['raw_material', 'wastage', 'fumigation', 'label_printing',
                                    'packing_labour', 'primary_pm_cost', 'secondary_pm_cost', 'final_fg_cost',
                                    'conversion_cost']
                if 'source_sku_id' not in row.keys():
                    raise ValidationError(f"Row {row_num} | 'Source_SKU_ID' can't be empty when "
                                          f"repackaging_type is destination")
                if 'source_sku_id' in row.keys() and row['source_sku_id'] == '':
                    raise ValidationError(f"Row {row_num} | 'Source_SKU_ID' can't be empty "
                                          f"when repackaging_type is destination")
                if 'source_sku_name' not in row.keys():
                    raise ValidationError(f"Row {row_num} | 'Source_SKU_Name' can't be empty "
                                          f"when repackaging_type is destination")
                if 'source_sku_name' in row.keys() and row['source_sku_name'] == '':
                    raise ValidationError(f"Row {row_num} | 'Source_SKU_Name' can't be empty when "
                                          f"repackaging_type is destination")
                for field in mandatory_fields:
                    if field not in header_list:
                        raise ValidationError(f"{mandatory_fields} are the essential headers and cannot be empty "
                                              f"when repackaging_type is destination")
                    if row[field] == '':
                        raise ValidationError(f"Row {row_num} | {row[field]} | {field} cannot be empty {mandatory_fields} "
                                              f" are the essential fields when repackaging_type is destination")
                    if not re.match("^\d+[.]?[\d]{0,2}$", str(row[field])):
                        raise ValidationError(f"Row {row_num} | {row[field]} | {field} "
                                              f"can only be a numeric or decimal value.")

                if 'source_sku_id' in header_list and 'source_sku_id' in row.keys() and row['source_sku_id'] != '':
                    p = re.compile('\'')
                    sku_ids = p.sub('\"', row['source_sku_id'])
                    sku_id_data = json.loads(sku_ids)
                    for sk in sku_id_data:
                        if not child_product.filter(product_sku=sk).exists():
                            raise ValidationError(f"Row {row_num} | {sk} | 'Source SKU ID' doesn't exist.")
                if 'source_sku_name' in header_list and 'source_sku_name' in row.keys() and row['source_sku_name'] != '':
                    q = re.compile('\'')
                    source_sku_name = q.sub('\"', row['source_sku_name'])
                    sku_names = json.loads(source_sku_name)
                    for sk in sku_names:
                        if not child_product.filter(product_name=sk).exists():
                            raise ValidationError(f"Row {row_num} | {sk} | 'Source SKU Name' doesn't exist in"
                                                  f" the system.")
    except ValueError as e:
        raise ValidationError(f"Row {row_num} | ValueError : {e} | Please Enter valid Data")
    except KeyError as e:
        raise ValidationError(f"Row {row_num} | KeyError : {e} | Something went wrong while "
                              f"checking excel data from dictionary")
