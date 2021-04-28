import csv
import codecs
from products.models import Product
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Script to upload MRP for product'

    def handle(self, *args, **options):
        mrp_upload_product()
        # find_mismatch_mrp()
        # copy_cats()


def mrp_upload_product():
    f = open('products/management/missing_mrp_products_1.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8', errors='ignore'))
    first_row = next(reader)
    for row_id, row in enumerate(reader):
        print(row_id)
        if not row[0] or not row[4]:
            continue
        product = Product.objects.get(id=int(row[0]))
        product_mrp = float(row[4])
        product.product_mrp = product_mrp
        product.save()
