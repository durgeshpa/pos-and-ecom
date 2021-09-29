import codecs
import csv
import datetime
import io
import logging
import math

from django.db import transaction
from django.db.models import Q

from brand.common_function import BrandCls
from brand.models import Brand
from categories.common_function import CategoryCls
from categories.models import Category
from products.common_function import ParentProductCls, ProductCls
from products.models import Product, ParentProduct, ParentProductTaxMapping, ProductHSN, ParentProductCategory, Tax, \
    DestinationRepackagingCostMapping, ProductSourceMapping, ProductPackingMapping, ProductVendorMapping, \
    SlabProductPrice, PriceSlab, DiscountedProductPrice, ProductPrice
from products.utils import get_selling_price
from retailer_backend.utils import getStrToDate, getStrToYearDate
from global_config.views import get_config
from shops.models import Shop
from wms.models import BinInventory, In

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


def get_ptr_type_text(ptr_type=None):
    if ptr_type is not None and ptr_type in ParentProduct.PTR_TYPE_CHOICES:
        return ParentProduct.PTR_TYPE_CHOICES[ptr_type]
    return ''


class SetMasterData(object):
    """
    It will call the functions mentioned in UploadMasterData class as per the condition of header_list
    """

    @classmethod
    def set_master_data(cls, excel_file_data_list):
        UploadMasterData.set_inactive_status(excel_file_data_list)
        UploadMasterData.set_parent_data(excel_file_data_list)
        UploadMasterData.set_child_parent(excel_file_data_list)
        UploadMasterData.set_sub_brand_and_brand(excel_file_data_list)
        UploadMasterData.set_sub_category_and_category(excel_file_data_list)
        UploadMasterData.set_child_data(excel_file_data_list)


