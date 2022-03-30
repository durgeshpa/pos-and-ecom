import logging

from rest_framework import status
from rest_framework.response import Response
from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
    ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping, ChildProductImage, ProductImage, \
    ProductSourceMapping, DestinationRepackagingCostMapping, ProductPackingMapping, CentralLog, ParentProductB2cCategory
from categories.models import Category, B2cCategory
from sp_to_gram.tasks import get_product_price
from wms.models import Out, WarehouseInventory, BinInventory

from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_product, \
    get_validate_seller_shop, get_validate_vendor, get_validate_parent_product, get_csv_file_data

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ParentProductCls(object):

    @classmethod
    def upload_parent_product_images(cls, parent_product, parent_product_pro_image, product_images):
        """
            Delete Existing Images of specific ParentProduct
            Create or Update Parent Product Images
        """
        ids = []
        if parent_product_pro_image:
            for image in parent_product_pro_image:
                ids.append(image['id'])

        ParentProductImage.objects.filter(parent_product=parent_product).exclude(
            id__in=ids).delete()
        if product_images:
            for image in product_images:
                ParentProductImage.objects.create(image=image, image_name=image.name.rsplit(".", 1)[0],
                                                  parent_product=parent_product)

    @classmethod
    def create_parent_product_category(cls, parent_product, parent_product_pro_category):
        """
             Delete Existing Category of specific ParentProduct if any
             Create Parent Product Categories
        """
        parent_cat = ParentProductCategory.objects.filter(parent_product=parent_product)
        if parent_cat.exists():
            parent_cat.delete()

        for product_category in parent_product_pro_category:
            category = Category.objects.get(id=product_category['category'])
            ParentProductCategory.objects.create(parent_product=parent_product, category=category)
    
    @classmethod
    def create_parent_product_b2c_category(cls, parent_product, parent_product_pro_b2c_category):
        """
             Delete Existing Category of specific ParentProduct if any
             Create Parent Product B2c Categories
        """
        parent_cat = ParentProductB2cCategory.objects.filter(parent_product=parent_product)
        if parent_cat.exists():
            parent_cat.delete()

        for product_category in parent_product_pro_b2c_category:
            category = B2cCategory.objects.get(id=product_category['category'])
            ParentProductB2cCategory.objects.create(parent_product=parent_product, category=category)

    @classmethod
    def create_parent_product_tax(cls, parent_product, parent_product_pro_tax):
        """
            Delete Existing Tax of specific ParentProduct if any
            Create Parent Product Tax
        """
        parent_tax = ParentProductTaxMapping.objects.filter(parent_product=parent_product)
        if parent_tax.exists():
            parent_tax.delete()

        for tax_data in parent_product_pro_tax:
            tax = Tax.objects.get(id=tax_data['tax'])
            ParentProductTaxMapping.objects.create(parent_product=parent_product, tax=tax)

    @classmethod
    def create_parent_product_log(cls, log_obj, action):
        """
            Create Parent Product Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        parent_product_log = CentralLog.objects.create(parent_product=log_obj, updated_by=create_updated_by,
                                                       action=action)
        dict_data = {'updated_by': parent_product_log.updated_by, 'updated_at': parent_product_log.update_at,
                     'product_id': log_obj, }
        info_logger.info("parent product update info ", dict_data)

        return parent_product_log


class ProductCls(object):

    @classmethod
    def create_child_product(cls, parent_product, **validated_data):
        """
           Create Child Product
        """
        parent_product_obj = get_validate_parent_product(parent_product)
        return Product.objects.create(parent_product=parent_product_obj['parent_product'], **validated_data)

    @classmethod
    def upload_child_product_images(cls, child_product, product_images, product_pro_image):
        """
           Delete Existing Images of specific ParentProduct
           Create Parent Product Images
        """
        ids = []
        if product_pro_image:
            for image in product_pro_image:
                ids.append(image['id'])

        ProductImage.objects.filter(product=child_product).exclude(
            id__in=ids).delete()

        if product_images:
            for image in product_images:
                ProductImage.objects.create(image=image, image_name=image.name.rsplit(".", 1)[0],
                                            product=child_product)

    @classmethod
    def update_child_product(cls, parent_product, child_product):
        """
            Update Parent Product
        """
        parent_product_obj = get_validate_parent_product(parent_product)
        child_product.parent_product = parent_product_obj['parent_product']
        child_product.save()
        return child_product

    @classmethod
    def create_source_product_mapping(cls, child_product, source_sku):
        """
            Create Source Product Mapping
        """
        source_pro_map = ProductSourceMapping.objects.filter(destination_sku=child_product)
        if source_pro_map.exists():
            source_pro_map.delete()

        for source_sku_data in source_sku:
            source_sku_id = Product.objects.get(id=source_sku_data['source_sku'])
            ProductSourceMapping.objects.create(destination_sku=child_product, source_sku=source_sku_id)

    @classmethod
    def packing_material_product_mapping(cls, child_product, packing_material_rt):
        """
            Create Packing Material Product Mapping
        """
        pro_pac_mat = ProductPackingMapping.objects.filter(sku=child_product)
        if pro_pac_mat.exists():
            pro_pac_mat.delete()

        for source_sku_data in packing_material_rt:
            pack_sku_id = Product.objects.get(id=source_sku_data['packing_sku'])
            ProductPackingMapping.objects.create(sku=child_product, packing_sku=pack_sku_id,
                                                 packing_sku_weight_per_unit_sku=source_sku_data[
                                                     'packing_sku_weight_per_unit_sku'])

    @classmethod
    def create_destination_product_mapping(cls, child_product, destination_product_repackaging):
        """
            Create Destination Product Mapping
        """
        dest_rep_cost_map = DestinationRepackagingCostMapping.objects.filter(destination=child_product)
        if dest_rep_cost_map.exists():
            dest_rep_cost_map.delete()

        for pro_des_data in destination_product_repackaging:
            DestinationRepackagingCostMapping.objects.create(destination=child_product, **pro_des_data)

    @classmethod
    def update_weight_inventory(cls, child_product):
        """
            Update WarehouseInventory
        """
        warehouse_inv = WarehouseInventory.objects.filter(sku=child_product)
        for inv in warehouse_inv:
            inv.weight = inv.quantity * child_product.weight_value
            inv.save()
        bin_inv = BinInventory.objects.filter(sku=child_product)
        for inv in bin_inv:
            inv.weight = inv.quantity * child_product.weight_value
            inv.save()

    @classmethod
    def create_product_capping(cls, product, seller_shop, **validated_data):
        """
            Create Product Capping
        """
        product_obj = get_validate_product(product)
        seller_shop_obj = get_validate_seller_shop(seller_shop)
        return ProductCapping.objects.create(product=product_obj['product'],
                                             seller_shop=seller_shop_obj['seller_shop'], **validated_data)

    @classmethod
    def create_product_vendor_mapping(cls, product, vendor, **validated_data):
        """
            Create Product Vendor Mapping
        """
        product_obj = get_validate_product(product)
        vendor_obj = get_validate_vendor(vendor)
        return ProductVendorMapping.objects.create(product=product_obj['product'],
                                                   vendor=vendor_obj['vendor'], **validated_data)

    @classmethod
    def update_product_vendor_mapping(cls, product, vendor, product_vendor_map):
        """
            Update Product Vendor Mapping
        """
        product_obj = get_validate_product(product)
        vendor_obj = get_validate_vendor(vendor)
        product_vendor_map.product = product_obj['product']
        product_vendor_map.vendor = vendor_obj['vendor']
        product_vendor_map.save()
        return product_vendor_map

    @classmethod
    def create_child_product_log(cls, log_obj, action):
        """
            Create Child Product Log
        """

        action, create_updated_by = created_updated_by(log_obj, action)
        child_product_log = CentralLog.objects.create(child_product=log_obj, updated_by=create_updated_by,
                                                      action=action)
        dict_data = {'updated_by': child_product_log.updated_by, 'update_at': child_product_log.update_at,
                     'child_product': log_obj}
        info_logger.info("child product update info ", dict_data, )

        return child_product_log

    @classmethod
    def create_tax_log(cls, log_obj, action):
        """
            Create Tax Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        tax_log = CentralLog.objects.create(tax=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': tax_log.updated_by, 'update_at': tax_log.update_at, 'tax': log_obj}
        info_logger.info("tax update info ", dict_data)

        return tax_log

    @classmethod
    def create_hsn_log(cls, log_obj, action):
        """
            Create HSN Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        hsn_log = CentralLog.objects.create(hsn=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': hsn_log.updated_by, 'update_at': hsn_log.update_at, 'hsn': log_obj}
        info_logger.info("hsn update info ", dict_data)

        return hsn_log

    @classmethod
    def create_weight_log(cls, log_obj, action):
        """
            Create Weight Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        weight_log = CentralLog.objects.create(weight=log_obj, updated_by=create_updated_by, action=action)
        dict_data = {'updated_by': weight_log.updated_by, 'updated_at': weight_log.update_at, 'weight': log_obj}
        info_logger.info("weight_log update info ", dict_data)

        return weight_log

    @classmethod
    def create_product_vendor_map_log(cls, log_obj, action):
        """
            Create Product Vendor Mapping Log
        """
        action, create_updated_by = created_updated_by(log_obj, action)
        product_vendor_map_log = CentralLog.objects.create(product_vendor_map=log_obj, updated_by=create_updated_by,
                                                           action=action)
        dict_data = {'updated_by': product_vendor_map_log.updated_by, 'update_at': product_vendor_map_log.update_at,
                     'product_vendor_map': log_obj}
        info_logger.info("product vendor mapping update info ", dict_data)

        return product_vendor_map_log


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True, "message": msg, "response_data": data}
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


