import logging

from brand.models import Brand
from categories.models import Category
from products.models import Product, ParentProduct, ParentProductTaxMapping, ProductHSN, ParentProductCategory

logger = logging.getLogger(__name__)


class SetMasterData(object):

    @classmethod
    def set_master_data(cls, header_list, excel_file_data_list):
        UploadMasterData.set_inactive_status(header_list, excel_file_data_list)
        UploadMasterData.set_sub_brand_and_brand(header_list, excel_file_data_list)
        UploadMasterData.set_sub_category_and_category(header_list, excel_file_data_list)
        UploadMasterData.set_parent_data(header_list, excel_file_data_list)
        UploadMasterData.set_child_data(header_list, excel_file_data_list)
        UploadMasterData.set_child_parent(header_list, excel_file_data_list)


class UploadMasterData(object):

    @classmethod
    def set_inactive_status(cls, header_list, excel_file_data_list):

        count = 0
        logger.info("Method Start to set Inactive status from excel file")
        for row in excel_file_data_list:
            if row['status'] == 'Deactivated':
                count += 1
                Product.objects.filter(product_sku=row['sku_id']).update(status='deactivated')
            else:
                continue
        logger.info("Inactive row id count :" + str(count))
        logger.info("Method Complete to set the Inactive status from excel file")

    @classmethod
    def set_sub_brand_and_brand(cls, header_list, excel_file_data_list):
        count = 0
        row_num = 1
        sub_brand = []
        logger.info('Method Start to set the Sub-brand to Brand mapping from excel file')
        for row in excel_file_data_list:
            count += 1
            row_num += 1
            try:
                if row['sub_brand_id'] == row['brand_id']:
                    continue
                else:
                    Brand.objects.filter(id=row['sub_brand_id']).update(brand_parent=row['brand_id'])
            except:
                sub_brand.append(str(row_num))
        logger.info("Total row executed :" + str(count))
        logger.info("Sub brand is not updated in these row :" + str(sub_brand))
        logger.info("Method complete to set the Sub-Brand to Brand mapping from csv file")

    @classmethod
    def set_sub_category_and_category(cls, header_list, excel_file_data_list):
        count = 0
        row_num = 1
        sub_category = []
        logger.info("Method Start to set the Sub-Category to Category mapping from excel file")
        for row in excel_file_data_list:
            count += 1
            row_num += 1
            try:
                if row['sub_category_id'] == row['category_id']:
                    continue
                else:
                    Category.objects.filter(id=row['sub_category_id']).update(
                        category_parent=row['category_id'])
            except:
                sub_category.append(str(row_num))
        logger.info("Total row executed :" + str(count))
        logger.info("Sub Category is not updated in these row :" + str(sub_category))
        logger.info("Method Complete to set the Sub-Category to Category mapping from excel file")

    @classmethod
    def set_parent_data(cls, header_list, excel_file_data_list):
        count = 0
        row_num = 1
        parent_data = []
        parent_brand = []
        parent_hsn = []
        parent_category = []
        logger.info("Method Start to set the data for Parent SKU")
        for row in excel_file_data_list:
            row_num += 1
            if not row['status'] == 'Deactivated':
                count += 1
                try:
                    if 'parent_id' in header_list:
                        parent_product = ParentProduct.objects.filter(parent_id=row['parent_id'])
                except Exception as e:
                    parent_data.append(str(row_num))
                try:
                    ParentProduct.objects.filter(parent_id=row['parent_id']).update(
                        parent_brand=Brand.objects.filter(id=row['sub_brand_id'].strip()).last(),
                        brand_case_size=row['brand_case_size'], inner_case_size=row['inner_case_size'])
                except:
                    parent_brand.append(str(row_num))
                try:
                    required_parent_hsn_data_list = ['parent_id', 'hsn']
                    required_data = False
                    for ele in required_parent_hsn_data_list:
                        if ele in header_list:
                            required_data = True
                        else:
                            required_data = False
                            break
                    if required_data:
                        ParentProduct.objects.filter(parent_id=row['parent_id']).update(
                            product_hsn=ProductHSN.objects.filter(
                                product_hsn_code=row['hsn'].replace("'", '')).last())
                except:
                    parent_hsn.append(str(row_num))
                try:
                    if 'sub_category_id' in header_list:
                        ParentProductCategory.objects.filter(parent_product=parent_product[0].id).update(
                            category=Category.objects.filter(id=row['sub_category_id'].strip()).last())
                except:
                    parent_category.append(str(row_num))
                    required_parent_hsn_data_list = ['tax_1(gst)', 'Tax_2(cess/surcharge)']
                    required_data = False
                    for ele in required_parent_hsn_data_list:
                        if ele in header_list:
                            required_data = True
                        else:
                            required_data = False
                            break
                    if required_data:
                        if not row['tax_1(gst)'] == '':
                            tax = tax.objects.filter(tax_name=row['tax_1(gst)'])
                            ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(
                                tax=tax[0])
                        if not row['Tax_2(cess/surcharge)'] == '':
                            tax = tax.objects.filter(tax_name=row['tax_2(cess/surcharge)'])
                            ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(
                                tax=tax[0])
            else:
                continue
        logger.info("Total row executed :" + str(count))
        logger.info("Parent_ID is not exist in these row:" + str(parent_data))
        logger.info("Parent Brand is not exist in these row :" + str(parent_brand))
        logger.info("Parent HSN is not exist in these row :" + str(parent_hsn))
        logger.info("Parent Category is not exist in these row :" + str(parent_category))
        logger.info("Method Complete to set the data for Parent SKU")


    @classmethod
    def set_child_parent(cls, header_list, excel_file_data_list):
        logger.info("Method Start to set the Child to Parent mapping from excel file")
        count = 0
        row_num = 1
        set_child = []
        for row in excel_file_data_list:
            row_num += 1
            if not row['status'] == 'Deactivated':
                count += 1
                try:
                    Product.objects.filter(product_sku=row['sku_id']).update(
                        parent_product=ParentProduct.objects.filter(parent_id=row['parent_id']).last())
                except:
                    set_child.append(str(row_num))
            else:
                continue
        logger.info("Total row executed :" + str(count))
        logger.info("Child SKU is not exist in these row :" + str(set_child))
        logger.info("Method complete to set the Child to Parent mapping from excel file")

    @classmethod
    def set_child_data(cls, header_list, excel_file_data_list):
        logger.info("Method Start to set the Child data from excel file")
        count = 0
        row_num = 1
        child_data = []
        for row in excel_file_data_list:
            row_num += 1
            if not row['status'] == 'Deactivated':
                count += 1
                try:
                    Product.objects.filter(product_sku=row['sku_id']).update(product_ean_code=row['ean'],
                                                                             product_name=row['sku_name'],
                                                                             status='active', )
                except:
                    child_data.append(str(row_num))
            else:
                continue
        logger.info("Total row executed :" + str(count))
        logger.info("Child SKU is not exist in these row :" + str(child_data))
        logger.info("Script Complete to set the Child data")
