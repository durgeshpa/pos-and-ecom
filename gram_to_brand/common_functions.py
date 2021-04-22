from decimal import Decimal

from .models import GRNOrderProductMapping
from wms.models import InventoryType, WarehouseInventory
from wms.common_functions import get_stock
from products.models import Product, ProductSourceMapping, DestinationRepackagingCostMapping, ProductPackingMapping
from shops.models import ParentRetailerMapping


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
    if product_type == 'source':
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        retailer = ParentRetailerMapping.objects.filter(parent=shop, status=True).last().retailer
        inventory = get_stock(retailer, type_normal, [product_id])
        inv_total = inventory[int(product_id)] if inventory and int(product_id) in inventory else 0
        grn_total = grn_qty
    elif product_type == 'packing_material':
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        inventory = WarehouseInventory.objects.filter(inventory_type=type_normal,
                                                      inventory_state__inventory_state='total_available',
                                                      sku_id=product_id).last()
        inv_total = inventory.weight if inventory else 0
        product = Product.objects.get(id=product_id)
        grn_total = grn_qty * product.weight_value
    else:
        return

    grn_piece_price = grn_price / case_size if grn_price_unit == 'Per Pack' else grn_price

    last_product_grn = GRNOrderProductMapping.objects.filter(product=product_id, delivered_qty__gt=0). \
        exclude(id=grn_map_id).order_by('created_at').last()
    last_tax_percentage = last_product_grn.grn_order.order.ordered_cart.cart_list.filter(cart_product=product_id). \
        values_list('_tax_percentage', flat=True)
    last_tax_percentage = last_tax_percentage[0] if last_tax_percentage else 0
    last_price = 0
    if last_product_grn:
        vendor_product = last_product_grn.vendor_product
        last_price = last_product_grn.product_invoice_price
        if vendor_product.brand_to_gram_price_unit == 'Per Pack':
            last_price = last_price / vendor_product.case_size

    moving_buying_price = round(Decimal((float(grn_total) * (float(grn_piece_price) / (1 + tax_percentage)) +
                                         float(inv_total) * (float(last_price) / (1 + last_tax_percentage))) / float(
        grn_total + inv_total)), 2)
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
                                                      source_sku.moving_average_buying_price / source_sku.weight_value) * destination_sku.weight_value
            raw_m_cost = total_raw_material / count if count > 0 else 0
            DestinationRepackagingCostMapping.objects.filter(destination=destination_sku). \
                update(raw_material=round(Decimal(raw_m_cost), 2))
    # packing material cost
    else:
        product_mappings = ProductPackingMapping.objects.filter(packing_sku_id=product_id)
        for mapping in product_mappings:
            pack_product = mapping.packing_sku
            destination_product = mapping.sku
            pack_m_cost = (
                                      pack_product.moving_average_buying_price / pack_product.weight_value) * mapping.packing_sku_weight_per_unit_sku
            DestinationRepackagingCostMapping.objects.filter(destination=destination_product).update(
                primary_pm_cost=round(Decimal(pack_m_cost), 2))
