import logging

from brand.models import Brand
from categories.models import Category
from products.models import Product, ParentProduct, ParentProductTaxMapping, ProductHSN, ParentProductCategory, Tax

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')


class SetMasterData(object):
    """
    It will call the functions mentioned in UploadMasterData class as per the condition of header_list
    """

    @classmethod
    def set_master_data(cls, header_list, excel_file_data_list):
        if 'status' in header_list:
            UploadMasterData.set_inactive_status(header_list, excel_file_data_list)
            UploadMasterData.set_parent_data(header_list, excel_file_data_list)
            UploadMasterData.set_child_parent(header_list, excel_file_data_list)
        
        if 'sub_brand_id' in header_list and 'brand_id' in header_list:
            UploadMasterData.set_sub_brand_and_brand(header_list, excel_file_data_list)

        if 'sub_category_id' in header_list and 'category_id' in header_list:
            UploadMasterData.set_sub_category_and_category(header_list, excel_file_data_list)

        if 'status' in header_list and 'sku_name' in header_list:
            UploadMasterData.set_child_data(header_list, excel_file_data_list)



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
    def set_inactive_status(cls, header_list, excel_file_data_list):
        try:
            count = 0
            logger.info("Method Start to set Inactive status from excel file")
            for row in excel_file_data_list:
                if row['status'] == 'Deactivated':
                    count += 1
                    Product.objects.filter(product_sku=str(row['sku_id']).strip()).update(status='deactivated')
                else:
                    continue
            info_logger.info("Inactive row id count :" + str(count))
            info_logger.info("Method Complete to set the Inactive status from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Inactive Status Functionality' + {str(e)}")

    @classmethod
    def set_sub_brand_and_brand(cls, header_list, excel_file_data_list):
        try:
            count = 0
            row_num = 1
            sub_brand = []
            info_logger.info('Method Start to set the Sub-brand to Brand mapping from excel file')
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
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Sub brand is not updated in these row :" + str(sub_brand))
            info_logger.info("Method complete to set the Sub-Brand to Brand mapping from csv file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Sub Brand and Brand Functionality' + {str(e)}")

    @classmethod
    def set_sub_category_and_category(cls, header_list, excel_file_data_list):
        try:
            count = 0
            row_num = 1
            sub_category = []
            info_logger.info("Method Start to set the Sub-Category to Category mapping from excel file")
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
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Sub Category is not updated in these row :" + str(sub_category))
            info_logger.info("Method Complete to set the Sub-Category to Category mapping from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Sub Category and Category Functionality' + {str(e)}")

    @classmethod
    def set_parent_data(cls, header_list, excel_file_data_list):
        try:
            count = 0
            row_num = 1
            parent_data = []
            parent_brand = []
            parent_hsn = []
            parent_category = []
            parent_tax = []
            info_logger.info("Method Start to set the data for Parent SKU")
            for row in excel_file_data_list:
                row_num += 1
                if not row['status'] == 'Deactivated':
                    count += 1
                    try:
                        if 'parent_id' in header_list:
                            parent_product = ParentProduct.objects.filter(parent_id=str(row['parent_id']).strip())
                    except Exception as e:
                        parent_data.append(str(row_num))
                    try:
                        required_parent_brand_data_list = ['sub_brand_id', 'brand_case_size', 'inner_case_size']
                        required_data = False
                        for ele in required_parent_brand_data_list:
                            if ele in header_list:
                                required_data = True
                            else:
                                required_data = False
                                break
                        if required_data:
                            ParentProduct.objects.filter(parent_id=str(row['parent_id']).strip()).update(
                                parent_brand=Brand.objects.filter(id=row['sub_brand_id']).last(),
                                brand_case_size=row['brand_case_size'], inner_case_size=row['inner_case_size'])
                    except:
                        parent_brand.append(str(row_num))
                    try:
                        if 'hsn' in header_list:
                            ParentProduct.objects.filter(parent_id=str(row['parent_id']).strip()).update(
                                product_hsn=ProductHSN.objects.filter(
                                    product_hsn_code=row['hsn'].replace("'", '')).last())
                    except:
                        parent_hsn.append(str(row_num))
                    try:
                        if 'sub_category_id' in header_list:
                            ParentProductCategory.objects.filter(parent_product=parent_product[0].id).update(
                                category=Category.objects.filter(id=row['sub_category_id']).last())
                    except:
                        parent_category.append(str(row_num))
                    try:
                        if 'tax_1(gst)' in header_list and 'tax_2(cess/surcharge)' in header_list:
                            if not row['tax_1(gst)'] == '':
                                tax = Tax.objects.filter(tax_name=row['tax_1(gst)'])
                                ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(
                                    tax=tax[0])
                            if not row['tax_2(cess/surcharge)'] == '':
                                tax = Tax.objects.filter(tax_name=row['tax_2(cess/surcharge)'])
                                ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(
                                    tax=tax[0])
                    except:
                        parent_tax.append(str(row_num))
                else:
                    continue
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Parent_ID is not exist in these row:" + str(parent_data))
            info_logger.info("Parent Brand is not exist in these row :" + str(parent_brand))
            info_logger.info("Parent HSN is not exist in these row :" + str(parent_hsn))
            info_logger.info("Parent Category is not exist in these row :" + str(parent_category))
            info_logger.info("Tax is not exist in these row :" + str(parent_tax))
            info_logger.info("Method Complete to set the data for Parent SKU")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Parent Data Functionality' + {str(e)}")

    @classmethod
    def set_child_parent(cls, header_list, excel_file_data_list):
        try:
            info_logger.info("Method Start to set the Child to Parent mapping from excel file")
            count = 0
            row_num = 1
            set_child = []
            for row in excel_file_data_list:
                row_num += 1
                if not row['status'] == 'Deactivated':
                    count += 1
                    try:
                        Product.objects.filter(product_sku=str(row['sku_id']).strip()).update(
                            parent_product=ParentProduct.objects.filter(parent_id=str(row['parent_id']).strip()).last())
                    except:
                        set_child.append(str(row_num))
                else:
                    continue
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Child SKU is not exist in these row :" + str(set_child))
            info_logger.info("Method complete to set the Child to Parent mapping from excel file")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Child Parent Functionality' + {str(e)}")

    @classmethod
    def set_child_data(cls, header_list, excel_file_data_list):
        try:
            info_logger.info("Method Start to set the Child data from excel file")
            count = 0
            row_num = 1
            child_data = []
            for row in excel_file_data_list:
                row_num += 1
                if not row['status'] == 'Deactivated':
                    count += 1
                    try:
                        if 'ean' in header_list:
                            Product.objects.filter(product_sku=str(row['sku_id']).strip()).update(product_ean_code=row['ean'],
                                                                                                  product_name=row['sku_name'],
                                                                                                  status='active', )
                    except:
                        child_data.append(str(row_num))
                else:
                    continue
            info_logger.info("Total row executed :" + str(count))
            info_logger.info("Child SKU is not exist in these row :" + str(child_data))
            info_logger.info("Script Complete to set the Child data")
        except Exception as e:
            error_logger.info(
                f"Something went wrong, while working with 'Set Child Data Functionality' + {str(e)}")
