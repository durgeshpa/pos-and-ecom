from django.db import transaction
from django.db.models import Sum

from retailer_to_sp.models import OrderedProductMapping, OrderedProduct, Order, OrderedProductBatch
from wms.common_functions import CommonWarehouseInventoryFunctions, InCommonFunctions
from wms.models import InventoryType, InventoryState

trip_id = 18996
type_normal = InventoryType.objects.filter(inventory_type='normal').last()
state_picked = InventoryState.objects.filter(inventory_state='picked').last()
state_shipped = InventoryState.objects.filter(inventory_state='shipped').last()

def run():
    oredered_product = OrderedProduct.objects.filter(id__in=[217354,217353])
    for shipment in oredered_product:
        with transaction.atomic():
            print('shipment {}'.format(shipment.id))
            order_status = Order.FULL_SHIPMENT_CREATED
            for product in shipment.rt_order_product_order_product_mapping.all():
                print('shipment {} product {} shipped_qty {}'.format(shipment.id, product.product, product.shipped_qty))

                shipment_batch_list = OrderedProductBatch.objects.filter(
                    ordered_product_mapping=product).all()
                for shipment_batch in shipment_batch_list:
                    InCommonFunctions.create_only_in(shipment.order.seller_shop, 'warehouse_adjustment', shipment.pk,
                                                     product.product, shipment_batch.batch_id,
                                                     shipment_batch.quantity, type_normal)
                # CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                #     shipment.order.seller_shop, product.product, type_normal, state_picked, product.shipped_qty,
                #     "warehouse_adjustment", trip_id)
                # CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                #     shipment.order.seller_shop, product.product, type_normal, state_shipped, -1 * product.shipped_qty,
                #     "warehouse_adjustment", trip_id)
                # if shipment.order.ordered_cart.rt_cart_list.filter(cart_product=product.product).last().no_of_pieces != product.shipped_qty:
                #     order_status = Order.PARTIAL_SHIPMENT_CREATED

            print('shipment {} order status {}'.format(shipment.id, order_status))
            # shipment.shipment_status = OrderedProduct.READY_TO_SHIP
            # shipment.trip = None
            # shipment.order.order_status = order_status
            # shipment.order.save()
            # shipment.save()