class UploadMasterData(object):
    """
    This function will be used for following operations:
    a)Set the Status to "Deactivated" for a Product
    b)Mapping of "Sub Brand" to "Brand"
    c)Mapping of "Sub Category" to "Category"
    d)Set the data for "Parent SKU"
    e)Mapping of Child SKU to Parent SKU
    f)Set the Child SKU Data
    """

    @classmethod
    def set_inactive_status(cls, csv_file_data_list, user):
        try:
            count = 0
            info_logger.info("Method Start to set Inactive status from excel file")
            child_product = Product.objects.all()
            for row in csv_file_data_list:
                if row['status'] == 'deactivated':
                    count += 1
                    product = child_product.filter(product_sku=row['sku_id'])
                    if 'mrp' in row.keys() and not row['mrp'] == '':
                        product.update(status='deactivated', product_mrp=row['mrp'], updated_by=user)
                    else:
                        product.update(status='deactivated', updated_by=user)
                else:
                    continue
            info_logger.info("Set Inactive Status function called -> Inactive row id count :" + str(count))
            info_logger.info("Method Complete to set the Inactive status from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Inactive Status Functionality' + {str(e)}")

    @classmethod
    def set_sub_brand_and_brand(cls, csv_file_data_list, user):
        """
            Updating Brand & Sub Brand
        """
        try:
            count = 0
            row_num = 1
            sub_brand = []
            info_logger.info('Method Start to set the Sub-brand to Brand mapping from excel file')
            brand = Brand.objects.all()
            for row in csv_file_data_list:
                count += 1
                row_num += 1
                try:
                    if 'sub_brand_id' in row.keys() and not row['sub_brand_id'] == '':
                        if row['sub_brand_id'] == row['brand_id']:
                            continue
                        else:
                            brand.filter(id=row['sub_brand_id']).update(brand_parent=row['brand_id'], updated_by=user)
                except:
                    sub_brand.append(str(row_num))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Sub brand is not updated in these row :" + str(sub_brand))
            info_logger.info("Method complete to set the Sub-Brand to Brand mapping from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with 'Set Sub Brand and Brand Functionality'"
                              f" + {str(e)}")

    @classmethod
    def set_sub_category_and_category(cls, csv_file_data_list, user):
        try:
            count = 0
            row_num = 1
            sub_category = []
            info_logger.info("Method Start to set the Sub-Category to Category mapping from excel file")
            category = Category.objects.all()
            for row in csv_file_data_list:
                count += 1
                row_num += 1
                try:
                    if 'sub_category_id' in row.keys() and not row['sub_category_id'] == '':
                        if row['sub_category_id'] == row['category_id']:
                            continue
                        else:
                            category.filter(id=row['sub_category_id']).update(category_parent=row['category_id'],
                                                                              updated_by=user)
                except:
                    sub_category.append(str(row_num))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Sub Category is not updated in these row :" + str(sub_category))
            info_logger.info("Method Complete to set the Sub-Category to Category mapping from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Sub Category and Category Functionality' + {str(e)}")

    @classmethod
    def set_child_data(cls, csv_file_data_list, user):
        try:
            info_logger.info("Method Start to set the Child data from excel file")
            count = 0
            row_num = 1
            child_data = []
            product = Product.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                count += 1
                try:
                    child_product = product.filter(product_sku=row['sku_id'])
                    child_product.update(product_name=row['sku_name'], status=row['status'], updated_by=user)
                    fields = ['ean', 'mrp', 'weight_unit', 'weight_value']
                    available_fields = []
                    for col in fields:
                        if col in row.keys() and row[col] != '':
                            available_fields.append(col)

                    for col in available_fields:
                        if col == 'ean':
                            child_product.update(product_ean_code=row['ean'])
                        if col == 'mrp':
                            child_product.update(product_mrp=row['mrp'])
                        if col == 'weight_value':
                            child_product.update(weight_value=row['weight_value'])

                    if 'repackaging_type' in row.keys() and row['repackaging_type'] == 'destination':
                        DestinationRepackagingCostMapping.objects.filter(destination=child_product[0].id) \
                            .update(raw_material=row['raw_material'],
                                    wastage=row['wastage'],
                                    fumigation=row['fumigation'],
                                    label_printing=row['label_printing'],
                                    packing_labour=row['packing_labour'],
                                    primary_pm_cost=row['primary_pm_cost'],
                                    secondary_pm_cost=row['secondary_pm_cost'],
                                    final_fg_cost=row['final_fg_cost'],
                                    conversion_cost=row['conversion_cost'])
                except Exception as e:
                    child_data.append(str(row_num) + ' ' + str(e))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info(
                "Some error found in these row while working with Child data Functionality:" + str(child_data))
            info_logger.info("Script Complete to set the Child data")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Child Data Functionality' + {str(e)}")

    @classmethod
    def set_product_tax(cls, csv_file_data_list, user):
        """
            Updating Parent Product & Tax
        """
        try:
            info_logger.info('Method Start to update the Parent Product with Tax')
            for row in csv_file_data_list:
                parent_pro_id = ParentProduct.objects.filter(parent_id=row['parent_id'].strip()).last()
                queryset = ParentProductTaxMapping.objects.filter(parent_product=parent_pro_id)
                if queryset.exists():
                    gst_tax = Tax.objects.get(tax_type='gst', tax_percentage=float(row['gst']))
                    queryset.filter(tax__tax_type='gst').update(tax=gst_tax)
                    if row['cess']:
                        cess_tax = Tax.objects.get(tax_type='cess', tax_percentage=float(row['cess']))
                        product_cess_tax = queryset.filter(tax__tax_type='cess')
                        if product_cess_tax.exists():
                            queryset.filter(tax__tax_type='cess').update(tax_id=cess_tax)
                        else:
                            ParentProductTaxMapping.objects.create(parent_product=parent_pro_id, tax=cess_tax)
                    if row['surcharge']:
                        surcharge_tax = Tax.objects.get(tax_type='surcharge', tax_percentage=float(row['surcharge']))
                        product_surcharge_tax = queryset.filter(tax__tax_type='surcharge')
                        if product_surcharge_tax.exists():
                            queryset.filter(tax__tax_type='surcharge').update(tax_id=surcharge_tax)
                        else:
                            ParentProductTaxMapping.objects.create(parent_product=parent_pro_id, tax=surcharge_tax)

            info_logger.info("Method complete to update the Parent Product with Tax from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with update Parent Product with Tax Functionality'"
                              f" + {str(e)}")

    @classmethod
    def update_parent_data(cls, csv_file_data_list, user):
        try:
            count = 0
            row_num = 1
            parent_data = []
            info_logger.info("Method Start to set the data for Parent SKU")
            parent_pro = ParentProduct.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                count += 1
                try:
                    parent_product = parent_pro.filter(parent_id=str(row['parent_id']).strip())

                    fields = ['product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)', 'status', 'tax_3(surcharge)',
                              'brand_case_size', 'inner_case_size', 'brand_id', 'sub_brand_id', 'category_id',
                              'is_ptr_applicable', 'ptr_type', 'brand_case_size', 'ptr_percent', 'is_ars_applicable',
                              'max_inventory_in_days', 'is_lead_time_applicable', 'discounted_life_percent']

                    available_fields = []
                    for col in fields:
                        if col in row.keys():
                            if row[col] != '':
                                available_fields.append(col)

                    for col in available_fields:

                        if col == 'product_type':
                            parent_product.update(product_type=str(row['product_type'].lower()))

                        if col == 'status':
                            parent_product.update(status=True if str(row['status'].lower()) == 'active' else False)

                        if col == 'hsn':
                            parent_product.update(
                                product_hsn=ProductHSN.objects.filter(product_hsn_code=str(row['hsn'])).last())

                        if col == 'tax_1(gst)':
                            tax = Tax.objects.filter(tax_name=row['tax_1(gst)'])
                            ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id,
                                                                   tax__tax_type='gst').update(tax=tax[0])

                        if col == 'tax_2(cess)':
                            tax = Tax.objects.filter(tax_name=row['tax_2(cess)'])
                            ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id,
                                                                   tax__tax_type='cess').update(tax=tax[0])
                        if col == 'tax_3(surcharge)':
                            tax = Tax.objects.filter(tax_name=row['tax_3(surcharge)'])
                            ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id,
                                                                   tax__tax_type='surcharge').update(tax=tax[0])

                        if col == 'inner_case_size':
                            parent_product.update(inner_case_size=int(row['inner_case_size']))

                        if col == 'brand_case_size':
                            parent_product.update(brand_case_size=int(row['brand_case_size']))

                        if col == 'brand_id':
                            parent_product.update(parent_brand=Brand.objects.filter(id=row['brand_id']).last())

                        if col == 'is_ptr_applicable':
                            parent_product.update(
                                is_ptr_applicable=True if str(row['is_ptr_applicable']).lower() == 'yes' else False)

                        if col == 'ptr_type':
                            parent_product.update(ptr_type=None if not str(
                                row['is_ptr_applicable']).lower() == 'yes' else ParentProduct.PTR_TYPE_CHOICES.MARK_UP
                            if row['ptr_type'].lower() == 'mark up' else ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN)

                        if col == 'ptr_percent':
                            parent_product.update(
                                ptr_percent=None if not row['is_ptr_applicable'].lower() == 'yes' else row[
                                    'ptr_percent'])

                        if col == 'is_ars_applicable':
                            parent_product.update(
                                is_ars_applicable=True if row['is_ars_applicable'].lower() == 'yes' else False)

                        if col == 'discounted_life_percent':
                            parent_product.update(
                                discounted_life_percent=float(row['discounted_life_percent']) if not
                                row['discounted_life_percent'] is None else 0.0)

                        if col == 'max_inventory_in_days':
                            parent_product.update(max_inventory=int(row['max_inventory_in_days']))

                        if col == 'is_lead_time_applicable':
                            parent_product.update(is_lead_time_applicable=True if row[
                                                                                      'is_lead_time_applicable'].lower() == 'yes' else False)
                        if col == 'discounted_life_percent':
                            parent_product.update(discounted_life_percent=row['discounted_life_percent'])
                        parent_product.update(updated_by=user)
                        ParentProductCls.create_parent_product_log(parent_product.last(), "updated")

                except Exception as e:
                    parent_data.append(str(row_num) + ' ' + str(e))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info(
                "Some Error Found in these rows, while working with Parent Data Functionality :" + str(parent_data))
            info_logger.info("Method Complete to set the data for Parent SKU")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with 'Set Parent Data Functionality' + {str(e)}")

    @classmethod
    def update_child_data(cls, csv_file_data_list, user):
        try:
            info_logger.info("Method Start to Update the Child to Parent mapping from excel file")
            count = 0
            row_num = 1
            set_child = []
            child_product = Product.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                count += 1
                try:
                    child_pro = child_product.filter(product_sku=row['sku_id'])
                    source_pro = ProductSourceMapping.objects.filter(destination_sku=child_pro.last())

                    fields = ['sku_id', 'sku_name', 'ean', 'mrp', 'weight_unit', 'weight_value', 'parent_id',
                              'status', 'repackaging_type', 'source_sku_id', 'status', 'product_special_cess',
                              'raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour',
                              'primary_pm_cost', 'secondary_pm_cost', "packing_sku_id", "packing_material_weight"]

                    available_fields = []
                    for col in fields:
                        if col in row.keys():
                            if row[col] != '':
                                available_fields.append(col)
                    child_obj = {'updated_by': user}
                    dest_obj = {}
                    pack_obj = {}

                    if 'ean' in row and row['ean']:
                        child_obj['product_ean_code'] = row['ean']

                    if 'sku_name' in row and row['sku_name']:
                        child_obj['product_name'] = row['sku_name']

                    if 'parent_id' in row and row['parent_id']:
                        child_obj['parent_product'] = ParentProduct.objects.filter(
                                parent_id=str(row['parent_id']).strip()).last()

                    if 'status' in row and row['status']:
                        child_obj['status'] = str(row['status'].lower())

                    if 'mrp' in row and row['mrp']:
                        child_obj['product_mrp'] = float(row['mrp'])

                    if 'weight_unit' in row and row['weight_unit']:
                        child_obj['weight_unit'] = row['weight_unit']

                    if 'weight_value' in row and row['weight_value']:
                        child_obj['weight_value'] = float(row['weight_value'])

                    if 'product_special_cess' in row and row['product_special_cess']:
                        child_obj['product_special_cess'] = float(row['product_special_cess']) if row[
                            'product_special_cess'] else None

                    if 'repackaging_type' in row and row['repackaging_type']:
                        child_obj['repackaging_type'] = row['repackaging_type']

                        if row['repackaging_type'] == 'destination':
                            if 'raw_material' in row and row['raw_material']:
                                dest_obj['raw_material'] = float(row['raw_material'])

                            if 'wastage' in row and row['wastage']:
                                dest_obj['wastage'] = float(row['wastage'])

                            if 'fumigation' in row and row['fumigation']:
                                dest_obj['fumigation'] = float(row['fumigation'])

                            if 'label_printing' in row and row['label_printing']:
                                dest_obj['label_printing'] = float(row['label_printing'])

                            if 'packing_labour' in row and row['packing_labour']:
                                dest_obj['packing_labour'] = float(row['packing_labour'])

                            if 'primary_pm_cost' in row and row['primary_pm_cost']:
                                dest_obj['primary_pm_cost'] = float(row['primary_pm_cost'])

                            if 'secondary_pm_cost' in row and row['secondary_pm_cost']:
                                dest_obj['secondary_pm_cost'] = float(row['secondary_pm_cost'])

                            if 'packing_sku_id' in row and row['packing_sku_id']:
                                pack_obj['packing_sku'] = Product.objects.filter(
                                    product_sku=row['packing_sku_id'].strip()).last()

                            if 'packing_material_weight' in row and row['packing_material_weight']:
                                pack_obj['packing_sku_weight_per_unit_sku'] = float(row['packing_material_weight'])

                            if 'source_sku_id' in row and row['source_sku_id']:
                                if source_pro.exists():
                                    source_pro.delete()

                                source_map = []
                                for product_skus in row['source_sku_id'].split(','):
                                    pro = product_skus.strip()
                                    if pro is not '' and pro not in source_map and \
                                            child_product.filter(product_sku=pro, repackaging_type='source').exists():
                                        source_map.append(pro)

                                for sku in source_map:
                                    pro_sku = child_product.filter(product_sku=sku, repackaging_type='source').last()
                                    ProductSourceMapping.objects.create(destination_sku=child_pro.last(),
                                                                        source_sku=Product.objects.get(id=pro_sku.id))

                            DestinationRepackagingCostMapping.objects.update_or_create(destination=child_pro.last(),
                                                                                       defaults=dest_obj)
                            ProductPackingMapping.objects.update_or_create(sku=child_pro.last(), defaults=pack_obj)

                        child_pro.update(**child_obj)
                        if 'repackaging_type' in row and row['repackaging_type']:
                            if row['repackaging_type'] == 'packing_material':
                                ProductCls.update_weight_inventory(child_pro.last())

                    ProductCls.create_child_product_log(child_pro.last(), "updated")

                except Exception as e:
                    set_child.append(str(row_num))

            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Child SKU is not exist in these row :" + str(set_child))
            info_logger.info("Method complete to set the Child to Parent mapping from excel file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with 'Set Child Parent Functionality' + {str(e)}")

    @classmethod
    def update_category_data(cls, csv_file_data_list, user):
        try:
            info_logger.info("Method Start to update category data from csv file")
            count = 0
            row_num = 1
            cat_data = []
            categories = Category.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                count += 1
                try:
                    category = categories.filter(id=row['category_id'])
                    fields = ["name", "category_slug", "category_desc", "category_sku_part",
                              "parent_category_id", "status"]

                    available_fields = []
                    for col in fields:
                        if col in row.keys() and row[col] != '':
                            available_fields.append(col)

                    for col in available_fields:
                        if col == 'name':
                            category.update(category_name=row['name'])
                        if col == 'category_slug':
                            category.update(category_slug=row['category_slug'])
                        if col == 'category_desc':
                            category.update(category_desc=row['category_desc'])
                        if col == 'category_sku_part':
                            category.update(category_sku_part=row['category_sku_part'])
                        if col == 'status':
                            category.update(status=True if str(row['status'].lower()) == 'active' else False)
                        if col == 'parent_category_id':
                            category.update(
                                category_parent=Category.objects.filter(id=int(row['parent_category_id'])).last())

                        category.update(updated_by=user)
                        CategoryCls.create_category_log(category.last(), "updated")

                except Exception as e:
                    cat_data.append(str(row_num) + ' ' + str(e))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info(
                "Some error found in these row while working with category update Functionality:" + str(cat_data))
            info_logger.info("Script Complete to update category data")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Category Update Functionality' + {str(e)}")

    @classmethod
    def update_brand_data(cls, csv_file_data_list, user):
        try:
            info_logger.info("Method Start to update brand data from csv file")
            count = 0
            row_num = 1
            brand_data = []
            brands = Brand.objects.all()
            for row in csv_file_data_list:
                row_num += 1
                count += 1
                try:
                    brand = brands.filter(id=row['brand_id'])
                    fields = ["name", "brand_slug", "brand_description", "brand_code",
                              "brand_parent_id", "status"]

                    available_fields = []
                    for col in fields:
                        if col in row.keys() and row[col] != '':
                            available_fields.append(col)

                    for col in available_fields:
                        if col == 'name':
                            brand.update(brand_name=row['name'])
                        if col == 'brand_slug':
                            brand.update(brand_slug=row['brand_slug'])
                        if col == 'brand_description':
                            brand.update(brand_description=row['brand_description'])
                        if col == 'brand_code':
                            brand.update(brand_code=row['brand_code'])
                        if col == 'status':
                            brand.update(status=True if str(row['status'].lower()) == 'active' else False)
                        if col == 'brand_parent_id':
                            brand.update(brand_parent=Brand.objects.filter(id=int(row['brand_parent_id'])).last())

                        brand.update(updated_by=user)
                    BrandCls.create_brand_log(brand.last(), "updated")

                except Exception as e:
                    brand_data.append(str(row_num) + ' ' + str(e))
            info_logger.info("Total row executed :" + str(count))
            info_logger.info(
                "Some error found in these row while working with category update Functionality:" + str(brand_data))
            info_logger.info("Script Complete to update category data")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with 'Category Update Functionality' + {str(e)}")

    @classmethod
    def create_bulk_parent_product(cls, csv_file_data_list, user):
        """
            Create Parent Product
        """
        try:
            info_logger.info('Method Start to create Parent Product')
            for row in csv_file_data_list:
                parent_product = ParentProduct.objects.create(
                    name=row['product_name'].strip(),
                    parent_brand=Brand.objects.filter(id=int(row['brand_id'])).last(),
                    product_hsn=ProductHSN.objects.filter(product_hsn_code=row['hsn'].replace("'", '')).last(),
                    inner_case_size=int(row['inner_case_size']), product_type=row['product_type'],
                    is_ptr_applicable=(True if row['is_ptr_applicable'].lower() == 'yes' else False),
                    ptr_type=(None if not row['is_ptr_applicable'].lower() == 'yes' else ParentProduct.PTR_TYPE_CHOICES.MARK_UP
                    if row['ptr_type'].lower() == 'mark up' else ParentProduct.PTR_TYPE_CHOICES.MARK_DOWN),
                    ptr_percent=(None if not row['is_ptr_applicable'].lower() == 'yes' else row['ptr_percent']),
                    discounted_life_percent=(0.0 if not row['discounted_life_percent'] else
                                             float(row['discounted_life_percent'])),
                    is_ars_applicable=True if row['is_ars_applicable'].lower() == 'yes' else False,
                    max_inventory=int(row['max_inventory_in_days']),
                    brand_case_size=int(row['brand_case_size']),
                    status=True if str(row['status'].lower()) == 'active' else False,
                    is_lead_time_applicable=(True if row['is_lead_time_applicable'].lower() == 'yes' else False),
                    created_by=user
                )
                ParentProductCls.create_parent_product_log(parent_product, "created")
                parent_gst = int(row['gst'])
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='gst', tax_percentage=parent_gst).last())

                parent_cess = int(row['cess']) if row['cess'] else 0
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='cess', tax_percentage=parent_cess).last())

                parent_surcharge = float(row['surcharge']) if row['surcharge'] else 0
                if Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).exists():
                    ParentProductTaxMapping.objects.create(
                        parent_product=parent_product,
                        tax=Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).last())
                else:
                    new_surcharge_tax = Tax.objects.create(tax_name='Surcharge - {}'.format(parent_surcharge),
                                                           tax_type='surcharge',
                                                           tax_percentage=parent_surcharge,
                                                           tax_start_at=datetime.datetime.now())

                    ParentProductTaxMapping.objects.create(parent_product=parent_product, tax=new_surcharge_tax)

                if Category.objects.filter(category_name=row['category_name'].strip()).exists():
                    ParentProductCategory.objects.create(
                        parent_product=parent_product,
                        category=Category.objects.filter(category_name=row['category_name'].strip()).last())

                else:
                    categories = row['category_name'].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        ParentProductCategory.objects.create(parent_product=parent_product,
                                                             category=Category.objects.filter(
                                                                 category_name=cat).last())

            info_logger.info("Method complete to create the Parent Product from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with create Parent Product "
                              f" + {str(e)}")

    @classmethod
    def create_bulk_child_product(cls, csv_file_data_list, user):
        """
            Create Child Product
        """
        try:
            info_logger.info('Method Start to create Child Product')
            for row in csv_file_data_list:
                child_product = Product.objects.create(
                    parent_product=ParentProduct.objects.filter(parent_id=row['parent_id'].strip()).last(),
                    reason_for_child_sku=(row['reason_for_child_sku'].lower()), product_name=row['product_name'],
                    product_ean_code=row['ean'].replace("'", ''), product_mrp=float(row['mrp']),
                    weight_value=float(row['weight_value']), weight_unit=str(row['weight_unit'].lower()),
                    repackaging_type=row['repackaging_type'], created_by=user,
                    status='pending_approval' if row['status'].lower() is None else row['status'].lower(),
                    product_special_cess=(
                        None if str(row['product_special_cess']).strip() == '' else float(row['product_special_cess'])))

                ProductCls.create_child_product_log(child_product, "created")

                if row['repackaging_type'] == 'packing_material':
                    ProductCls.update_weight_inventory(child_product)

                if row['repackaging_type'] == 'destination':
                    source_map = []
                    for product_skus in row['source_sku_id'].split(','):
                        pro = product_skus.strip()
                        if pro is not '' and pro not in source_map and \
                                Product.objects.filter(product_sku=pro, repackaging_type='source').exists():
                            source_map.append(pro)
                    for sku in source_map:
                        pro_sku = Product.objects.filter(product_sku=sku, repackaging_type='source').last()
                        ProductSourceMapping.objects.create(destination_sku=child_product, source_sku=pro_sku,
                                                            status=True)
                    DestinationRepackagingCostMapping.objects.create(destination=child_product,
                                                                     raw_material=float(row['raw_material']),
                                                                     wastage=float(row['wastage']),
                                                                     fumigation=float(row['fumigation']),
                                                                     label_printing=float(row['label_printing']),
                                                                     packing_labour=float(row['packing_labour']),
                                                                     primary_pm_cost=float(row['primary_pm_cost']),
                                                                     secondary_pm_cost=float(row['secondary_pm_cost']))

                    ProductPackingMapping.objects.create(sku=child_product, packing_sku=Product.objects.get(
                        product_sku=row['packing_sku_id']), packing_sku_weight_per_unit_sku=float(
                        row['packing_material_weight']))

            info_logger.info("Method complete to create the Child Product from csv file")
        except Exception as e:
            import traceback;
            print(traceback.print_exc())
            error_logger.info(f"Something went wrong, while working with create Child Product "
                              f" + {str(e)}")

    @classmethod
    def create_bulk_category(cls, csv_file_data_list, user):
        """
            Create Category
        """
        try:
            info_logger.info('Method Start to create Category')
            for row in csv_file_data_list:
                cat_obj = Category.objects.create(
                    category_name=row['name'],
                    category_slug=row['category_slug'],
                    category_parent=Category.objects.filter(id=int(row['parent_category_id'])).last()
                    if row['parent_category_id'] else None,
                    category_desc=row['category_desc'],
                    category_sku_part=row['category_sku_part'],
                    status=True if str(row['status'].lower()) == 'active' else False,
                    created_by=user)
                CategoryCls.create_category_log(cat_obj, "created")

            info_logger.info("Method complete to create Category from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with create Category "
                              f" + {str(e)}")

    @classmethod
    def create_bulk_brand(cls, csv_file_data_list, user):
        """
            Create Brand
        """
        try:
            info_logger.info('Method Start to create Brand')

            for row in csv_file_data_list:
                brand_obj = Brand.objects.create(
                    brand_name=row['name'],
                    brand_slug=row['brand_slug'],
                    brand_parent=Brand.objects.filter(id=int(row['brand_parent_id'])).last() if row['brand_parent_id'] else None,
                    brand_description=row['brand_description'],
                    brand_code=row['brand_code'],
                    status=True if str(row['status'].lower()) == 'active' else False,
                    created_by=user)
                BrandCls.create_brand_log(brand_obj, "created")

            info_logger.info("Method complete to create Brand from csv file")
        except Exception as e:
            error_logger.info(f"Something went wrong, while working with create Brand "
                              f" + {str(e)}")


