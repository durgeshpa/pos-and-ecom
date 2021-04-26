import os
import django
import csv
import codecs
from products.models import Product, ParentProduct, ParentProductCategory, ParentProductTaxMapping, Tax, ProductHSN
from brand.models import Brand
from categories.models import Category

def run():
    set_inactive_status()
    set_sub_brand_and_brand()
    set_sub_category_and_category()
    set_parent_data()
    set_child_parent()
    set_child_data()


def set_inactive_status():
    """
    This method is used for to set inactive status for Product
    """
    f = open('products/scripts/master_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    first_row = next(reader)
    print ("Script Start to set the Inactive status from csv file")
    count = 0
    for row_id, row in enumerate(reader):
        if row[12] == 'In-Active':
            count += 1
            Product.objects.filter(product_sku=row[2]).update(status='deactivated')
        else:
            continue
    print("Inactive row id count :" + str(count))
    print("Script Complete to set the Inactive status from csv file")


def set_sub_brand_and_brand():
    """
    This method is used for match sub_brand to brand
    """
    f = open('products/scripts/master_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    first_row = next(reader)
    print("Script Start to set the Sub-brand to Brand mapping from csv file")
    count = 0
    sub_brand = []
    for row_id, row in enumerate(reader):
        count += 1
        try:
            if row[7] == row[5]:
                continue
            else:
                Brand.objects.filter(id=row[7]).update(brand_parent=row[5])
        except:
            sub_brand.append(str(row_id))
    print("Total row executed :" + str(count))
    print("Sub brand is not updated in these row :" + str(sub_brand))
    print("Script Complete to set the Sub-brand to Brand mapping from csv file")


def set_sub_category_and_category():
    """
    This method is used for match sub_category to category
    """
    f = open('products/scripts/master_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    first_row = next(reader)
    print("Script Start to set the Sub-Category to Category mapping from csv file")
    count = 0
    sub_category = []
    for row_id, row in enumerate(reader):
        count += 1
        try:
            if row[16] == row[14]:
                continue
            else:
                Category.objects.filter(id=row[16]).update(category_parent=row[14])
        except:
            sub_category.append(str(row_id))
    print("Total row executed :" + str(count))
    print("Sub Category is not updated in these row :" + str(sub_category))
    print("Script Complete to set the Sub-Category to Category mapping from csv file")


def set_parent_data():
    """
    This method is used to set parent sku data from csv file
    """
    f = open('products/scripts/master_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    first_row = next(reader)
    print("Script Start to set the data for Parent SKU")
    count = 0
    parent_data = []
    parent_brand = []
    parent_hsn = []
    parent_category = []
    for row_id, row in enumerate(reader):
        if not row[12] == 'In-Active':
            count += 1
            try:
                parent_product = ParentProduct.objects.filter(parent_id=row[1])
            except Exception as e:
                parent_data.append(str(row_id))
            try:
                ParentProduct.objects.filter(parent_id=row[1]).update(parent_brand=Brand.objects.filter(id=row[7].strip()).last(),
                                                                      brand_case_size=row[10], inner_case_size=row[11])
            except:
                parent_brand.append(str(row_id))
            try:
                ParentProduct.objects.filter(parent_id=row[1]).update(product_hsn=ProductHSN.objects.filter(product_hsn_code=row[9].strip()).last())
            except:
                parent_hsn.append(str(row_id))
            try:
                ParentProductCategory.objects.filter(parent_product=parent_product[0].id).update(category=Category.objects.filter(id=row[16].strip()).last())
            except:
                parent_category.append(str(row_id))
            if not row[17] == '':
                tax = Tax.objects.filter(tax_name=row[17])
                ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(tax=tax[0])
            if not row[18] == '':
                tax = Tax.objects.filter(tax_name=row[18])
                ParentProductTaxMapping.objects.filter(parent_product=parent_product[0].id).update(tax=tax[0])
        else:
            continue
    print("Total row executed :" + str(count))
    print("Parent id is not exist in these row :" + str(parent_data))
    print("Parent Brand is not exist in these row :" + str(parent_brand))
    print("Parent HSN is not exist in these row :" + str(parent_hsn))
    print("Parent Category is not exist in these row :" + str(parent_category))
    print("Script Complete to set the data for Parent SKU")


def set_child_parent():
    """
    This method is used to set child sku to parent sku
    """
    f = open('products/scripts/master_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    first_row = next(reader)
    print("Script Start to set the Child to Parent mapping from csv file")
    count = 0
    set_child = []
    for row_id, row in enumerate(reader):
        if not row[12] == 'In-Active':
            count += 1
            try:
                Product.objects.filter(product_sku=row[2]).update(parent_product=ParentProduct.objects.filter(parent_id=row[1]).last())
            except:
                set_child.append(str(row_id))
        else:
            continue
    print("Total row executed :" + str(count))
    print("Child SKU is not exist in these row :" + str(set_child))
    print("Script Complete to set the Child to Parent mapping from csv file")


def set_child_data():
    """
    This method is used to set child sku data from csv
    """
    f = open('products/scripts/master_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    first_row = next(reader)
    print("Script Start to set the Child data")
    count = 0
    child_data = []
    for row_id, row in enumerate(reader):
        if not row[12] == 'In-Active':
            count += 1
            try:
                Product.objects.filter(product_sku=row[2]).update(product_ean_code=row[3], product_name= row[8],
                                                                  status='active',)
            except:
                child_data.append(str(row_id))
        else:
            continue
    print("Total row executed :" + str(count))
    print("Child SKU is not exist in these row :" + str(child_data))
    print("Script Complete to set the Child data")
