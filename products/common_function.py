import logging
from rest_framework import status
from rest_framework.response import Response

from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
     ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping, ChildProductImage, ProductImage, \
    ProductSourceMapping, DestinationRepackagingCostMapping, ProductPackingMapping, CentralLog
from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_product,\
    get_validate_seller_shop, get_validate_vendor, get_validate_parent_product
from categories.models import Category
from wms.models import Out, WarehouseInventory, BinInventory
from brand.models import Brand

# Get an instance of a logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')


class ParentProductCls(object):

    @classmethod
    def upload_parent_product_images(cls, parent_product,  parent_product_pro_image, product_images):
        """
            Delete Existing Images of specific ParentProduct if any
            Create Parent Product Images
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
    def create_parent_product_log(cls, log_obj):
        """
            Create Parent Product Log
        """
        parent_product_log = CentralLog.objects.create(parent_product=log_obj, updated_by=log_obj.updated_by)

        dict_data = {'updated_by': log_obj.updated_by, 'updated_at': log_obj.updated_at,
                     'product_id': log_obj}
        info_logger.info("parent product update info ", dict_data)

        return parent_product_log


class ProductCls(object):

    @classmethod
    def create_child_product(cls, parent_product,  **validated_data):
        """
           Create Child Product
        """
        parent_product_obj = get_validate_parent_product(parent_product)
        return Product.objects.create(parent_product=parent_product_obj['parent_product'], **validated_data)

    @classmethod
    def upload_child_product_images(cls, child_product, product_images, product_pro_image):
        """
           Delete Existing Images of specific ParentProduct if any
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
                                                 packing_sku_weight_per_unit_sku=source_sku_data['packing_sku_weight_per_unit_sku'])

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
    def update_product_vendor_mapping(cls, product, vendor,  product_vendor_map):
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
    def create_child_product_log(cls, log_obj):
        """
            Create Child Product Log
        """
        child_product_log = CentralLog.objects.create(child_product=log_obj, updated_by=log_obj.updated_by)

        dict_data = {'updated_by': log_obj.updated_by, 'updated_at': log_obj.updated_at,
                     'child_product': log_obj}
        info_logger.info("child product update info ", dict_data)

        return child_product_log


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


class BulkMasterUploadCls(object):

    @classmethod
    def set_sub_brand_and_brand(cls, validated_data):
        """
            Updating Brand & Sub Brand
        """
        try:
            count = 0
            row_num = 1
            sub_brand = []
            info_logger.info('Method Start to set the Sub-brand to Brand mapping from excel file')
            for row in validated_data:
                count += 1
                row_num += 1
                try:
                    if 'sub_brand_id' in row.keys():
                        if row['sub_brand_id'] == row['brand_id']:
                            continue
                        else:
                            if row['sub_brand_id'] == '':
                                continue
                            else:
                                Brand.objects.filter(id=row['sub_brand_id']).update(brand_parent=row['brand_id'])
                except:
                    sub_brand.append(str(row_num))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Sub brand is not updated in these row :" + str(sub_brand))
            info_logger.info("Method complete to set the Sub-Brand to Brand mapping from csv file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Sub Brand and Brand Functionality' + {str(e)}")


def get_excel_file_data(excel_file):
    headers = excel_file.pop(0)  # headers of the uploaded excel file
    excelFile_headers = [str(ele).lower() for ele in headers]  # Converting headers into lowercase

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