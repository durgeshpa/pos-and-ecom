from cms.models import CardItem, LandingPageProducts
from pos.common_functions import PosInventoryCls
from wms.models import PosInventoryState


def check_inventory(product, shop_id):
    exclude_product_id = []
    sliced_product = product[0:min(product.count(),100)]
    for prd in sliced_product:
        if isinstance(prd, CardItem):
            product_id = prd.content_id
        elif isinstance(prd, LandingPageProducts):
            product_id = prd.product_id
        available_inventory = PosInventoryCls.get_available_inventory_by_linked_product(product_id,
                                                                      PosInventoryState.AVAILABLE, shop_id)
        if available_inventory < 1:
            exclude_product_id.append(prd.id)
    product = product.exclude(id__in = exclude_product_id)
    return product


def isEmptyString(string):
    """
    Checks if given string is empty
    """
    if string is None or len(string.strip()) == 0:
        return True
    return False