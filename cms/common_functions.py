from pos.common_functions import PosInventoryCls
from wms.models import PosInventoryState


def check_inventory(product):
    exclude_product_id = []
    sliced_product = product[0:min(product.count(),100)]
    for prd in sliced_product:
        available_inventory = PosInventoryCls.get_available_inventory(prd.id, PosInventoryState.AVAILABLE)
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