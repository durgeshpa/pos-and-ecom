import logging
from retailer_to_sp.models import OrderedProduct
from .models import (Bin, BinInventory, Putaway, PutawayBinInventory, Pickup, WarehouseInventory,
                     InventoryState, InventoryType, WarehouseInternalInventoryChange, In, PickupBinInventory,
                     BinInternalInventoryChange, StockMovementCSVUpload, StockCorrectionChange, OrderReserveRelease)


from shops.models import Shop
from django.db.models import Sum, Q
import functools
import json
from celery.task import task
from products.models import Product, ProductPrice
from datetime import datetime




type_choices = {
    'normal': 'normal',
    'expired': 'expired',
    'damaged': 'damaged',
    'discarded': 'discarded',
    'disposed': 'disposed'}

state_choices = {
     'available': 'available',
     'reserved' :'reserved',
     'shipped' : 'shipped'
}


class CommonBinFunctions(object):

    @classmethod
    def create_bin(cls, warehouse, bin_id, bin_type, is_active):
        bin_obj = Bin.objects.create(warehouse=warehouse, bin_id=bin_id, bin_type=bin_type, is_active=is_active)
        return bin_obj

    @classmethod
    def get_filtered_bins(cls, **kwargs):
        bins = Bin.objects.filter(**kwargs)
        return bins


# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

class PutawayCommonFunctions(object):

    @classmethod
    def create_putaway(cls, warehouse, putaway_type, putaway_type_id, sku, batch_id, quantity, putaway_quantity):
        if warehouse.shop_type.shop_type=='sp':
            putaway_obj = Putaway.objects.create(warehouse=warehouse, putaway_type=putaway_type, putaway_type_id=putaway_type_id, sku=sku,
                                   batch_id=batch_id, quantity=quantity, putaway_quantity=putaway_quantity)
            return putaway_obj

    @classmethod
    def get_filtered_putaways(cls, **kwargs):
        putaway_data = Putaway.objects.filter(**kwargs)
        return putaway_data

    @classmethod
    def get_available_qty_for_batch(cls, warehouse_id, sku_id, batch_id):
        batches = Putaway.objects.filter(Q(warehouse__id=warehouse_id),
                                              Q(sku__id=sku_id),
                                              Q(batch_id=batch_id))
        if batches.exists():
            return batches.aggregate(total=Sum('putaway_quantity')).get('total')
        else:
            return 0


class InCommonFunctions(object):

    @classmethod
    def create_in(cls, warehouse, in_type, in_type_id, sku, batch_id, quantity, putaway_quantity):
        if warehouse.shop_type.shop_type == 'sp':
            in_obj = In.objects.create(warehouse=warehouse, in_type=in_type, in_type_id=in_type_id, sku=sku,
                                       batch_id=batch_id, quantity=quantity)
            PutawayCommonFunctions.create_putaway(in_obj.warehouse, in_obj.in_type, in_obj.id, in_obj.sku,
                                                  in_obj.batch_id, in_obj.quantity, putaway_quantity)
            return in_obj

    @classmethod
    def get_filtered_in(cls, **kwargs):
        in_data = In.objects.filter(**kwargs)
        return in_data


class CommonBinInventoryFunctions(object):

    @classmethod
    def update_or_create_bin_inventory(cls, warehouse, bin, sku, batch_id, inventory_type, quantity, in_stock):

        bin_inv_obj = BinInventory.objects.filter(warehouse=warehouse, bin__bin_id=bin, sku=sku, batch_id=batch_id,
                                                  inventory_type=inventory_type, in_stock=in_stock).last()
        if bin_inv_obj:
            bin_quantity = bin_inv_obj.quantity
            final_quantity = bin_quantity + quantity
            bin_inv_obj.quantity = final_quantity
            bin_inv_obj.save()
        else:
            BinInventory.objects.get_or_create(warehouse=warehouse, bin=bin, sku=sku, batch_id=batch_id,
                                        inventory_type=inventory_type, quantity=quantity, in_stock=in_stock)


    @classmethod
    def create_bin_inventory(cls, warehouse, bin, sku, batch_id, inventory_type, quantity, in_stock):
        BinInventory.objects.get_or_create(warehouse=warehouse, bin=bin, sku=sku, batch_id=batch_id,
                                    inventory_type=inventory_type, quantity=quantity, in_stock=in_stock)

    @classmethod
    def filter_bin_inventory(cls, warehouse, sku, batch_id, bin_obj, inventory_type):
        return BinInventory.objects.filter(warehouse=warehouse, sku=sku, batch_id=batch_id, bin=bin_obj,
                                           inventory_type__inventory_type=inventory_type)

    @classmethod
    def get_filtered_bin_inventory(cls, **kwargs):
        bin_inv_data = BinInventory.objects.filter(**kwargs)
        return bin_inv_data


