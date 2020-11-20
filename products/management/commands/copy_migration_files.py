import os
import csv
from datetime import datetime

from django.core.management.base import BaseCommand
from products.models import Product, ProductPrice, ParentProductCategory
from shops.models import Shop

class Command(BaseCommand):
    help = 'Script to copy migration files from PROD server to Local'

    def handle(self, *args, **options):
        copy_migration_files()
        # find_mismatch_mrp()
        # copy_cats()


def copy_cats():
    # products = Product.objects.filter(product_sku='CNPPROLAY00000019')
    # print(products)
    time_inst = datetime(2020,11,18,0,0,0)
    already_done = ParentProductCategory.objects.filter(created_at__gte=time_inst).values_list('parent_product__id', flat=True).distinct()
    already_done = list(already_done)
    print(len(already_done))
    count = 0
    products = Product.objects.exclude(parent_product__id__in=already_done)
    print(len(products))
    # return
    for product in products:
        if not product.parent_product or not product.product_pro_category.exists():
            continue
        parent_id = product.parent_product.id
        if parent_id in already_done:
            # print("skipping")
            continue
        parent = product.parent_product
        # print(parent)
        cats = product.product_pro_category.all()
        # print(cats.last().category)
        # print(ParentProductCategory.objects.filter(parent_product=parent).last().category)
        ParentProductCategory.objects.filter(parent_product=parent).delete()
        for cat in cats:
            ParentProductCategory.objects.create(
                parent_product=parent,
                category=cat.category
            ).save()
        count += 1
        if count % 10 == 0:
            print("Done: {}".format(count))
            



def find_mismatch_mrp():
    f = open('products/management/product_mrp_mismatch_prices.csv', 'w')
    writer = csv.writer(f)
    writer.writerow(["Product ID", "Product SKU", "Product Name", "Product MRP at Child Level", "Multiple Active Prices for Addistro Noida"])
    addis_noida_shop = Shop.objects.filter(
        shop_name='ADDISTRO TECHNOLOGIES PVT LTD (NOIDA)',
        shop_type__shop_type='sp'
    ).last()
    gfdn_noida_shop = Shop.objects.filter(
        shop_name='GFDN SERVICES PVT LTD (NOIDA)',
        shop_type__shop_type='sp'
    ).last()
    products = Product.objects.all()
    for product in products:
        mult_active = False
        mismatch = False
        prices = product.product_pro_price.filter(seller_shop=gfdn_noida_shop, status=True, approval_status=2)
        if prices:
            if len(prices) > 1:
                mult_active = True
            # print(len(prices))
            for price in prices:
                if price.mrp != product.product_mrp:
                    mismatch = True
                    break
        if mismatch:
            writer.writerow([str(product.id), str(product.product_sku), str(product.product_name), str(product.product_mrp), str(mult_active)])
    f.close()



def copy_migration_files():
    # PROD Server IP
    server_ip = '13.127.58.205'
    # Location of PEM file to access SCP
    key_location = 'products/management/commands/live_server_key.pem'
    app_list = [
        'addresses', 'audit', 'brand', 'categories', 'coupon', 'gram_to_brand',
        'offer', 'orders', 'products', 'retailer_to_gram', 'retailer_to_sp',
        'services', 'shops', 'sp_to_gram', 'wms'
    ]

    for app in app_list:
        if not os.path.exists(f'./{app}/migrations'):
            os.makedirs(f'./{app}/migrations')

        if not os.path.exists(f'./local_migrations_bkp/{app}'):
            os.makedirs(f'./local_migrations_bkp/{app}')
            os.makedirs(f'./local_migrations_bkp/{app}/migrations')

        cp_command = f'cp ./{app}/migrations/*.py ./local_migrations_bkp/{app}/migrations/'
        os.system(cp_command)
        rm_command = f'rm -rf ./{app}/migrations/*.py'
        os.system(rm_command)
        command = f'sudo scp -i ./{key_location} ubuntu@{server_ip}:"~/project/retailer-backend/{app}/migrations/*.py" ./{app}/migrations/'
        os.system(command)
