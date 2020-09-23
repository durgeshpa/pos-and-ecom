# This file contains the migration script for production env

from retailer_to_sp.models import Order, CartProductMapping, OrderedProductBatch, OrderedProduct
from wms.models import OrderReserveRelease, WarehouseInternalInventoryChange, WarehouseInventory, InventoryType, \
    InventoryState, Pickup, PickupBinInventory, Bin
from django.db import transaction
import logging

info_logger = logging.getLogger('file-info')
virtual_bin= Bin.objects.filter(bin_id='V2VZ01SR001-0001').last()

def generate_order_data():
    orders = Order.objects.filter(order_status=Order.ORDERED,
                                  order_closed=False)  # add check for shipment status
    info_logger.info(
        "WMS Migration : Order data generation : Order State [ordered] : no of orders {}".format(orders.count()))
    for o in orders:
        generate_order_data_for_order(o)

def generate_order_data_by_order_no(order_no):
    order = Order.objects.filter(order_no=order_no).last()
    if order.order_closed:
        info_logger.error(
            "WMS Migration : Order data generation : Order No {} : order is already closed".format(order_no))
    if order.order_status == Order.ORDERED:
        generate_order_data_for_order(order)


def warehouse_entry_exists(order_no, seller_shop, cart_product, qty):
    return WarehouseInternalInventoryChange.objects.filter(warehouse=seller_shop,
                                                           sku=cart_product,
                                                           transaction_id=order_no,
                                                           quantity=qty).exists()


def generate_order_data_for_order(o):
    cart_products_mapping = CartProductMapping.objects.filter(cart=o.ordered_cart, status=True)
    info_logger.info(
        "WMS Migration : Order data generation : Warehouse {}, Order No {} : no of products {}".format(
            o.seller_shop, o.order_no, cart_products_mapping.count()))
    for p in cart_products_mapping:
        info_logger.info("WMS Migration : Order data generation : product sku {} quantity {}".format(
            p.cart_product.product_sku, p.qty))
        already_created = warehouse_entry_exists(o.order_no, o.seller_shop, p.cart_product, p.qty)
        if not already_created:
            create_wms_entry_for_cart_product(o.order_no, o.seller_shop, p.cart_product, p.qty)
        else:
            info_logger.info(
                "WMS Migration : Order data generation : Warehouse {}, Order No {} : "
                "product sku {} quantity {} ENTRY ALREADY CREATED".format(
                    o.seller_shop, o.order_no, p.cart_product.product_sku, p.qty))


@transaction.atomic
def create_wms_entry_for_cart_product(order_no, warehouse, sku, quantity):
    inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
    stage_available = InventoryState.objects.filter(inventory_state='available').last()
    stage_reserved = InventoryState.objects.filter(inventory_state='reserved').last()
    stage_ordered = InventoryState.objects.filter(inventory_state='ordered').last()

    transaction_type = 'reserved'
    create_inventory(warehouse, sku, inventory_type, stage_reserved, 0)
    info_logger.info("WMS Migration : Order data generation : inventory created {}".format(stage_reserved))
    warehouse_internal_inventory_reserve = create_inventory_transactions(order_no, warehouse, sku, transaction_type,
                                                                         inventory_type,
                                                                         stage_available,
                                                                         inventory_type, stage_reserved, quantity)

    info_logger.info("WMS Migration : Order data generation : inventory transaction created {}".format(stage_reserved))
    transaction_type = 'ordered'
    create_inventory(warehouse, sku, inventory_type, stage_ordered, quantity)
    info_logger.info("WMS Migration : Order data generation : inventory created {}".format(stage_ordered))
    warehouse_internal_inventory_release = create_inventory_transactions(order_no, warehouse, sku, transaction_type,
                                                                         inventory_type,
                                                                         stage_reserved,
                                                                         inventory_type, stage_ordered, quantity)
    info_logger.info("WMS Migration : Order data generation : inventory transaction created {}".format(stage_ordered))

    OrderReserveRelease.objects.create(warehouse=warehouse,
                                       sku=sku,
                                       transaction_id=order_no,
                                       warehouse_internal_inventory_reserve=warehouse_internal_inventory_reserve,
                                       warehouse_internal_inventory_release=warehouse_internal_inventory_release,
                                       reserved_time=warehouse_internal_inventory_reserve.created_at,
                                       release_time=warehouse_internal_inventory_release.created_at)
    info_logger.info(
        "WMS Migration : Order data generation : completed for Order {} Product {}".format(order_no, sku.product_sku))


def create_inventory(warehouse, sku, inventory_type, inventory_state, quantity):
    inventory, created = WarehouseInventory.objects.get_or_create(warehouse=warehouse, sku=sku,
                                                                  inventory_type=inventory_type,
                                                                  inventory_state=inventory_state,
                                                                  in_stock=True,
                                                                  defaults={'quantity': quantity})
    if not created:
        inventory.quantity = inventory.quantity + quantity
        inventory.save()


