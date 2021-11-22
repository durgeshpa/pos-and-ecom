import json
import csv
import codecs


from django.core.management.base import BaseCommand
from products.models import Product, ProductPrice
from shops.models import Shop

class Command(BaseCommand):
    help = 'Script to store product status and mrp data before running Parent Child Migration'

    def handle(self, *args, **options):
        # create_product_status_data()
        # create_mrp_data()
        create_brand_data()

def create_product_status_data():
    status_file = open('products/management/commands/product_status_data.txt', "w")
    products = Product.objects.all().only('status', 'id')
    status_data = {}
    for product in products:
        if product.status:
            status_data[product.id] = 'active'
        else:
            status_data[product.id] = 'deactivated'
    print(len(status_data))
    status_data = json.dumps(status_data)
    status_file.write(status_data)
    status_file.close()

def create_mrp_data():
    mrp_file = open('products/management/commands/product_mrp_data.txt', "w")
    products = Product.objects.all().only('id', 'pk')
    mrp_data = {}

    missing_mrp_file = open('products/management/commands/missing_mrp_data.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(missing_mrp_file, 'utf-8', errors='ignore'))
    first_row = next(reader)
    for _, row in enumerate(reader):
        if not row[0] or not row[9]:
            continue
        try:
            mrp_val = float(row[9])
        except Exception as e:
            continue
        else:
            mrp_data[row[0]] = str(mrp_val)

    for product in products:
        mrp_found, mrp = find_mrp(product)
        if mrp_found:
            mrp_data[product.id] = str(mrp)
    print(len(mrp_data))
    mrp_data = json.dumps(mrp_data)
    mrp_file.write(mrp_data)
    mrp_file.close()

def find_mrp(product):
    mrp_found = False
    mrp = 0

    addis_noida_shop = Shop.objects.filter(shop_name='ADDISTRO TECHNOLOGIES PVT LTD (NOIDA)', shop_type__shop_type='sp').last()

    prices = product.product_pro_price.filter(seller_shop=addis_noida_shop, status=True, approval_status=2)
    if prices:
        mrp_found = True
        mrp = product.product_pro_price.filter(seller_shop=addis_noida_shop, status=True, approval_status=2).last().mrp
    else:
        prices = product.product_pro_price.filter(seller_shop=addis_noida_shop, status=True)
        if prices:
            mrp_found = True
            mrp = product.product_pro_price.filter(seller_shop=addis_noida_shop, status=True).last().mrp
        else:
            prices = product.product_pro_price.filter(seller_shop=addis_noida_shop)
            if prices:
                mrp_found = True
                mrp = product.product_pro_price.filter(seller_shop=addis_noida_shop).last().mrp
            else:
                prices = product.product_vendor_mapping.all()
                if prices:
                    mrp_found = True
                    mrp = product.product_vendor_mapping.all().last().product_mrp
    return mrp_found, mrp

def create_brand_data():

    # mrp_data = {}
    # missing_mrp_file = open('products/management/commands/missing_mrp_data.csv', 'rb')
    # reader = csv.reader(codecs.iterdecode(missing_mrp_file, 'utf-8'))
    # first_row = next(reader)
    # for _, row in enumerate(reader):
    #     if not row[0] or not row[9]:
    #         continue
    #     try:
    #         mrp_val = float(row[9])
    #     except Exception as e:
    #         continue
    #     else:
    #         mrp_data[row[0]] = str(mrp_val)

    brand_file = open('products/management/commands/product_brand_data.txt', "w")
    brand_data = {}
    products = Product.objects.all()
    for product in products:
        brand_data[product.id] = {}
        if product.product_hsn:
            brand_data[product.id]['hsn'] = product.product_hsn.id
        if product.product_brand:
            brand_data[product.id]['brand'] = product.product_brand.id
        brand_data[product.id]['inner_case'] = product.product_inner_case_size or 1
        brand_data[product.id]['case'] = product.product_case_size or 1
        brand_data[product.id]['cats'] = []
        for cat in product.product_pro_category.all():
            brand_data[product.id]['cats'].append(cat.category.id)
        brand_data[product.id]['tax'] = []
        for tax in product.product_pro_tax.all():
            brand_data[product.id]['tax'].append("{}__{}".format(tax.tax.tax_type, tax.tax.tax_percentage))
        if product.status:
            brand_data[product.id]['status'] = 'active'
        else:
            brand_data[product.id]['status'] = 'deactivated'
        mrp_found, mrp = find_mrp(product)
        if mrp_found:
            brand_data[product.id]['mrp'] = str(mrp)
        # elif mrp_data.get(product.id):
        #     brand_data[product.id]['mrp'] = mrp_data[product.id]
        # elif mrp_data.get(str(product.id)):
        #     brand_data[product.id]['mrp'] = mrp_data[str(product.id)]
        


    print(len(brand_data))
    brand_data = json.dumps(brand_data)
    brand_file.write(brand_data)
    brand_file.close()