class CommonPickupFunctions(object):

    @classmethod
    def create_pickup_entry(cls, warehouse, pickup_type, pickup_type_id, sku, quantity, status):
        Pickup.objects.create(warehouse=warehouse, pickup_type=pickup_type, pickup_type_id=pickup_type_id, sku=sku, quantity=quantity, status=status)

    @classmethod
    def get_filtered_pickup(cls, **kwargs):
        pickup_data = Pickup.objects.filter(**kwargs)
        return pickup_data


class CommonInventoryStateFunctions(object):

    @classmethod
    def filter_inventory_state(cls, **kwargs):
        inv_state = InventoryState.objects.filter(**kwargs)
        return inv_state


class CommonWarehouseInventoryFunctions(object):

    @classmethod
    def create_warehouse_inventory(cls, warehouse, sku, inventory_state,inventory_type,quantity,in_stock):
        WarehouseInventory.objects.update_or_create(warehouse=warehouse, sku=sku,
                                                    inventory_state=InventoryState.objects.filter(inventory_state=inventory_state).last(),
                                                    defaults={
                                                             'inventory_type': InventoryType.objects.filter(inventory_type=inventory_type).last(),
                                                             'inventory_state':InventoryState.objects.filter(inventory_state=inventory_state).last(),
                                                             'quantity':quantity,
                                                             'in_stock': in_stock})

    @classmethod
    def filtered_warehouse_inventory_items(cls, **kwargs):
        inven_items = WarehouseInventory.objects.filter(**kwargs)
        return inven_items

class CommonPickBinInvFunction(object):

    @classmethod
    def create_pick_bin_inventory(cls,warehouse, pickup, batch_id, bin, quantity, pickup_quantity):
        PickupBinInventory.objects.create(warehouse=warehouse, pickup=pickup, batch_id=batch_id, bin=bin, quantity=quantity, pickup_quantity=pickup_quantity)


    @classmethod
    def get_filtered_pick_bin_inv(cls, **kwargs):
        pick_bin_inv = PickupBinInventory.objects.filter(**kwargs)
        return pick_bin_inv


def stock_decorator(wid, skuid):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ava = BinInventory.get_filtered_bin_inventories(warehouse__id=wid, sku__id=skuid)
            print(ava)
            return func(*args, **kwargs)
        return wrapper
    return actual_decorator


def get_brand_in_shop_stock(shop_id, brand):
    shop_stock = WarehouseInventory.objects.filter(
        Q(warehouse__id=shop_id),
        Q(quantity__gt=0),
        Q(sku__product_brand__brand_parent=brand))

    return shop_stock


def get_stock(shop):
    # For getting available stock of a particular warehouse
    """:param shop:
       :return: """
    return WarehouseInventory.objects.filter(
        Q(warehouse=shop),
        Q(quantity__gt=0),
        Q(inventory_state=InventoryState.objects.filter(inventory_state='available').last()),
        Q(in_stock='t')
    )


def get_product_stock(shop, sku):
    """:param shop:
      :param sku:
      :return: """
    return WarehouseInventory.objects.filter(
            Q(sku=sku),
            Q(warehouse=shop),
            Q(quantity__gt=0),
            Q(inventory_state=InventoryState.objects.filter(inventory_state='available').last()),
            Q(in_stock='t')
    )


def get_warehouse_product_availability(sku_id, shop_id=False):
    # For getting stock of a sku for a particular warehouse when shop_id is given else stock of sku for all warehouses
    """
    :param shop_id:
    :param sku_id:
    :return:
    """

    if shop_id:
        product_availability = WarehouseInventory.objects.filter(
            Q(sku__id=sku_id),
            Q(warehouse__id=shop_id),
            Q(quantity__gt=0),
            Q(inventory_state=InventoryState.objects.filter(inventory_state='available').last()),
            Q(in_stock='t')
        ).aggregate(total=Sum('quantity')).get('total')

        return product_availability

    else:
        product_availability = WarehouseInventory.objects.filter(
            Q(sku__id=sku_id),
            Q(quantity__gt=0),
            Q(inventory_state=InventoryState.objects.filter(inventory_state='available').last()),
            Q(in_stock='t')
        ).aggregate(total=Sum('quantity')).get('total')

        return product_availability


