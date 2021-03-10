from gram_to_brand.models import GRNOrderProductMapping


def get_grned_product_qty_by_grn_id(grn_id):
    """takes grn id and returns product along with grned quantity in dictionary"""
    grn_products_qs = GRNOrderProductMapping.objects.filter(grn_order_id=grn_id, delivered_qty__gt=0)
    product_qty_dict = {}
    for g in grn_products_qs:
        if product_qty_dict.get(g.product_id) is None:
            product_qty_dict[g.product_id] = 0
        product_qty_dict[g.product_id] += g.delivered_qty
    return product_qty_dict
