import csv
import codecs
from decimal import Decimal

from django.db import transaction

from rest_framework import status
from rest_framework.response import Response

from wms.models import InventoryType, WarehouseInventory
from wms.common_functions import get_stock
from products.models import Product, ProductSourceMapping, DestinationRepackagingCostMapping, ProductPackingMapping
from shops.models import ParentRetailerMapping
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


def moving_average_buying_price(product_id, grn_map_id, product_type, grn_price, grn_qty, shop, grn_price_unit,
                                case_size, tax_percentage):
    """
        Update moving average buying price for source and packing material products
    """
    retailer = ParentRetailerMapping.objects.filter(parent=shop, status=True).last().retailer
    if product_type == 'source':
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        inventory = get_stock(retailer, type_normal, [product_id])
        inv_total = inventory[int(product_id)] if inventory and int(product_id) in inventory else 0
        grn_total = grn_qty
    elif product_type == 'packing_material':
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        inventory = WarehouseInventory.objects.filter(inventory_type=type_normal,
                                                      inventory_state__inventory_state='total_available',
                                                      sku_id=product_id,
                                                      warehouse=retailer).last()
        inv_total = inventory.weight if inventory else 0
        product = Product.objects.get(id=product_id)
        grn_total = grn_qty * product.weight_value
    else:
        return

    grn_piece_price = grn_price / case_size if grn_price_unit == 'Per Pack' else grn_price

    last_product_grn = GRNOrderProductMapping.objects.filter(product=product_id, delivered_qty__gt=0). \
        exclude(id=grn_map_id).order_by('created_at').last()
    last_price = 0
    last_tax_percentage = 0
    if last_product_grn:
        vendor_product = last_product_grn.vendor_product
        last_price = last_product_grn.product_invoice_price
        if vendor_product.brand_to_gram_price_unit == 'Per Pack':
            last_price = last_price / vendor_product.case_size
        last_tax_percentage = last_product_grn.grn_order.order.ordered_cart.cart_list.filter(cart_product=product_id). \
            values_list('_tax_percentage', flat=True)
        last_tax_percentage = last_tax_percentage[0] if last_tax_percentage else 0

    moving_buying_price = round(Decimal((float(grn_total) * (float(grn_piece_price) / (1 + (tax_percentage / 100))) +
                                         float(inv_total) * (float(last_price) / (1 + (last_tax_percentage / 100)))) / float(grn_total + inv_total)), 2)
    Product.objects.filter(id=product_id).update(moving_average_buying_price=moving_buying_price)
    update_destination_pack_cost(product_type, product_id)


def update_destination_pack_cost(product_type, product_id):
    """
        Update raw material and packing cost for destination product
    """
    # Update raw material cost
    if product_type == 'source':
        product_mappings = ProductSourceMapping.objects.filter(source_sku_id=product_id)
        for mapping in product_mappings:
            destination_sku = mapping.destination_sku
            source_sku_maps = ProductSourceMapping.objects.filter(destination_sku=destination_sku)
            total_raw_material = 0
            count = 0
            for source_sku_map in source_sku_maps:
                source_sku = source_sku_map.source_sku
                if source_sku.moving_average_buying_price:
                    count += 1
                    total_raw_material += (
                                                      float(source_sku.moving_average_buying_price) / float(source_sku.weight_value)) * float(destination_sku.weight_value)
            raw_m_cost = total_raw_material / count if count > 0 else 0
            DestinationRepackagingCostMapping.objects.filter(destination=destination_sku). \
                update(raw_material=round(Decimal(raw_m_cost), 2))
    # packing material cost
    else:
        product_mappings = ProductPackingMapping.objects.filter(packing_sku_id=product_id)
        for mapping in product_mappings:
            pack_product = mapping.packing_sku
            destination_product = mapping.sku
            pack_m_cost = (float(pack_product.moving_average_buying_price) / float(pack_product.weight_value)) * \
                           float(mapping.packing_sku_weight_per_unit_sku)
            DestinationRepackagingCostMapping.objects.filter(destination=destination_product).update(
                primary_pm_cost=round(Decimal(pack_m_cost), 2))


def upload_cart_product_csv(instance):
    """
        Add products to cart via csv upload
    """
    with transaction.atomic():
        product_ids = []
        if instance.cart_product_mapping_csv:
            reader = csv.reader(codecs.iterdecode(instance.cart_product_mapping_csv, 'utf-8'))
            next(reader)
            for row in reader:
                if row[0] and row[2] and row[6] and row[7]:
                    product_ids += [int(row[2])]
                    # create/update cart product mapping for each product in csv
                    create_cart_product_mapping(row, instance)
        # Delete all other existing cart products
        CartProductMapping.objects.filter(cart_id=instance.id).exclude(cart_product_id__in=product_ids).delete()


def create_cart_product_mapping(row, instance):
    """
        Adding product in cart
        Mapping product to vendor, price details
        Adding entry for product to map to cart and vendor
    """
    parent_product = ParentProduct.objects.get(parent_id=row[0])
    # check if vendor mapping already exists, else create
    vendor_product = ProductVendorMapping.objects.filter(vendor=instance.supplier_name, product_id=row[2])
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
    # create or update entry for product in cart
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


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True,
                      "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": []}

    return Response(result, status=status_code)


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]