class OrderManagement(object):

    @classmethod
    @task
    def create_reserved_order(cls,reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        products = params['products']
        transaction_type = params['transaction_type']
        print("et")

        for prod_id, ordered_qty in products.items():
            WarehouseInventory.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                              sku=Product.objects.get(id=int(prod_id)),
                                              inventory_type=InventoryType.objects.filter(inventory_type='normal').last(),
                                              inventory_state=InventoryState.objects.filter(inventory_state='reserved').last(),
                                              quantity=ordered_qty, in_stock='t')
            win = WarehouseInventory.objects.filter(sku__id=int(prod_id), quantity__gt=0,
                                                    inventory_state__inventory_state='available').order_by('created_at')
            WarehouseInternalInventoryChange.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                    sku=Product.objects.get(id=int(prod_id)),
                                                    transaction_type=transaction_type,
                                                    transaction_id=transaction_id, initial_stage=InventoryState.objects.filter(inventory_state='available').last(),
                                                    final_stage=InventoryState.objects.filter(inventory_state='reserved').last(), quantity=ordered_qty)
            OrderReserveRelease.objects.create(warehouse=Shop.objects.get(id=shop_id), sku=Product.objects.get(id=int(prod_id)),warehouse_internal_inventory_reserve=WarehouseInternalInventoryChange.objects.all().last(),
                                               reserved_time=WarehouseInternalInventoryChange.objects.all().last().created_at)

            for k in win:
                wu = WarehouseInventory.objects.filter(id=k.id)
                qty = wu.last().quantity
                if ordered_qty == 0:
                    break
                if ordered_qty >= qty:
                    remain = 0
                    ordered_qty = ordered_qty - qty
                    wu.update(quantity=remain)
                else:
                    qty = qty - ordered_qty
                    wu.update(quantity=qty)
                    ordered_qty = 0

    @classmethod
    @task
    def release_blocking(cls, reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        transaction_type = params['transaction_type']
        order_status = params['order_status']
        common_for_release(sku_id, shop_id, transaction_type, transaction_id, order_status)

class InternalInventoryChange(object):
    @classmethod
    def create_bin_internal_inventory_change(cls, shop_id, sku, batch_id, bin_id, final_bin_id, initial_type,
                                             final_type, quantity, inventory_csv):
        """

        :param shop_id: shop id
        :param sku: sku id
        :param batch_id: batch id
        :param bin_id: initial bin id
        :param final_bin_id: final bin id
        :param initial_type: initial inventory type
        :param final_type: final inventory type
        :param quantity: quantity
        :param inventory_csv: stock movement csv obj
        :return: queryset
        """
        try:
            BinInternalInventoryChange.objects.create(warehouse_id=shop_id, sku=Product.objects.get(product_sku=sku),
                                                      batch_id=batch_id,
                                                      initial_bin=Bin.objects.get(bin_id=bin_id),
                                                      final_bin=Bin.objects.get(bin_id=final_bin_id),
                                                      initial_inventory_type=InventoryType.objects.get(
                                                          inventory_type=initial_type),
                                                      final_inventory_type=InventoryType.objects.get(
                                                          inventory_type=final_type),
                                                      quantity=quantity, inventory_csv=inventory_csv)
        except Exception as e:
            error_logger.error(e)


class WareHouseCommonFunction(object):
    @classmethod
    def update_or_create_warehouse_inventory(cls, warehouse, sku, inventory_state, inventory_type, quantity, in_stock):
        """

        :param warehouse: warehouse obj
        :param sku: sku obj
        :param inventory_state: type of inventory state
        :param inventory_type: type of inventory type
        :param quantity: quantity
        :param in_stock: in stock
        :return:
        """
        WarehouseInventory.objects.update_or_create(warehouse=warehouse, sku=sku,
                                                    inventory_type__inventory_type=InventoryType.objects.get(inventory_type=inventory_type),
                                                    inventory_state__inventory_state=InventoryState.objects.get(inventory_state=inventory_state),
                                                    defaults={'quantity': quantity, 'in_stock': in_stock})

    @classmethod
    def create_warehouse_inventory(cls, warehouse, sku, inventory_type, inventory_state, quantity, in_stock):
        """

        :param warehouse: warehouse obj
        :param sku: sku obj
        :param inventory_type: type of inventory type
        :param inventory_state: type of inventory state
        :param quantity: quantity
        :param in_stock: in stock
        :return:
        """
        WarehouseInventory.objects.get_or_create(warehouse=warehouse, sku=sku,
                                                 inventory_type=inventory_type, inventory_state=inventory_state,
                                                 quantity=quantity, in_stock=in_stock)

    @classmethod
    def filter_warehouse_inventory(cls, warehouse, sku, inventory_state, inventory_type):
        """

        :param warehouse: warehouse obj
        :param sku: sku obj
        :param inventory_state: type of inventory state
        :param inventory_type: type of inventory type
        :return:
        """
        return WarehouseInventory.objects.filter(warehouse=warehouse, sku=sku,
                                                 inventory_type__inventory_type=InventoryType.objects.get(inventory_type=inventory_type),
                                                 inventory_state__inventory_state=InventoryState.objects.get(inventory_state=inventory_state))


class InternalWarehouseChange(object):
    @classmethod
    def create_warehouse_inventory_change(cls, warehouse, sku, transaction_type, transaction_id, initial_stage,
                                          final_stage, inventory_type, quantity, inventory_csv):
        """

        :param warehouse: warehouse obj
        :param sku: sku obj
        :param transaction_type: type of transaction
        :param transaction_id: transaction id
        :param initial_stage: initial stage obj
        :param final_stage: final stage obj
        :param inventory_type: inventory type obj
        :param quantity: quantity
        :param inventory_csv: stock movement csv obj
        :return: queryset
        """
        try:
            WarehouseInternalInventoryChange.objects.create(warehouse_id=warehouse,
                                                            sku=sku, transaction_type=transaction_type,
                                                            transaction_id=transaction_id, initial_stage=initial_stage,
                                                            final_stage=final_stage, quantity=quantity,
                                                            inventory_type=inventory_type, inventory_csv=inventory_csv)
        except Exception as e:
            error_logger.error(e)


class InternalStockCorrectionChange(object):
    @classmethod
    def create_stock_inventory_change(cls, warehouse, stock_sku, batch_id, stock_bin_id, correction_type,
                                      quantity, inventory_csv):
        """

        :param warehouse: warehouse obj
        :param stock_sku: sku obj
        :param batch_id: batch obj
        :param stock_bin_id: bin obj
        :param correction_type: type of correction
        :param quantity: quantity
        :param inventory_csv: stock movement csv obj
        :return: queryset
        """
        try:
            StockCorrectionChange.objects.create(warehouse=warehouse,
                                                            stock_sku=stock_sku, batch_id=batch_id,
                                                            stock_bin_id=stock_bin_id, correction_type=correction_type,
                                                            quantity=quantity, inventory_csv=inventory_csv)
        except Exception as e:
            error_logger.error(e)


class StockMovementCSV(object):
    @classmethod
    def create_stock_movement_csv(cls, uploaded_by, upload_csv, inventory_movement_type):
        """

        :param uploaded_by: User object
        :param upload_csv: File object
        :param inventory_movement_type: type of movement
        :return: queryset of stock movement csv
        """
        try:
            stock_movement_csv_object = StockMovementCSVUpload.objects.get_or_create(uploaded_by=uploaded_by,
                                                                                     upload_csv=upload_csv,
                                                                                     inventory_movement_type=inventory_movement_type,)

            return stock_movement_csv_object

        except Exception as e:
            error_logger.error(e)


def updating_tables_on_putaway(sh, bin_id, put_away, batch_id, inv_type,inv_state, t, val):
    CommonBinInventoryFunctions.update_or_create_bin_inventory(sh, Bin.objects.filter(bin_id=bin_id).last(),
                                                               put_away.last().sku, batch_id,
                                                               InventoryType.objects.filter(
                                                                   inventory_type=inv_type).last(), val, t)
    PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(),
                                       bin=CommonBinInventoryFunctions.get_filtered_bin_inventory().last(),putaway_quantity=val)
    CommonWarehouseInventoryFunctions.create_warehouse_inventory(sh, put_away.last().sku,
                                                                 CommonInventoryStateFunctions.filter_inventory_state(inventory_state=inv_state).last(),
                                                                 InventoryType.objects.filter(inventory_type=inv_type).last(),
                                                                 BinInventory.available_qty(sh.id, put_away.last().sku.id), t)