class DownloadMasterData(object):
    """
   brand.update(brand_parent=Brand.objects.filter(id=int(row['brand_parent_id'])).last())     This function will be used for following operations:
        a)return an Sample File in xlsx format which can be used for uploading the master_data
        b)return an Sample File in xlsx format which can be used for Status to "Deactivated" for a Product
        c)return an Sample File in xlsx format which can be used for Mapping of "Sub Brand" to "Brand"
        d)return an Sample File in xlsx format which can be used for Mapping of "Sub Category" to "Category"
        e)return an Sample File in xlsx format which can be used for Set the data for "Parent SKU"
        f)return an Sample File in xlsx format which can be used for Mapping of Child SKU to Parent SKU
        g)return an Sample File in xlsx format which can be used for Set the Child SKU Data
        """

    def response_workbook(filename):

        csv_file_buffer = io.StringIO()
        writer = csv.writer(csv_file_buffer, dialect='excel', delimiter=',')
        return csv_file_buffer, writer

    @classmethod
    def set_inactive_status_sample_file(cls, validated_data):

        response, writer = DownloadMasterData.response_workbook("active_inactive_status_sample")
        columns = ['sku_id', 'sku_name', 'mrp', 'status', ]
        writer.writerow(columns)

        products = Product.objects.values('product_sku', 'product_name', 'product_mrp', 'status', ). \
            filter(Q(parent_product__parent_product_pro_category__category__category_name__icontains=
                     validated_data['category_id'].category_name))

        for product in products:
            row = []
            row.append(product['product_sku'])
            row.append(product['product_name'])
            row.append(product['product_mrp'])
            row.append(product['status'])

            writer.writerow(row)

        info_logger.info("Set Inactive Status Sample File has been Successfully Downloaded")
        response.seek(0)
        return response

    @classmethod
    def set_brand_sub_brand_mapping_sample_file(cls):
        response, writer = DownloadMasterData.response_workbook("brand_sub_brand_mapping_sample_file")
        columns = ['brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name', ]
        writer.writerow(columns)

        brands = Brand.objects.values('id', 'brand_name', 'brand_parent_id', 'brand_parent__brand_name')
        for brand in brands:
            row = []
            if brand['brand_parent_id']:
                row.append(brand['brand_parent_id'])
                row.append(brand['brand_parent__brand_name'])
                row.append(brand['id'])
                row.append(brand['brand_name'])

            else:
                row.append(brand['id'])
                row.append(brand['brand_name'])
                row.append(brand['brand_parent_id'])
                row.append(brand['brand_parent__brand_name'])

            writer.writerow(row)

        info_logger.info("Brand and Sub Brand Mapping Sample File has been Successfully Downloaded")
        response.seek(0)
        return response

    @classmethod
    def set_category_sub_category_mapping_sample_file(cls):

        response, writer = DownloadMasterData.response_workbook("sub_category_and_category_mapping_sample_file")
        columns = ['category_id', 'category_name', 'sub_category_id', 'sub_category_name', ]
        writer.writerow(columns)

        categories = Category.objects.values('id', 'category_name', 'category_parent_id',
                                             'category_parent__category_name')
        for category in categories:
            row = []
            if category['category_parent_id']:
                row.append(category['category_parent_id'])
                row.append(category['category_parent__category_name'])
                row.append(category['id'])
                row.append(category['category_name'])
            else:
                row.append(category['id'])
                row.append(category['category_name'])
                row.append(category['category_parent_id'])
                row.append(category['category_parent__category_name'])

            writer.writerow(row)
        info_logger.info("Category and Sub Category Mapping Sample File has been Successfully Downloaded")
        response.seek(0)
        return response

    @classmethod
    def set_product_tax_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("bulk_product_tax_gst_update_sample")
        columns = ['parent_id', 'gst', 'cess', 'surcharge', ]
        writer.writerow(columns)

        writer.writerow(['PHEATOY0006', 2, 12, 4])

        info_logger.info("bulk tax update Sample CSVExported successfully ")
        response.seek(0)
        return response,

    @classmethod
    def update_child_with_parent_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("child_parent_mapping_data_sample")
        columns = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'status', ]
        writer.writerow(columns)

        products = Product.objects.values('product_sku', 'product_name', 'parent_product__parent_id',
                                          'parent_product__name', 'status') \
            .filter(Q(parent_product__parent_product_pro_category__category__category_name__icontains=validated_data[
            'category_id'].category_name))

        for product in products:
            row = []
            row.append(product['product_sku'])
            row.append(product['product_name'])
            row.append(product['parent_product__parent_id'])
            row.append(product['parent_product__name'])
            row.append(product['status'])

            writer.writerow(row)

        info_logger.info("Child Parent Mapping Sample File has been Successfully Downloaded")
        response.seek(0)
        return response

    # create bulk sample file
    @classmethod
    def create_parent_product_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("bulk_parent_product_create_sample")

        columns = ["product_name", "brand_id", "brand_name", "category_name", "hsn", "gst", "cess", "surcharge",
                   "inner_case_size", "brand_case_size", "product_type", "is_ptr_applicable", "ptr_type", "ptr_percent",
                   "is_ars_applicable", "discounted_life_percent", "max_inventory_in_days", "is_lead_time_applicable",
                   "status"]
        writer.writerow(columns)
        data = [["parent1", "2", "Too Yumm", "Health Care, Beverages, Grocery & Staples", "123456", "18", "12", "100",
                 "10", "2", "b2b", "yes", "Mark Up", "12", "yes", "2", "2", "yes", "deactivated"],
                ["parent2", "2", "Too Yumm", "Health Care, Beverages", "123456", "18", "12", "100",
                 "10", "2", "b2b", "yes", "Mark Up", "12", "yes", "0.0", "2", "yes", "active"]]

        for row in data:
            writer.writerow(row)

        info_logger.info("Parent Product Sample CSVExported successfully ")
        response.seek(0)
        return response

    @classmethod
    def create_child_product_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("bulk_child_product_create_sample")
        writer = csv.writer(response)

        writer.writerow(
            ["product_name", "reason_for_child_sku", "parent_id", "ean", "mrp", "weight_value", "weight_unit",
             "repackaging_type", "product_special_cess", 'status', "source_sku_id", 'raw_material', 'wastage',
             'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost', 'secondary_pm_cost', "packing_sku_id",
             "packing_material_weight"])
        data = [["TestChild1", "Default", "PHEAMGI0001", "abcdefgh", "50", "20", "gm", "none", " ", "pending_approval"],
                ["TestChild2", "Default", "PHEAMGI0001", "abcdefgh", "50", "20", "gm", "source", " ",
                 "pending_approval"],
                ["TestChild3", "Default", "PHEAMGI0001", "abcdefgh", "50", "20", "gm", "destination", " ",
                 "deactivated",
                 "SNGSNGGMF00000016, SNGSNGGMF00000016", "10.22", "2.33", "7", "4.33", "5.33", "10.22", "5.22",
                 "BPOBLKREG00000001", "10.00"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Child Product Sample CSVExported successfully ")
        response.seek(0)
        return response

    @classmethod
    def create_brand_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("bulk_brand_create_sample")
        columns = ["name", "brand_slug", "brand_parent", "brand_parent_id", "brand_description",
                   "brand_code", "status"]
        writer.writerow(columns)

        data = [["NatureLand", "natureland", "Dermanest", "1", "ABC", "NAT", "active"],
                ["Top", "top", "Dermanest", "1", "ABC", "NST", "deactivated"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Brand Sample CSVExported successfully ")

        info_logger.info("bulk tax update Sample CSVExported successfully ")
        response.seek(0)
        return response

    @classmethod
    def create_category_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("bulk_category_create_sample")
        columns = ["name", "category_slug", "category_desc", "category_parent", "parent_category_id",
                   "category_sku_part", "status"]
        writer.writerow(columns)
        data = [["Home Improvement", "home_improvement", "XYZ", "Processed Food", "2", "HMI", "active"],
                ["Electronics", "electronics", "XYZ", "Processed Food", "2", "KGF", "deactivated"]]
        for row in data:
            writer.writerow(row)

        info_logger.info("Category Sample CSVExported successfully ")
        response.seek(0)
        return response

    # update bulk sample file
    @classmethod
    def update_child_product_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("child_data_sample")
        columns = ['sku_id', 'sku_name', 'parent_id', 'parent_name', 'ean', 'mrp', 'weight_unit', 'weight_value',
                   'status', 'product_special_cess', 'repackaging_type', 'category_name', 'source_sku_id',
                   'raw_material', 'wastage', 'fumigation', 'label_printing', 'packing_labour', 'primary_pm_cost',
                   'secondary_pm_cost', "packing_sku_id", "packing_material_weight"]

        writer.writerow(columns)
        sub_cat = Category.objects.filter(category_parent=validated_data['category_id'])
        products = Product.objects.values('id', 'product_sku', 'product_name', 'product_ean_code', 'product_mrp',
                                          'weight_unit', 'weight_value', 'status', 'repackaging_type',
                                          'parent_product__parent_id', 'parent_product__name', 'product_special_cess',
                                          'parent_product__parent_product_pro_category__category__category_name') \
            .filter(Q(parent_product__parent_product_pro_category__category=validated_data['category_id']) |
                    Q(parent_product__parent_product_pro_category__category__in=sub_cat)).distinct('id')

        for product in products:
            row = []
            row.append(product['product_sku'])
            row.append(product['product_name'])
            row.append(product['parent_product__parent_id'])
            row.append(product['parent_product__name'])
            row.append(product['product_ean_code'])
            row.append(product['product_mrp'])
            row.append(product['weight_unit'])
            row.append(product['weight_value'])
            row.append(product['status'])
            row.append(product['product_special_cess'])
            row.append(product['repackaging_type'])
            row.append(product['parent_product__parent_product_pro_category__category__category_name'])

            source_sku_obj = ProductSourceMapping.objects.filter(destination_sku=product['id'])
            source_sku_ids = []
            for source_skus in source_sku_obj:
                if source_skus.source_sku.product_sku not in source_sku_ids:
                    source_sku_ids.append(source_skus.source_sku.product_sku)

            if source_sku_ids:
                row.append(','.join(source_sku_ids))
            else:
                row.append('')

            costs = DestinationRepackagingCostMapping.objects.values('raw_material', 'wastage', 'fumigation',
                                                                     'label_printing', 'packing_labour',
                                                                     'primary_pm_cost', 'secondary_pm_cost',
                                                                     'final_fg_cost', 'conversion_cost').filter(
                destination=product['id'])

            for cost in costs:
                row.append(cost['raw_material'])
                row.append(cost['wastage'])
                row.append(cost['fumigation'])
                row.append(cost['label_printing'])
                row.append(cost['packing_labour'])
                row.append(cost['primary_pm_cost'])
                row.append(cost['secondary_pm_cost'])

            pro_packing = ProductPackingMapping.objects.values('packing_sku_id',
                                                               'packing_sku_weight_per_unit_sku').filter(
                sku=product['id'])
            for pro_pack in pro_packing:
                pro_sku = Product.objects.get(id=pro_pack['packing_sku_id'])
                row.append(pro_sku.product_sku)
                row.append(pro_pack['packing_sku_weight_per_unit_sku'])

            writer.writerow(row)

        info_logger.info("Child Data Sample File has been Successfully Downloaded")
        response.seek(0)
        return response

    @classmethod
    def update_parent_product_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("parent_data_sample")
        columns = ['parent_id', 'parent_name', 'product_type', 'hsn', 'tax_1(gst)', 'tax_2(cess)', 'tax_3(surcharge)',
                   'inner_case_size', 'brand_case_size', 'brand_id', 'brand_name', 'sub_brand_id', 'sub_brand_name',
                   'category_id', 'category_name', 'sub_category_id', 'sub_category_name', 'status',
                   'is_ptr_applicable', 'ptr_type', 'ptr_percent', 'is_ars_applicable', 'max_inventory_in_days',
                   'is_lead_time_applicable', 'discounted_life_percent']
        writer.writerow(columns)

        sub_cat = Category.objects.filter(category_parent=validated_data['category_id'])

        parent_products = ParentProductCategory.objects.values('parent_product__id', 'parent_product__parent_id',
                                                               'parent_product__name', 'parent_product__product_type',
                                                               'parent_product__product_hsn__product_hsn_code',
                                                               'parent_product__inner_case_size',
                                                               'parent_product__brand_case_size',
                                                               'parent_product__parent_brand__id',
                                                               'parent_product__parent_brand__brand_name',
                                                               'parent_product__parent_brand__brand_parent_id',
                                                               'parent_product__parent_brand__brand_parent__brand_name',
                                                               'category__id', 'category__category_name',
                                                               'category__category_parent_id',
                                                               'category__category_parent__category_name',
                                                               'parent_product__status',
                                                               'parent_product__is_ptr_applicable',
                                                               'parent_product__ptr_type',
                                                               'parent_product__ptr_percent',
                                                               'parent_product__is_ars_applicable',
                                                               'parent_product__max_inventory',
                                                               'parent_product__is_lead_time_applicable',
                                                               'parent_product__discounted_life_percent',).filter(
            Q(category__in=sub_cat) | Q(category=validated_data['category_id'])).distinct('id')
        for product in parent_products:
            row = []
            tax_list = ['', '', '']
            row.append(product['parent_product__parent_id'])
            if product['parent_product__name'][0] == '#':
                row.append(product['parent_product__name'][1:])
            else:
                row.append(product['parent_product__name'])
            row.append(product['parent_product__product_type'])
            row.append(product['parent_product__product_hsn__product_hsn_code'])
            taxes = ParentProductTaxMapping.objects.select_related('tax').filter(
                parent_product=product['parent_product__id'])
            for tax in taxes:
                if tax.tax.tax_type == 'gst':
                    tax_list[0] = tax.tax.tax_name
                if tax.tax.tax_type == 'cess':
                    tax_list[1] = tax.tax.tax_name
                if tax.tax.tax_type == 'surcharge':
                    tax_list[2] = tax.tax.tax_name
            row.extend(tax_list)
            row.append(product['parent_product__inner_case_size'])
            row.append(product['parent_product__brand_case_size'])

            if product['parent_product__parent_brand__brand_parent_id']:
                row.append(product['parent_product__parent_brand__brand_parent_id'])
                row.append(product['parent_product__parent_brand__brand_parent__brand_name'])
                row.append(product['parent_product__parent_brand__id'])
                row.append(product['parent_product__parent_brand__brand_name'])
            else:
                row.append(product['parent_product__parent_brand__id'])
                row.append(product['parent_product__parent_brand__brand_name'])
                row.append(product['parent_product__parent_brand__brand_parent_id'])
                row.append(product['parent_product__parent_brand__brand_parent__brand_name'])

            if product['category__category_parent_id']:
                row.append(product['category__category_parent_id'])
                row.append(product['category__category_parent__category_name'])
                row.append(product['category__id'])
                row.append(product['category__category_name'])
            else:
                row.append(product['category__id'])
                row.append(product['category__category_name'])
                row.append(product['category__category_parent_id'])
                row.append(product['category__category_parent__category_name'])

            if product['parent_product__status']:
                row.append("active")
            else:
                row.append("deactivated")
            row.append('Yes' if product['parent_product__is_ptr_applicable'] else 'No')
            row.append(get_ptr_type_text(product['parent_product__ptr_type']))
            row.append(product['parent_product__ptr_percent'])
            row.append('Yes' if product['parent_product__is_ars_applicable'] else 'No')
            row.append(product['parent_product__max_inventory'])
            row.append('Yes' if product['parent_product__is_lead_time_applicable'] else 'No')
            row.append(product['parent_product__discounted_life_percent'])

            writer.writerow(row)
        info_logger.info("Parent Data Sample File has been Successfully Downloaded")
        response.seek(0)
        return response

    @classmethod
    def update_category_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("bulk_category_update_sample")
        columns = ["category_id", "name", "category_slug", "category_desc", "category_sku_part",
                   "parent_category_id", "parent_category_name", "status"]
        writer.writerow(columns)
        categories = Category.objects.values('id', 'category_name', 'category_slug', 'category_desc', 'status',
                                             'category_sku_part', 'category_parent', 'category_parent__category_name')

        for category in categories:
            row = [category['id'], category['category_name'], category['category_slug'], category['category_desc'],
                   category['category_sku_part'], category['category_parent'],
                   category['category_parent__category_name'],
                   'active' if category['status'] is True else 'deactivated']

            writer.writerow(row)
        info_logger.info("Update Category Sample File has been Successfully Downloaded")
        response.seek(0)
        return response

    @classmethod
    def update_brand_sample_file(cls, validated_data):
        response, writer = DownloadMasterData.response_workbook("bulk_brand_update_sample")
        columns = ["brand_id", "name", "brand_slug", "brand_description", "brand_code", "brand_parent_id",
                   "brand_parent", "status"]
        writer.writerow(columns)

        brands = Brand.objects.values('id', 'brand_name', 'brand_slug', 'brand_description', 'brand_code',
                                      'brand_parent_id', 'brand_parent__brand_name', 'status')
        for brand in brands:
            row = [brand['id'], brand['brand_name'], brand['brand_slug'], brand['brand_description'],
                   brand['brand_code'], brand['brand_parent_id'], brand['brand_parent__brand_name'],
                   'active' if brand['status'] is True else 'deactivated']

            writer.writerow(row)
        info_logger.info("Update Brand Sample CSVExported successfully ")
        response.seek(0)
        return response


def create_product_vendor_mapping_sample_file(validated_data, req_type):
    response, writer = DownloadMasterData.response_workbook("create_product_vendor_mapping_sample")
    columns = ['id', 'product_name', 'product_sku', 'brand_to_gram_price_unit', 'brand_to_gram_price', 'case_size']
    writer.writerow(columns)

    pro_vendor_map = ProductVendorMapping.objects.filter(vendor=validated_data['vendor_id'])
    products_vendors = pro_vendor_map.only('product', 'vendor', 'brand_to_gram_price_unit', 'product_price',
                                           'product_price_pack', 'case_size')
    if req_type == 0:
        for product_vendor in products_vendors:
            if product_vendor.status:
                if product_vendor.brand_to_gram_price_unit == "Per Piece":
                    writer.writerow([product_vendor.product.id, product_vendor.product.product_name,
                                     product_vendor.product.product_sku, product_vendor.brand_to_gram_price_unit,
                                     product_vendor.product_price, product_vendor.case_size])
                else:
                    writer.writerow([product_vendor.product.id, product_vendor.product.product_name,
                                     product_vendor.product.product_sku, product_vendor.brand_to_gram_price_unit,
                                     product_vendor.product_price_pack, product_vendor.case_size])
    else:
        if products_vendors:
            product_id = pro_vendor_map.values('product')
            products = Product.objects.filter(status="active").exclude(id__in=product_id).only('id', 'product_name',
                                                                                               'product_sku')
            for product in products:
                writer.writerow([product.id, product.product_name, product.product_sku, '', '',
                                 product.product_case_size])
        else:
            products = Product.objects.filter(status="active").only('id', 'product_name', 'product_sku', 'product_mrp')
            for product in products:
                writer.writerow([product.id, product.product_name, product.product_sku, '', '',
                                 product.product_case_size])
    info_logger.info("Create Product Vendor Mapping Sample CSVExported successfully ")
    response.seek(0)
    return response


def create_bulk_product_vendor_mapping(validated_data):
    reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
    next(reader)
    try:
        for row_id, row in enumerate(reader):
            if row[3].lower() == "per piece":
                product_vendor = ProductVendorMapping.objects.create(
                    vendor=validated_data['vendor_id'],
                    product=Product.objects.get(id=int(row[0])),
                    product_mrp=Product.objects.get(id=int(row[0])).product_mrp,
                    brand_to_gram_price_unit=row[3].title(),
                    product_price=row[4],
                    case_size=row[5],
                )
            else:
                product_vendor = ProductVendorMapping.objects.create(
                    vendor=validated_data['vendor_id'],
                    product=Product.objects.get(id=int(row[0])),
                    product_mrp=Product.objects.get(id=int(row[0])).product_mrp,
                    brand_to_gram_price_unit=row[3].title(),
                    product_price_pack=row[4],
                    case_size=row[5],
                )
            product_vendor.save()
    except Exception as e:
        error_logger.info(f"Something went wrong, while working with create Product Vendor Mapping "
                          f" + {str(e)}")


def create_bulk_product_slab_price(validated_data):
    reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
    next(reader)
    date_pattern = "%d-%m-%Y"
    try:
        for row_id, row in enumerate(reader):
            product = Product.objects.filter(product_sku=str(row[0]).strip()).last()
            seller_shop_id = Shop.objects.get(id=int(row[2]))

            # Create ProductPrice
            product_price = SlabProductPrice(product=product, mrp=product.product_mrp, seller_shop=seller_shop_id)
            product_price.save()

            # Get selling price applicable for first price slab
            if product.parent_product.is_ptr_applicable:
                selling_price = get_selling_price(product)
            else:
                selling_price = float(row[6])

            # Create Price Slab 1
            price_slab_1 = PriceSlab(product_price=product_price, start_value=0, end_value=int(row[5]),
                                     selling_price=selling_price)
            if row[7]:
                price_slab_1.offer_price = float(row[7])
                price_slab_1.offer_price_start_date = getStrToYearDate(row[8], date_pattern).strftime('%Y-%m-%d')
                price_slab_1.offer_price_end_date = getStrToYearDate(row[9], date_pattern).strftime('%Y-%m-%d')
            price_slab_1.save()

            # If slab 1 quantity is Zero then slab is not to be created
            if int(row[5]) == 0:
                continue
            # Create Price Slab 2
            price_slab_2 = PriceSlab(product_price=product_price, start_value=row[10], end_value=0,
                                     selling_price=float(row[11]))
            if row[12]:
                price_slab_2.offer_price = float(row[12])
                price_slab_2.offer_price_start_date = getStrToYearDate(row[13], date_pattern).strftime('%Y-%m-%d')
                price_slab_2.offer_price_end_date = getStrToYearDate(row[14], date_pattern).strftime('%Y-%m-%d')
            price_slab_2.save()
        #
        # return validated_data
    except Exception as e:
        msg = "Unable to create price for row {}".format(row_id + 1)
        error_logger.info(msg)
        return msg


def create_bulk_product_discounted_price(validated_data):
    reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
    next(reader)
    try:
        for row_id, row in enumerate(reader):
            with transaction.atomic():
                product = Product.objects.filter(product_sku=str(row[0]).strip()).last()
                seller_shop_id = int(row[2])
                seller_shop = Shop.objects.filter(pk=seller_shop_id).last()

                if not product.is_manual_price_update:
                    original_prod = product.product_ref
                    bin_inventory = BinInventory.objects.filter(sku=product,
                                                                inventory_type__inventory_type='normal',
                                                                quantity__gt=0).last()
                    latest_in = In.objects.filter(sku=bin_inventory.sku.product_ref,
                                                  batch_id=bin_inventory.batch_id).order_by('-modified_at')
                    expiry_date = latest_in[0].expiry_date
                    manufacturing_date = latest_in[0].manufacturing_date
                    product_life = expiry_date - manufacturing_date
                    remaining_life = expiry_date - datetime.date.today()
                    discounted_life = math.floor(
                        product_life.days * original_prod.parent_product.discounted_life_percent / 100)
                    product_price = original_prod.product_pro_price.filter(seller_shop=seller_shop,
                                                                           approval_status=ProductPrice.APPROVED).last()
                    base_price_slab = product_price.price_slabs.filter(end_value=0).last()
                    base_price = base_price_slab.ptr

                    half_life = (discounted_life - 2) / 2

                    if remaining_life.days <= half_life:
                        selling_price = round(
                            base_price * int(get_config('DISCOUNTED_HALF_LIFE_PRICE_PERCENT', 50)) / 100, 2)
                    else:
                        selling_price = round(
                            base_price * int(get_config('DISCOUNTED_PRICE_PERCENT', 75)) / 100, 2)

                else:
                    selling_price = float(row[4])

                # Create Product Price
                product_price = DiscountedProductPrice(product=product, mrp=product.product_mrp,
                                                       seller_shop_id=seller_shop_id,
                                                       selling_price=selling_price,
                                                       start_date=datetime.datetime.today(),
                                                       approval_status=ProductPrice.APPROVED)
                product_price.save()

                # Create Price for discounted Product
                discounted_product_price = PriceSlab(product_price=product_price, selling_price=selling_price,
                                                     start_value=0, end_value=0)
                discounted_product_price.save()

    except Exception as e:
        msg = "Unable to create price for row {}".format(row_id + 1)
        error_logger.info(msg)
        return msg

