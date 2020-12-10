import os
import django
import csv
import codecs
from products.models import Product, ParentProduct, ParentProductCategory, ParentProductTaxMapping, Tax, ProductHSN
from brand.models import Brand
from categories.models import Category

def run():
    f = open('products/scripts/master_data_1.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8'))
    first_row = next(reader)
    set_inactive_status(reader)
    set_sub_brand_and_brand(reader)
    set_sub_category_and_category(reader)
    set_parent_data(reader)
    set_child_parent(reader)
    set_child_data(reader)


def set_inactive_status(reader):
    """
    This method is used for to set inactive status for Product

    :param reader: CSV reader
    :return:
    """
    print ("Script Start to set the Inactive status from csv file")
    count = 0
    for row_id, row in enumerate(reader):
        if row[12] == 'In-Active':
            count += 1
            print("Inactive row number:- " + str(row_id) and "Count is: " + str(count))
            Product.objects.filter(product_sku=row[2]).update(status='deactivated')
        else:
            continue
    print("Inactive row id count :" + str(count))
    print("Script Complete to set the Inactive status from csv file")


def set_sub_brand_and_brand(reader):
    """
    This method is used for match sub_brand to brand

    :param reader: CSV reader
    :return:
    """
    print("Script Start to set the Sub-brand to Brand mapping from csv file")
    count = 0
    for row_id, row in enumerate(reader):
        print("Total row : " + str(row_id))
        count += 1
        print("Active Product row number:- " + str(row_id) and "Count is: " + str(count))
        try:
            Brand.objects.filter(id=row[7]).update(brand_parent=row[5])
        except:
            print("SubBrand is not exist in Database:= " + str(row_id))
    print("Total row executed :" + str(count))
    print("Script Complete to set the Sub-brand to Brand mapping from csv file")


def set_sub_category_and_category(reader):
    """
    This method is used for match sub_category to category

    :param reader: CSV reader
    :return:
    """
    print("Script Start to set the Sub-Category to Category mapping from csv file")
    count = 0
    for row_id, row in enumerate(reader):
        print("Total row : " + str(row_id))
        count += 1
        print("Active Product row number:- " + str(row_id) and "Count is: " + str(count))
        try:
            Category.objects.filter(id=row[16]).update(category_parent=row[14])
        except:
            print("SubCategory is not exist in Database:= " + str(row_id))
    print("Total row executed :" + str(count))
    print("Script Complete to set the Sub-Category to Category mapping from csv file")


def set_parent_data(reader):
    """
    This method is used to set parent sku data from csv file

    :param reader: CSV reader
    :return:
    """
    print("Script Start to set the data for Parent SKU")
    count = 0
    for row_id, row in enumerate(reader):
        print("Total row : " + str(row_id))
        if not row[12] == 'In-Active':
            count += 1
            print("Active Product row number:- " + str(row_id) and "Count is: " + str(count))
            try:
                parent_product = ParentProduct.objects.filter(parent_id=row[1])
                ParentProduct.objects.filter(parent_id=row[1]).update(parent_brand=Brand.objects.filter(id=row[7].strip()).last(),
                                                                      product_hsn=ProductHSN.objects.filter(product_hsn_code=row[9].replace("'", '')).last(),
                                                                      brand_case_size=row[10], inner_case_size=row[11])
                ParentProductCategory.objects.filter(parent_product=parent_product[0].id).update(category=Category.objects.filter(id=row[16].strip()).last())
                if not row[17] == '':
                    tax = Tax.objects.filter(tax_name=row[17])
                    ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(tax=tax[0])
                if not row[18] == '':
                    tax = Tax.objects.filter(tax_name=row[18])
                    ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(tax=tax[0])
            except Exception as e:
                print("Parent ID is not exist in Database:= " + str(e))
        else:
            continue
    print("Total row executed :" + str(count))
    print("Script Complete to set the data for Parent SKU")


def set_child_parent(reader):
    """
    This method is used to set child sku to parent sku

    :param reader: CSV reader
    :return:
    """
    print("Script Start to set the Child to Parent mapping from csv file")
    count = 0
    for row_id, row in enumerate(reader):
        if not row[12] == 'In-Active':
            print("Total row : " + str(row_id))
            count += 1
            print("Active Product row number:- " + str(row_id) and "Count is: " + str(count))
            try:
                Product.objects.filter(product_sku=row[2]).update(parent_product=ParentProduct.objects.filter(parent_id=row[1]).last())
            except:
                print("SubCategory is not exist in Database:= " + str(row_id))
        else:
            continue
    print("Total row executed :" + str(count))
    print("Script Complete to set the Child to Parent mapping from csv file")


def set_child_data(reader):
    """
    This method is used to set child sku data from csv

    :param reader: CSV reader
    :return:
    """
    print("Script Start to set the Child data")
    count = 0
    for row_id, row in enumerate(reader):
        if not row[12] == 'In-Active':
            print("Total row : " + str(row_id))
            count += 1
            print("Active Product row number:- " + str(row_id) and "Count is: " + str(count))
            try:
                Product.objects.filter(product_sku=row[2]).update(product_ean_code=row[3], product_name= row[8],
                                                                  status='active',)
            except:
                print("SubCategory is not exist in Database:= " + str(row_id))
        else:
            continue
    print("Total row executed :" + str(count))
    print("Script Complete to set the Child data")
