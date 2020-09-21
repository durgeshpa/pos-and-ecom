# This file contains the migration script for production env

from retailer_to_sp.models import Order, CartProductMapping
from wms.models import OrderReserveRelease, WarehouseInternalInventoryChange, WarehouseInventory, InventoryType, \
    InventoryState
from django.db import transaction
import logging

info_logger = logging.getLogger('file-info')


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


def generate_order_data_for_order(o):
    cart_products_mapping = CartProductMapping.objects.filter(cart=o.ordered_cart, status=True)
    info_logger.info(
        "WMS Migration : Order data generation : Warehouse {}, Order No {} : no of products {}".format(
            o.seller_shop, o.order_no, cart_products_mapping.count()))
    for p in cart_products_mapping:
        info_logger.info("WMS Migration : Order data generation : product sku {} quantity {}".format(
            p.cart_product.product_sku, p.qty))
        create_wms_entry_for_cart_product(o.order_no, o.seller_shop, p.cart_product, p.qty)


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
    info_logger.info("WMS Migration : Order data generation : completed for Order {} Product {}".format(order_no, sku.product_sku))


def create_inventory(warehouse, sku, inventory_type, inventory_state, quantity):
    inventory, created = WarehouseInventory.objects.get_or_create(warehouse=warehouse, sku=sku,
                                                                  inventory_type=inventory_type,
                                                                  inventory_state=inventory_state,
                                                                  in_stock=True,
                                                                  defaults={'quantity': quantity})
    if not created:
        inventory.quantity = inventory.quantity + quantity
        inventory.save()


def create_inventory_transactions(order_no, warehouse, sku, transaction_type, initial_type, initial_stage, final_type,
                                  final_stage, quantity):
    return WarehouseInternalInventoryChange.objects.create(warehouse=warehouse,
                                                           sku=sku,
                                                           transaction_type=transaction_type,
                                                           transaction_id=order_no,
                                                           initial_type=initial_type,
                                                           final_type=final_type,
                                                           initial_stage=initial_stage,
                                                           final_stage=final_stage,
                                                           quantity=quantity)
