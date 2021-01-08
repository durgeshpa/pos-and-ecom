import csv
import codecs
from products.models import Product, ProductSourceMapping, DestinationRepackagingCostMapping
from django.core.management.base import BaseCommand
from decimal import Decimal

class Command(BaseCommand):
    help = 'Script to alter product repackaging type'

    def handle(self, *args, **options):
        repackaging_type_modify()


def repackaging_type_modify():
    f = open('products/management/repackaging_type_update.csv', 'rb')
    reader = csv.reader(codecs.iterdecode(f, 'utf-8'))
    first_row = next(reader)
    for row_id, row in enumerate(reader):
        if not row[0]:
            print("No SKU Id {}".format(row_id))
            continue
        if not row[1]:
            print('provide repackaging type {}'.format(row_id))
            continue
        row[1] = row[1].strip().lower()
        if row[1] not in ['source', 'destination']:
            print("Rep Type invalid {}".format(row_id))
            continue
        try:
            product = Product.objects.get(product_sku=row[0].strip())
        except:
            print("product not found {}".format(row_id))
            continue
        repackaging_type = row[1].strip()
        if repackaging_type == 'destination':
            if not row[2] or not row[3] or not row[4] or not row[5] or not row[6] \
                    or not row[7] or not row[8] or not row[9]:
                print("Required destination values not present {}".format(row_id))
                continue

            try:
                source_sku = Product.objects.get(product_sku=row[2].strip())
            except:
                print("Source for destination not found {}".format(row_id))
                continue

            ProductSourceMapping.objects.get_or_create(source_sku=source_sku, destination_sku=product)
            dest_cost_obj = DestinationRepackagingCostMapping.objects.filter(destination=product).last()
            if dest_cost_obj:
                dest_cost_obj.raw_material=round(Decimal(row[3]), 2)
                dest_cost_obj.wastage=round(Decimal(row[4]), 2)
                dest_cost_obj.fumigation=round(Decimal(row[5]), 2)
                dest_cost_obj.label_printing=round(Decimal(row[6]), 2)
                dest_cost_obj.packing_labour=round(Decimal(row[7]), 2)
                dest_cost_obj.primary_pm_cost=round(Decimal(row[8]), 2)
                dest_cost_obj.secondary_pm_cost=round(Decimal(row[9]), 2)
                dest_cost_obj.save()
            else:
                DestinationRepackagingCostMapping.objects.create(destination=product, raw_material=round(Decimal(row[3]), 2),
                                                                 wastage=round(Decimal(row[4]), 2), fumigation=round(Decimal(row[5]), 2),
                                                                 label_printing=round(Decimal(row[6]), 2), packing_labour=round(Decimal(row[7]), 2),
                                                                 primary_pm_cost=round(Decimal(row[8]), 2), secondary_pm_cost=round(Decimal(row[9]), 2))

        product.repackaging_type = repackaging_type
        product.save()
        print("processed {}".format(row[0]))
