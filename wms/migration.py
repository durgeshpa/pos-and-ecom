# This file contains the migration script for production env
from datetime import datetime,timedelta
from retailer_to_sp.models import Order, CartProductMapping, OrderedProductBatch, OrderedProduct
from wms.models import OrderReserveRelease, WarehouseInternalInventoryChange, WarehouseInventory, InventoryType, \
    InventoryState, Pickup, PickupBinInventory, Bin, BinInventory
from django.db import transaction
from shops.models import Shop
from products.models import Product
import logging

info_logger = logging.getLogger('file-info')
virtual_bin = Bin.objects.filter(bin_id='V2VZ01SR001-0001').last()
start_time = datetime.now() - timedelta(days=30)
print(start_time)


def generate_order_data():
    orders = Order.objects.filter(order_status=Order.ORDERED,
                                  order_closed=False, created_at__gt=start_time)  # add check for shipment status
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
        already_created = warehouse_entry_exists(o.order_no, o.seller_shop, p.cart_product, p.no_of_pieces)
        if not already_created:
            create_wms_entry_for_cart_product(o.order_no, o.seller_shop, p.cart_product, p.no_of_pieces)
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


def create_inventory_transactions(transaction_id, warehouse, sku, transaction_type, initial_type, initial_stage,
                                  final_type,
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


@transaction.atomic
def shipment_basic_entry(shipment):
    for shipment_product in shipment.rt_order_product_order_product_mapping.all():
        shipment_status_return = ['FULLY_RETURNED_AND_COMPLETED', 'PARTIALLY_DELIVERED_AND_COMPLETED', 'READY_TO_DISPATCH',
                           'FULLY_DELIVERED_AND_COMPLETED']
        if shipment.shipment_status in shipment_status_return:
            shipment_product.returned_damage_qty=shipment_product.damaged_qty
            shipment_product.damaged_qty=0
        shipment_product.picked_pieces = shipment_product.shipped_qty
        shipment_product.save()
        create_pickup_entry(shipment_product)


def create_pickup_entry(shipment_product):
    cartproduct = shipment_product.ordered_product.order.ordered_cart.rt_cart_list.filter(
        cart_product=shipment_product.product).last()
    inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
    print(cartproduct.qty)
    print(cartproduct.no_of_pieces)
    pickup, created = Pickup.objects.get_or_create(warehouse=shipment_product.ordered_product.order.seller_shop,
                                                   pickup_type="Order",
                                                   pickup_type_id=shipment_product.ordered_product.order.order_no,
                                                   sku=shipment_product.product,
                                                   quantity=cartproduct.no_of_pieces,
                                                   pickup_quantity=shipment_product.shipped_qty,
                                                   status="picking_complete")
    if created:
        batch_id = '{}{}'.format(shipment_product.product.product_sku, '310321')
        shipment_batch = create_batch_entry(shipment_product)
        bin_inventory = BinInventory.objects.filter(warehouse=shipment_product.ordered_product.order.seller_shop,
                                                    bin=virtual_bin,
                                                    sku=shipment_product.product,
                                                    batch_id=batch_id,
                                                    inventory_type=inventory_type
                                                    ).last()
        pickup_bin, created = PickupBinInventory.objects.get_or_create(
            warehouse=shipment_product.ordered_product.order.seller_shop,
            pickup=pickup,
            batch_id=batch_id,
            bin=bin_inventory,
            quantity=cartproduct.no_of_pieces,
            pickup_quantity=shipment_product.shipped_qty,
            shipment_batch=shipment_batch)


def create_batch_entry(shipment_product):
    print(shipment_product)
    print(shipment_product.shipped_qty)
    batch_id = '{}{}'.format(shipment_product.product.product_sku, '31032021')
    cartproduct = shipment_product.ordered_product.order.ordered_cart.rt_cart_list.filter(
        cart_product=shipment_product.product).last()
    print(cartproduct)
    print(cartproduct.no_of_pieces)
    shipped_qty = shipment_product.shipped_qty
    if shipped_qty is None:
        shipped_qty = 0
    batch = OrderedProductBatch.objects.create(batch_id=batch_id,
                                               ordered_product_mapping=shipment_product,
                                               quantity=shipped_qty,
                                               ordered_pieces=cartproduct.no_of_pieces,
                                               pickup_quantity=shipped_qty,
                                               expiry_date='31/03/2021')
    return batch


@transaction.atomic
def shipment_picked_entry(shipment):
    inventory_type = InventoryType.objects.filter(inventory_type='normal').last()
    stage_picked = InventoryState.objects.filter(inventory_state='picked').last()
    stage_ordered = InventoryState.objects.filter(inventory_state='ordered').last()

    for shipment_product in shipment.rt_order_product_order_product_mapping.all():
        pickup = Pickup.objects.filter(warehouse=shipment_product.ordered_product.order.seller_shop,
                                       pickup_type="Order",
                                       pickup_type_id=shipment_product.ordered_product.order.order_no,
                                       sku=shipment_product.product,
                                       status="picking_complete").last()
        create_inventory(shipment_product.ordered_product.order.seller_shop, shipment_product.product,
                         inventory_type, stage_ordered, shipment_product.shipped_qty * -1)
        create_inventory(shipment_product.ordered_product.order.seller_shop, shipment_product.product,
                         inventory_type, stage_picked, shipment_product.shipped_qty)
        create_inventory_transactions(pickup.pk,
                                      shipment_product.ordered_product.order.seller_shop,
                                      shipment_product.product, "pickup_complete", inventory_type, stage_ordered,
                                      inventory_type,
                                      stage_picked, shipment_product.shipped_qty)


@transaction.atomic
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
    ordered_product_list = OrderedProduct.objects.filter(shipment_status__in=shipment_status, created_at__gt=start_time)
    print(ordered_product_list)
    info_logger.info("WMS Migration : total shipments found {}".format(ordered_product_list.count()))
    for ordered_product in ordered_product_list:
        already_created = Pickup.objects.filter(warehouse=ordered_product.order.seller_shop,
                                                pickup_type="Order",
                                                pickup_type_id=ordered_product.order.order_no).last()
        if not already_created:
            info_logger.info("WMS Migration : pickup data generation : shipment Id{}".format(ordered_product.id))
            generate_order_data_for_order(ordered_product.order)
            shipment_basic_entry(ordered_product)
            shipment_picked_entry(ordered_product)
            if ordered_product.shipment_status == 'OUT_FOR_DELIVERY':
                shipment_shipped_entry(ordered_product)

def create_shipment_data_return():
    shipment_status = ['FULLY_RETURNED_AND_COMPLETED','PARTIALLY_DELIVERED_AND_COMPLETED','READY_TO_DISPATCH','FULLY_DELIVERED_AND_COMPLETED']
    ordered_product_list = OrderedProduct.objects.filter(shipment_status__in=shipment_status, created_at__gt=start_time)
    print(ordered_product_list)
    info_logger.info("WMS Migration : total shipments found {}".format(ordered_product_list.count()))
    for ordered_product in ordered_product_list:
        already_created = Pickup.objects.filter(warehouse=ordered_product.order.seller_shop,
                                                pickup_type="Order",
                                                pickup_type_id=ordered_product.order.order_no).last()
        if not already_created:
            info_logger.info("WMS Migration : pickup data generation : shipment Id{}".format(ordered_product.id))
            generate_order_data_for_order(ordered_product.order)
            shipment_basic_entry(ordered_product)
            shipment_picked_entry(ordered_product)
            shipment_shipped_entry(ordered_product)


def order_reserve_release():
    """This script is for creating an entry in Warehosue and Warehouse internal inventory if
    Order reserve release transaction id and order number is not same"""
    with transaction.atomic():
        order_reserve_release = OrderReserveRelease.objects.all()
        for obj in order_reserve_release:
            if not obj.transaction_id is None:
                if obj.transaction_id != obj.warehouse_internal_inventory_release.transaction_id:
                    warehouse_product_reserved = WarehouseInventory.objects.filter(
                        warehouse=Shop.objects.get(id=obj.warehouse.id),
                        sku__id=obj.sku.id,
                        inventory_state__inventory_state='reserved').last()
                    if warehouse_product_reserved:
                        reserved_qty = warehouse_product_reserved.quantity
                        warehouse_product_reserved.quantity = reserved_qty - obj.warehouse_internal_inventory_reserve.quantity
                        warehouse_product_reserved.save()

                    warehouse_product_ordered = WarehouseInventory.objects.filter(
                        warehouse=Shop.objects.get(id=obj.warehouse.id),
                        sku__id=obj.sku.id,
                        inventory_type__inventory_type='normal',
                        inventory_state__inventory_state='ordered').last()
                    if warehouse_product_ordered:
                        available_qty = warehouse_product_ordered.quantity
                        warehouse_product_ordered.quantity = available_qty + obj.warehouse_internal_inventory_reserve.quantity
                        warehouse_product_ordered.save()
                    else:
                        WarehouseInventory.objects.create(warehouse=Shop.objects.get(id=obj.warehouse.id),
                                                          sku=Product.objects.get(id=obj.sku.id),
                                                          inventory_state=InventoryState.objects.filter(
                                                              inventory_state='ordered').last(),
                                                          quantity=reserved_qty, in_stock=True,
                                                          inventory_type=InventoryType.objects.filter(
                                                              inventory_type='normal').last())
                    WarehouseInternalInventoryChange.objects.create(warehouse=Shop.objects.get(id=obj.warehouse.id),
                                                                    sku=Product.objects.get(id=obj.sku.id),
                                                                    transaction_type='ordered',
                                                                    transaction_id=obj.transaction_id,
                                                                    initial_type=InventoryType.objects.filter(
                                                                        inventory_type='normal').last(),
                                                                    final_type=InventoryType.objects.filter(
                                                                        inventory_type='normal').last(),
                                                                    initial_stage=InventoryState.objects.filter(
                                                                        inventory_state='reserved').last(),
                                                                    final_stage=InventoryState.objects.filter(
                                                                        inventory_state='ordered').last(),
                                                                    quantity=obj.warehouse_internal_inventory_reserve.quantity)
                    order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=Shop.objects.get(id=obj.warehouse.id),
                                                                           sku=Product.objects.get(
                                                                               id=obj.sku.id),
                                                                           transaction_id=obj.transaction_id)
                    order_reserve_obj.update(
                        warehouse_internal_inventory_release=WarehouseInternalInventoryChange.objects.filter(
                            transaction_id=obj.transaction_id, transaction_type='ordered').last(),
                        release_time=datetime.now())



