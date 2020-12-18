from django.db import transaction

from retailer_to_sp.models import CartProductMapping
from wms.common_functions import CommonBinInventoryFunctions, InternalInventoryChange
from wms.models import Pickup, PickupBinInventory, InventoryType, BinInventory

def run():
    fix_bin_inventory()

@transaction.atomic
def fix_bin_inventory():
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    cart_products = CartProductMapping.objects.filter(cart__order_id='BOR2009010000690')
    for p in cart_products:
        pickup_obj = Pickup.objects.filter(pickup_type_id='BOR2009010000690',
                                           status='picking_cancelled',
                                           sku=p.cart_product).last()
        pickup_bin_qs = PickupBinInventory.objects.filter(pickup=pickup_obj)
        for item in pickup_bin_qs:
            bi_qs = BinInventory.objects.filter(id=item.bin_id)
            bi = bi_qs.last()
            bin_quantity = bi.quantity + item.quantity
            bi_qs.update(quantity=bin_quantity)
            InternalInventoryChange.create_bin_internal_inventory_change(bi.warehouse, bi.sku, bi.batch_id,
                                                                         bi.bin,
                                                                         type_normal, type_normal,
                                                                         "picking_cancelled",
                                                                         pickup_obj.pk,
                                                                         item.quantity)
            print('fix_bin_inventory| inventory reverted for sku-{}, batch-{}, qty-{}'
                  .format(bi.sku, bi.batch_id, item.quantity))
        print('fix_bin_inventory| inventory reverted for pickup-{}'.format(pickup_obj.pk))
    print('fix_bin_inventory|ended')