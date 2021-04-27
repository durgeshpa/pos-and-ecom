import csv
import codecs

from django.db import transaction

from products.models import Product, ProductSourceMapping, DestinationRepackagingCostMapping, ProductPackingMapping
from django.core.management.base import BaseCommand
from decimal import Decimal
from gram_to_brand.models import GRNOrderProductMapping


class Command(BaseCommand):
    help = 'Script to alter product repackaging type'

    def handle(self, *args, **options):
        repackaging_type_modify()


def repackaging_type_modify():
    with transaction.atomic():
        # update moving average price source skus
        grn_notfound = []
        source_modified = []
        source_skus = Product.objects.filter(repackaging_type='source')

        for source_sku in source_skus:
            last_source_product_grn = GRNOrderProductMapping.objects.filter(product=source_sku, delivered_qty__gt=0) \
                .order_by('created_at').last()
            if last_source_product_grn:
                vendor_product = last_source_product_grn.vendor_product
                last_price = last_source_product_grn.product_invoice_price
                if vendor_product.brand_to_gram_price_unit == 'Per Pack':
                    last_price = last_price / vendor_product.case_size
                last_tax_percentage = last_source_product_grn.grn_order.order.ordered_cart.cart_list.filter(
                    cart_product=source_sku).values_list('_tax_percentage', flat=True)
                last_tax_percentage = last_tax_percentage[0] if last_tax_percentage else 0
                source_sku.moving_average_buying_price = round(
                    Decimal(float(last_price) / (1 + (last_tax_percentage / 100))), 2)
                source_sku.save()
                source_modified += [source_sku.product_sku]
            else:
                grn_notfound += [source_sku.product_sku]

        print("below Source moving price updated")
        print(source_modified)
        print("           ")

        print("below Source grn not found")
        print(grn_notfound)
        print("           ")

        f = open('products/management/dest_pack_update.csv', 'rb')
        reader = csv.reader(codecs.iterdecode(f, 'utf-8'))
        first_row = next(reader)
        pp_notfound = []
        pp_found = []
        pgrn_notfound = []
        destination_notfound = []
        dest_found = []
        cost_not_found = []
        for row_id, row in enumerate(reader):

            try:
                pack_product = Product.objects.get(product_sku=row[1].strip())
                pp_found += [row[1]]
            except:
                pp_notfound += [row[1]]
                continue
            last_pack_product_grn = GRNOrderProductMapping.objects.filter(product=pack_product, delivered_qty__gt=0) \
                .order_by('created_at').last()
            if last_pack_product_grn:
                vendor_product = last_pack_product_grn.vendor_product
                last_price = last_pack_product_grn.product_invoice_price
                if vendor_product.brand_to_gram_price_unit == 'Per Pack':
                    last_price = last_price / vendor_product.case_size
                last_tax_percentage = last_pack_product_grn.grn_order.order.ordered_cart.cart_list.filter(
                    cart_product=pack_product).values_list('_tax_percentage', flat=True)
                last_tax_percentage = last_tax_percentage[0] if last_tax_percentage else 0
                pack_product.moving_average_buying_price = round(
                    Decimal(float(last_price) / (1 + (last_tax_percentage / 100))), 2)
            else:
                pgrn_notfound += [pack_product.product_sku]

            pack_product.repackaging_type = 'packing_material'
            pack_product.save()

            if row[0] and row[0].strip():

                try:
                    dest_product = Product.objects.get(product_sku=row[0].strip(), repackaging_type='destination')
                    dest_found += [row[0]]
                except:
                    destination_notfound += [row[0]]
                    continue

                try:
                    ppm = ProductPackingMapping.objects.get(sku=dest_product)
                except:
                    ppm = ProductPackingMapping.objects.create(sku=dest_product, packing_sku=pack_product,
                                                               packing_sku_weight_per_unit_sku=round(Decimal(row[2]), 2))
                ppm.packing_sku = pack_product
                ppm.packing_sku_weight_per_unit_sku = round(Decimal(row[2]), 2)
                ppm.save()

                source_sku_maps = ProductSourceMapping.objects.filter(destination_sku=dest_product)
                total_raw_material = 0
                count = 0
                for source_sku_map in source_sku_maps:
                    source_sku = source_sku_map.source_sku
                    if source_sku.moving_average_buying_price:
                        count += 1
                        total_raw_material += (
                                                      source_sku.moving_average_buying_price / source_sku.weight_value) * dest_product.weight_value
                raw_m_cost = total_raw_material / count if count > 0 else 0

                pack_m_cost = 0
                if pack_product.moving_average_buying_price:
                    pack_m_cost = (
                                          pack_product.moving_average_buying_price / pack_product.weight_value) * ppm.packing_sku_weight_per_unit_sku

                cost = DestinationRepackagingCostMapping.objects.filter(destination=dest_product).last()
                if cost:
                    if pack_m_cost > 0:
                        cost.primary_pm_cost = round(Decimal(pack_m_cost), 2)
                    if raw_m_cost > 0:
                        cost.raw_material = round(Decimal(raw_m_cost), 2)
                    cost.save()
                else:
                    cost_not_found += [row[0]]
                    DestinationRepackagingCostMapping.objects.create(destination=dest_product, raw_material=round(Decimal(raw_m_cost), 2),
                                                                     wastage=round(Decimal(0), 2), fumigation=round(Decimal(0), 2),
                                                                     label_printing=round(Decimal(0), 2), packing_labour=round(Decimal(0), 2),
                                                                     primary_pm_cost=round(Decimal(pack_m_cost), 2), secondary_pm_cost=round(Decimal(0), 2))

        print("         ")

        print("below Packing sku grn not found")
        print(set(pgrn_notfound))
        print("           ")

        print("below Packing sku found")
        print(set(pp_found))
        print("         ")

        print("below packing sku not found")
        print(set(pp_notfound))
        print("         ")

        print("below destination cost not found")
        print(set(cost_not_found))
        print("           ")

        print("below destination sku updated")
        print(set(dest_found))
        print("      ")

        print("below destination sku not found")
        print(set(destination_notfound))

    # f = open('products/management/repackaging_type_update.csv', 'rb')
    # reader = csv.reader(codecs.iterdecode(f, 'utf-8'))
    # first_row = next(reader)
    # for row_id, row in enumerate(reader):
    #     if not row[0]:
    #         print("No SKU Id {}".format(row_id))
    #         continue
    #     if not row[1]:
    #         print('provide repackaging type {}'.format(row_id))
    #         continue
    #     row[1] = row[1].strip().lower()
    #     if row[1] not in ['source', 'destination']:
    #         print("Rep Type invalid {}".format(row_id))
    #         continue
    #     try:
    #         product = Product.objects.get(product_sku=row[0].strip())
    #     except:
    #         print("product not found {}".format(row_id))
    #         continue
    #     repackaging_type = row[1].strip()
    #     if repackaging_type == 'destination':
    #         if not row[2] or not row[3] or not row[4] or not row[5] or not row[6] \
    #                 or not row[7] or not row[8] or not row[9]:
    #             print("Required destination values not present {}".format(row_id))
    #             continue
    #
    #         try:
    #             source_sku = Product.objects.get(product_sku=row[2].strip())
    #         except:
    #             print("Source for destination not found {}".format(row_id))
    #             continue
    #
    #         ProductSourceMapping.objects.get_or_create(source_sku=source_sku, destination_sku=product)
    #         dest_cost_obj = DestinationRepackagingCostMapping.objects.filter(destination=product).last()
    #         if dest_cost_obj:
    #             dest_cost_obj.raw_material=round(Decimal(row[3]), 2)
    #             dest_cost_obj.wastage=round(Decimal(row[4]), 2)
    #             dest_cost_obj.fumigation=round(Decimal(row[5]), 2)
    #             dest_cost_obj.label_printing=round(Decimal(row[6]), 2)
    #             dest_cost_obj.packing_labour=round(Decimal(row[7]), 2)
    #             dest_cost_obj.primary_pm_cost=round(Decimal(row[8]), 2)
    #             dest_cost_obj.secondary_pm_cost=round(Decimal(row[9]), 2)
    #             dest_cost_obj.save()
    #         else:
    #             DestinationRepackagingCostMapping.objects.create(destination=product, raw_material=round(Decimal(row[3]), 2),
    #                                                              wastage=round(Decimal(row[4]), 2), fumigation=round(Decimal(row[5]), 2),
    #                                                              label_printing=round(Decimal(row[6]), 2), packing_labour=round(Decimal(row[7]), 2),
    #                                                              primary_pm_cost=round(Decimal(row[8]), 2), secondary_pm_cost=round(Decimal(row[9]), 2))
    #
    #     product.repackaging_type = repackaging_type
    #     product.save()
    #     print("processed {}".format(row[0]))