def common_for_release(prod_list, shop_id, transaction_type, transaction_id, order_status):
    for prod in prod_list:
        ordered_product_reserved = WarehouseInventory.objects.filter(sku__id=prod, inventory_state__inventory_state='reserved')
        if ordered_product_reserved.exists():
            reserved_qty = ordered_product_reserved.last().quantity
            ordered_id = ordered_product_reserved.last().id
            wim = WarehouseInventory.objects.filter(sku__id=prod,inventory_state__inventory_state='available')
            available_qty = wim.last().quantity
            if order_status == 'ordered':
                wim.update(quantity=available_qty)
            else:
                wim.update(quantity=available_qty+reserved_qty)
            WarehouseInventory.objects.filter(id=ordered_id).update(quantity=0)
            warehouse_details = WarehouseInternalInventoryChange.objects.filter(transaction_id=transaction_id,
                                                                           transaction_type='reserved',
                                                                           status=True)
            # update those Ware house inventory which status is True
            warehouse_details.update(status=False)

            WarehouseInternalInventoryChange.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                            sku=Product.objects.get(id=prod),
                                                            transaction_type=transaction_type,
                                                            transaction_id=transaction_id,
                                                            initial_stage=InventoryState.objects.filter(inventory_state='reserved').last(), final_stage=InventoryState.objects.filter(inventory_state=order_status).last(),
                                                            quantity=reserved_qty)
            order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=Shop.objects.get(id=shop_id),
                                                                             sku=Product.objects.get(id=prod),
                                                                             warehouse_internal_inventory_release=None)
            order_reserve_obj.update(warehouse_internal_inventory_release = WarehouseInternalInventoryChange.objects.all().last(),
                                     release_time= datetime.now())