def created_updated_by(log_obj, action):
    if action == "created":
        create_updated_by = log_obj.created_by
    else:
        create_updated_by = log_obj.updated_by

    return action, create_updated_by


def get_b2c_product_details(product):
    user_selected_qty = None
    no_of_pieces = None
    sub_total = None
    available_qty = 0
    status = True
    mrp = product.product_mrp
    product_price_dict = get_product_price(None, [product.id])
    product_price = product_price_dict.get(product.id)
    margin = 0
    ptr = 0
    pack_size = None
    brand_case_size = None
    try:
        pack_size = product.product_inner_case_size if product.product_inner_case_size else None
    except Exception as e:
        info_logger.exception("pack size is not defined for {}".format(product.product_name))

    try:
        brand_case_size = product.product_case_size if product.product_case_size else None
    except Exception as e:
        info_logger.exception("brand case size is not defined for {}".format(product.product_name))

    price_details = []
    if product_price:
        price_details = product_price

    product_opt = product.product_opt_product.all()
    weight_value = None
    weight_unit = None
    try:
        for p_o in product_opt:
            weight_value = p_o.weight.weight_value if p_o.weight.weight_value else None
            weight_unit = p_o.weight.weight_unit if p_o.weight.weight_unit else None
    except:
        weight_value = None
        weight_unit = None
    if weight_unit is None:
        weight_unit = product.weight_unit
    if weight_value is None:
        weight_value = product.weight_value

    product_img = product.product_pro_image.all()
    product_images = [
        {
            "image_name": p_i.image_name,
            # "image_alt": p_i.image_alt_text,
            "image_url": p_i.image.url
        }
        for p_i in product_img
    ]
    if not product_images:
        if product.use_parent_image:
            product_images = [
                {
                    "image_name": p_i.image_name,
                    # "image_alt": p_i.image_alt_text,
                    "image_url": p_i.image.url
                }
                for p_i in product.parent_product.parent_product_pro_image.all()
            ]
        else:
            product_images = [
                {
                    "image_name": p_i.image_name,
                    # "image_alt": p_i.image_alt_text,
                    "image_url": p_i.image.url
                }
                for p_i in product.child_product_pro_image.all()
            ]

    product_categories = [str(c.category) for c in
                          product.parent_product.parent_product_pro_category.filter(status=True)]
    b2c_product_categories = [str(b2c_c.category) for b2c_c in
                              product.parent_product.parent_product_pro_b2c_category.filter(status=True)]

    visible = True
    ean = product.product_ean_code
    if ean and type(ean) == str:
        ean = ean.split('_')[0]
    is_discounted = True if product.product_type == Product.PRODUCT_TYPE_CHOICE.DISCOUNTED else False
    expiry_date = None
    product_details = {
        "sku": product.product_sku,
        "parent_id": product.parent_product.parent_id,
        "parent_name": product.parent_product.name,
        "name": product.product_name,
        "name_lower": product.product_name.lower(),
        "brand": str(product.product_brand),
        "brand_lower": str(product.product_brand).lower(),
        "category": product_categories,
        "bc2_category": b2c_product_categories,
        "mrp": mrp,
        "status": status,
        "id": product.id,
        "weight_value": weight_value,
        "weight_unit": weight_unit,
        "product_images": product_images,
        "user_selected_qty": user_selected_qty,
        "pack_size": pack_size,
        "brand_case_size": brand_case_size,
        "margin": margin,
        "no_of_pieces": no_of_pieces,
        "sub_total": sub_total,
        "available": available_qty,
        "visible": visible,
        "ean": ean,
        "price_details": price_details,
        "is_discounted": is_discounted,
        "expiry_date": expiry_date
    }
    info_logger.info("inside get_b2c_product_details product_details: " + str(product_details))
    return product_details


def generate_tax_group_name_by_the_mapped_taxes(taxes_instance):
    group_names = []
    tax_types = ['gst', 'cess']
    for tax_type in tax_types:
        taxes = taxes_instance.filter(tax_type__iexact=tax_type).\
            values_list('tax_percentage', flat=True)
        if taxes:
            group_names.append(''.join([tax_type.upper()] + [str(int(x)) for x in taxes]))
    return '_'.join(group_names)
