from django.db import transaction

from pos.common_functions import PosInventoryCls
from wms.models import PosInventory, PosInventoryState
from accounts.models import User


def run(*args):
    with transaction.atomic():
        # Move all ordered inventory to shipped
        ordered_inventory = PosInventory.objects.filter(inventory_state__inventory_state=PosInventoryState.ORDERED).all()

        user = User.objects.get(phone_number=7763886418)
        for or_inv in ordered_inventory:
            PosInventoryCls.order_inventory(or_inv.product.id, PosInventoryState.ORDERED, PosInventoryState.SHIPPED,
                                            or_inv.quantity, user, "Inventory Move", "Inventory Move")
