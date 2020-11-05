import json


from django.core.management.base import BaseCommand
from products.models import Product, ProductPrice
from shops.models import Shop

class Command(BaseCommand):
    help = 'Script to store product status and mrp data before running Parent Child Migration'

    def handle(self, *args, **options):
        create_product_status_data()
        create_mrp_data()

def create_product_status_data():
    status_file = open('products/management/commands/product_status_data.txt', "w")
    products = Product.objects.all().only('status', 'id')
    status_data = {}
    for product in products:
        if product.status:
            status_data[product.id] = 'active'
        else:
            status_data[product.id] = 'deactivated'
    status_data = json.dumps(status_data)
    status_file.write(status_data)
    status_file.close()

def create_mrp_data():
    mrp_file = open('products/management/commands/product_mrp_data.txt', "w")
    products = Product.objects.all().only('id', 'pk')
    mrp_data = {}
    for product in products:
        mrp_found, mrp = find_mrp(product)
        if mrp_found:
            mrp_data[product.id] = str(mrp)
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