def create_inventory_transactions(transaction_id, warehouse, sku, transaction_type, initial_type, initial_stage, final_type,
                                  final_stage, quantity):
    return WarehouseInternalInventoryChange.objects.create(warehouse=warehouse,
                                                           sku=sku,
                                                           transaction_type=transaction_type,
                                                           transaction_id=transaction_id,
                                                           initial_type=initial_type,
                                                           final_type=final_type,
                                                           initial_stage=initial_stage,
                                                           final_stage=final_stage,
                                                           quantity=quantity)

def shipment_basic_entry(shipment):
    for shipment_product in shipment.rt_order_product_order_product_mapping.all():
        create_pickup_entry(shipment_product)

def create_pickup_entry(shipment_product):
    quantity = shipment_product.ordered_product.order.ordered_cart.rt_cart_list.filter(cart_product=shipment_product.product)
    pickup, created = Pickup.objects.get_or_create(warehouse=shipment_product.ordered_product.order.seller_shop,
                                 pickup_type="Order",
                                 pickup_type_id=shipment_product.ordered_product.order.order_no,
                                 sku=shipment_product.product,
                                 quantity=quantity,
                                 pickup_quantity=shipment_product.shipped_qty,
                                 status="picking_complete")
    if created:
        batch_id = '{}{}'.format(shipment_product.product.product_sku,'31032021')
        shipment_batch = create_batch_entry(shipment_product)
        pickup_bin, created = PickupBinInventory.objects.get_or_create(warehouse=shipment_product.ordered_product.order.seller_shop,
                                                       pickup=pickup,
                                                       batch_id=batch_id,
                                                       bin=virtual_bin,
                                                       quantity=quantity,
                                                       pickup_quantity=shipment_product.shipped_qty,
                                                       shipment_batch= shipment_batch )

def create_batch_entry(shipment_product):
    batch_id = '{}{}'.format(shipment_product.product.product_sku, '31032021')
    ordered_quantity = shipment_product.ordered_product.order.ordered_cart.rt_cart_list.filter(
        cart_product=shipment_product.product)
    batch,created = OrderedProductBatch.objects.get_or_create(batch_id=batch_id,ordered_product_mapping=shipment_product,
                                              bin=virtual_bin,quantity=shipment_product.shipped_qty,
                                              ordered_pieces=ordered_quantity,pickup_quantity=shipment_product.shipped_qty,
                                              expiry_date='31/03/2021')
    return batch


def shipment_picked_entry(shipment):
    inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
    stage_picked = InventoryState.objects.filter(inventory_state='picked').last()
    stage_ordered = InventoryState.objects.filter(inventory_state='ordered').last()

    for shipment_product in shipment.rt_order_product_order_product_mapping.all():
        pickup=Pickup.objects.filter(warehouse=shipment_product.ordered_product.order.seller_shop,
                              pickup_type="Order",
                              pickup_type_id=shipment_product.ordered_product.order.order_no,
                              sku=shipment_product.product,
                              status="picking_complete").last()
        create_inventory(shipment_product.ordered_product.order.seller_shop, shipment_product.product,
                         inventory_type, stage_ordered, shipment_product.shipped_qty*-1)
        create_inventory(shipment_product.ordered_product.order.seller_shop, shipment_product.product,
                         inventory_type, stage_picked, shipment_product.shipped_qty)
        create_inventory_transactions(pickup.pk,
                                      shipment_product.ordered_product.order.seller_shop,
                                      shipment_product.product, "pickup_complete", inventory_type, stage_ordered,
                                      inventory_type,
                                      stage_picked, shipment_product.shipped_qty)


def shipment_shipped_entry(shipment):
    inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
    stage_picked = InventoryState.objects.filter(inventory_state='picked').last()
    stage_shipped = InventoryState.objects.filter(inventory_state='shipped').last()

    for shipment_product in shipment.rt_order_product_order_product_mapping.all():
        create_inventory(shipment_product.ordered_product.order.seller_shop, shipment_product.product,
                         inventory_type, stage_picked, shipment_product.shipped_qty * -1)
        create_inventory(shipment_product.ordered_product.order.seller_shop, shipment_product.product,
                         inventory_type, stage_shipped, shipment_product.shipped_qty)
        create_inventory_transactions(shipment.pk,
                                      shipment_product.ordered_product.order.seller_shop,
                                      shipment_product.product, "shipped_out", inventory_type, stage_picked,
                                      inventory_type,
                                      stage_shipped, shipment_product.shipped_qty)


def create_shipment_data_before_delivery():
    shipment_status = ['SHIPMENT_CREATED','READY_TO_SHIP','READY_TO_DISPATCH','OUT_FOR_DELIVERY']
    ordered_product_list = OrderedProduct.objects.filter(shipment_status__in = shipment_status)
    for ordered_product in ordered_product_list:
        generate_order_data_for_order(ordered_product.order)
        shipment_basic_entry(ordered_product)
        shipment_picked_entry(ordered_product)
        if ordered_product.shipment_status=='OUT_FOR_DELIVERY':
            shipment_shipped_entry(ordered_product)
        

