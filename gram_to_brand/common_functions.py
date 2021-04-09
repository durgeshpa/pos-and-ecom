import csv
import codecs

from django.db import transaction

from gram_to_brand.models import GRNOrderProductMapping
from products.models import Product, ProductVendorMapping, ParentProduct
from .models import CartProductMapping


def get_grned_product_qty_by_grn_id(grn_id):
    """takes grn id and returns product along with grned quantity in dictionary"""
    grn_products_qs = GRNOrderProductMapping.objects.filter(grn_order_id=grn_id, delivered_qty__gt=0)
    product_qty_dict = {}
    for g in grn_products_qs:
        if product_qty_dict.get(g.product_id) is None:
            product_qty_dict[g.product_id] = 0
        product_qty_dict[g.product_id] += g.delivered_qty
    return product_qty_dict


def upload_cart_product_csv(instance):
    with transaction.atomic():
        CartProductMapping.objects.filter(cart_id=instance.id).delete()
        if instance.cart_product_mapping_csv:
            reader = csv.reader(codecs.iterdecode(instance.cart_product_mapping_csv, 'utf-8'))
            for row in reader:
                if row[0] and row[2] and row[6] and row[7]:
                    create_cart_product_mapping(row, instance)


def create_cart_product_mapping(row, instance):
    parent_product = ParentProduct.objects.get(parent_id=row[0])
    vendor_product = ProductVendorMapping.objects.filter(vendor=instance.supplier_name, product_id=row[2]).last()
    if row[8].lower() == "per piece":
        if vendor_product and (vendor_product.case_size == row[5] or vendor_product.product_price == row[9]):
            vendor_product_dt = vendor_product
        else:
            vendor_product_dt, created = ProductVendorMapping.objects.get_or_create(vendor=instance.supplier_name,
                                                                                    product_id=row[2],
                                                                                    product_price=row[9],
                                                                                    product_mrp=row[7],
                                                                                    case_size=row[5], status=True)
    elif row[8].lower() == "per pack":
        if vendor_product and (vendor_product.case_size == row[5] or vendor_product.product_price_pack == row[9]):
            vendor_product_dt = vendor_product
        else:
            vendor_product_dt, created = ProductVendorMapping.objects.get_or_create(vendor=instance.supplier_name,
                                                                                    product_id=row[2],
                                                                                    product_price_pack=row[9],
                                                                                    product_mrp=row[7],
                                                                                    case_size=row[5], status=True)
    CartProductMapping.objects.get_or_create(cart=instance, cart_parent_product=parent_product, cart_product_id=row[2],
                                             no_of_pieces=int(vendor_product_dt.case_size) * int(row[6]),
                                             price=float(row[9]), vendor_product=vendor_product_dt)
