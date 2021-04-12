import csv
import codecs

from django.db import transaction

from gram_to_brand.models import GRNOrderProductMapping
from products.models import ProductVendorMapping, ParentProduct
from products.utils import vendor_product_mapping
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
        product_ids = []
        if instance.cart_product_mapping_csv:
            reader = csv.reader(codecs.iterdecode(instance.cart_product_mapping_csv, 'utf-8'))
            next(reader)
            for row in reader:
                if row[0] and row[2] and row[6] and row[7]:
                    product_ids += [int(row[2])]
                    create_cart_product_mapping(row, instance)
        CartProductMapping.objects.filter(cart_id=instance.id).exclude(cart_product_id__in=product_ids).delete()


def create_cart_product_mapping(row, instance):
    parent_product = ParentProduct.objects.get(parent_id=row[0])
    vendor_product = ProductVendorMapping.objects.filter(vendor=instance.supplier_name, product_id=row[2]).last()
    if row[8].lower() == "per piece":
        if vendor_product.filter(product_price=row[9], status=True).exists():
            vendor_product_dt = vendor_product.filter(product_price=row[9], status=True).last()
        else:
            vendor_product_dt = vendor_product_mapping(instance.supplier_name, row[2], row[9], row[7], row[5],
                                                       'per piece')
    elif row[8].lower() == "per pack":
        if vendor_product.filter(product_price_pack=row[9], status=True).exists():
            vendor_product_dt = vendor_product.filter(product_price_pack=row[9], status=True).last()
        else:
            vendor_product_dt = vendor_product_mapping(instance.supplier_name, row[2], row[9], row[7], row[5],
                                                       'per pack')
    no_of_pieces = int(vendor_product_dt.case_size) * int(row[6])
    cart_prod_map = CartProductMapping.objects.filter(cart=instance, cart_product_id=row[2]).last()
    if cart_prod_map:
        cart_prod_map.cart_parent_product = parent_product
        cart_prod_map.no_of_pieces = no_of_pieces
        cart_prod_map.price = float(row[9])
        cart_prod_map.vendor_product = vendor_product_dt
        cart_prod_map.save()
    else:
        CartProductMapping.objects.create(cart=instance, cart_product_id=row[2], cart_parent_product=parent_product,
                                          no_of_pieces=no_of_pieces, price=float(row[9]),
                                          vendor_product=vendor_product_dt)