def cancel_order(instance):
    """

    :param instance: order instance
    :return:
    """
    ware_house_internal = WarehouseInternalInventoryChange.objects.filter(
        transaction_id=instance.order_no, final_stage=4, transaction_type='ordered')
    sku_id = [p.sku.id for p in ware_house_internal]
    quantity = [p.quantity for p in ware_house_internal]
    for prod, qty in zip(sku_id, quantity):
        wim = WarehouseInventory.objects.filter(sku__id=prod,
                                                inventory_state__inventory_state='available',
                                                inventory_type__inventory_type='normal')
        wim_quantity = wim[0].quantity
        wim.update(quantity=wim_quantity + qty)
        transaction_type = 'canceled'
        initial_stage = 'ordered'
        final_stage = 'canceled'
        inventory_type = 'normal'
        WarehouseInternalInventoryChange.objects.create(warehouse=wim[0].warehouse,
                                                        sku=wim[0].sku,
                                                        transaction_type=transaction_type,
                                                        transaction_id=ware_house_internal[0].transaction_id,
                                                        initial_stage=InventoryState.objects.get(inventory_state=initial_stage),
                                                        final_stage=InventoryState.objects.get(inventory_state=final_stage),
                                                        inventory_type=InventoryType.objects.get(inventory_type=inventory_type),
                                                        quantity=qty)


def cancel_order_with_pick(instance):
    """

    :param instance: order instance
    :return:

    """
    # order_obj = OrderedProduct.objects.filter(order=instance, shipment_status=OrderedProduct.READY_TO_SHIP)
    # if order_obj.exists():
    #     order_obj.update(shipment_status='CANCELLED')
    pickup_object = PickupBinInventory.objects.filter(pickup__pickup_type_id=instance.order_no)
    for pickup in pickup_object:
        # pickup_bin_inventory_object = PickupBinInventory.objects.filter(pickup=pickup)

        pick_up_bin_quantity = pickup.pickup_quantity

        # Bin Model Update
        bin_inv_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(bin__bin_id=pickup.bin.bin.bin_id,
                                                                             sku__id=pickup.pickup.sku.id,
                                                                             batch_id=pickup.batch_id,
                                                                             quantity__gt=0)
        bin_inv_qty = bin_inv_obj.last().quantity
        bin_inv_obj.update(quantity=bin_inv_qty + pick_up_bin_quantity)

        # Update Pickup and PickUp Bin Inventory
        pick_up_pickup_quantity = 0
        pickup.pickup_quantity = pick_up_pickup_quantity
        pickup.save()
        pick_obj = Pickup.objects.filter(pickup_type_id=instance.order_no)
        pick_obj.update(pickup_quantity=0)
