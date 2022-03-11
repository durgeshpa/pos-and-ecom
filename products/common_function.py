import codecs
import csv
import logging
from functools import wraps

from rest_framework import status
from rest_framework.response import Response
from products.models import Product, Tax, ParentProductTaxMapping, ParentProduct, ParentProductCategory, \
    ParentProductImage, ProductHSN, ProductCapping, ProductVendorMapping, ChildProductImage, ProductImage, \
    ProductSourceMapping, DestinationRepackagingCostMapping, ProductPackingMapping, CentralLog, \
    ParentProductB2cCategory, ProductHsnGst, ProductHsnCess, ParentProductTaxApprovalLog
from categories.models import Category, B2cCategory
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

    @classmethod
    def update_tax_status_and_remark(cls, parent_product):
        """
            Update Tax status and remark of specific ParentProduct on the basis of Parent Product Tax in HSN
        """
        if parent_product.tax_status != ParentProduct.APPROVED:
            parent_taxs = ParentProductTaxMapping.objects.filter(parent_product=parent_product)
            product_hsn_gsts = parent_product.product_hsn.hsn_gst.values_list('gst', flat=True)
            product_hsn_cess = parent_product.product_hsn.hsn_cess.values_list('cess', flat=True)
            tax_status = None
            tax_remark = None
            if parent_taxs.filter(tax__tax_type='gst').exists():
                if parent_taxs.filter(tax__tax_type='gst').last().tax.tax_percentage in product_hsn_gsts:
                    if len(product_hsn_gsts) == 1:
                        tax_status = ParentProduct.APPROVED
                    else:
                        tax_status = ParentProduct.PENDING
                        tax_remark = ParentProduct.GST_MULTIPLE_RATES
                else:
                    tax_status = ParentProduct.PENDING
                    tax_remark = ParentProduct.GST_RATE_MISMATCH
            if parent_taxs.filter(tax__tax_type='cess').exists():
                if parent_taxs.filter(tax__tax_type='cess').last().tax.tax_percentage in product_hsn_cess:
                    if len(product_hsn_cess) == 1:
                        tax_status = ParentProduct.PENDING \
                            if tax_status == ParentProduct.PENDING else ParentProduct.APPROVED
                    else:
                        tax_status = ParentProduct.PENDING
                        tax_remark = ParentProduct.GST_AND_CESS_MULTIPLE_RATES \
                            if tax_remark == ParentProduct.GST_MULTIPLE_RATES else \
                            ParentProduct.CESS_MULTIPLE_RATES_AND_GST_RATE_MISMATCH if \
                                tax_remark == ParentProduct.GST_RATE_MISMATCH else ParentProduct.CESS_MULTIPLE_RATES
                else:
                    tax_status = ParentProduct.PENDING
                    tax_remark = ParentProduct.GST_AND_CESS_RATE_MISMATCH \
                        if tax_remark == ParentProduct.GST_RATE_MISMATCH else \
                        ParentProduct.GST_MULTIPLE_RATES_AND_CESS_RATE_MISMATCH if \
                            tax_remark == ParentProduct.GST_MULTIPLE_RATES else ParentProduct.CESS_RATE_MISMATCH
            if tax_status or tax_remark:
                parent_product.tax_status = tax_status
                parent_product.tax_remark = tax_remark
                parent_product.save()
                ParentProductCls.update_tax_status_and_remark_in_log(
                    parent_product, tax_status, tax_remark,
                    parent_product.updated_by if parent_product.updated_by else parent_product.created_by)

    @classmethod
    def update_tax_status_and_remark_in_log(cls, parent_product, tax_status, tax_remark, user):
        """
            Update Tax status and remark of specific ParentProduct in Logs
        """
        tax_log = ParentProductTaxApprovalLog.objects.filter(parent_product=parent_product).last()
        if not tax_log or tax_log.tax_status != tax_status or tax_log.tax_remark != tax_remark:
            ParentProductTaxApprovalLog.objects.create(
                parent_product=parent_product, tax_status=tax_status, tax_remark=tax_remark, created_by=user)


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


class ProductHSNCommonFunction(object):

    @classmethod
    def create_product_hsn(cls, validated_data, user):
        """
           Create Product HSNs
        """
        csv_file = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
        # Converting headers into lowercase
        csv_file_headers = [str(ele).split(' ')[0].strip().lower() for ele in csv_file_header_list]
        uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
        try:
            info_logger.info('Method Start to create / update Product HSN')
            for row in uploaded_data_by_user_list:
                product_hsn_object, created = ProductHSN.objects.update_or_create(
                    product_hsn_code=int(row['product_hsn_code']), defaults={'created_by': user})

                # Delete existing and create new HSN GST
                if product_hsn_object.hsn_gst.exists():
                    product_hsn_object.hsn_gst.all().delete()
                ProductHSNCommonFunction.create_product_hsn_gst(product_hsn_object, float(row['gst_rate_1']), user)
                if 'gst_rate_2' in row and row['gst_rate_2']:
                    ProductHSNCommonFunction.create_product_hsn_gst(product_hsn_object, float(row['gst_rate_2']), user)
                if 'gst_rate_3' in row and row['gst_rate_3']:
                    ProductHSNCommonFunction.create_product_hsn_gst(product_hsn_object, float(row['gst_rate_3']), user)

                # Delete existing and create new HSN Cess
                if product_hsn_object.hsn_cess.exists():
                    product_hsn_object.hsn_cess.all().delete()
                if 'cess_rate_1' in row and row['cess_rate_1']:
                    ProductHSNCommonFunction.create_product_hsn_cess(product_hsn_object, float(row['cess_rate_1']), user)
                if 'cess_rate_2' in row and row['cess_rate_2']:
                    ProductHSNCommonFunction.create_product_hsn_cess(product_hsn_object, float(row['cess_rate_2']), user)
                if 'cess_rate_3' in row and row['cess_rate_3']:
                    ProductHSNCommonFunction.create_product_hsn_cess(product_hsn_object, float(row['cess_rate_3']), user)

            info_logger.info("Method complete to create Product HSN from csv file")
        except Exception as e:
            import traceback;
            traceback.print_exc()
            error_logger.info(f"Something went wrong, while working with create Product HSN {str(e)}")

    @classmethod
    def create_product_hsn_gst(cls, product_hsn_instance, gst, user):
        return ProductHsnGst.objects.create(product_hsn=product_hsn_instance, gst=gst, created_by=user)

    @classmethod
    def create_product_hsn_cess(cls, product_hsn_instance, cess, user):
        return ProductHsnCess.objects.create(product_hsn=product_hsn_instance, cess=cess, created_by=user)


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


def can_approve_product_tax(view_func):
    """
        Decorator to validate the user can approve Product TAX
    """

    @wraps(view_func)
    def _wrapped_view_func(self, request, *args, **kwargs):
        user = request.user
        if not user.has_perm('product.can_approve_product_tax'):
            return get_response("Logged In user does not have required permission to perform this action.")
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view_func
