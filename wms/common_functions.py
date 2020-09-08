# python imports
import functools
import json
import logging
from datetime import datetime
from celery.task import task

# django imports
from django import forms
from django.db.models import Sum, Q
from django.db import transaction

# app imports
from .models import (Bin, BinInventory, Putaway, PutawayBinInventory, Pickup, WarehouseInventory,
                     InventoryState, InventoryType, WarehouseInternalInventoryChange, In, PickupBinInventory,
                     BinInternalInventoryChange, StockMovementCSVUpload, StockCorrectionChange, OrderReserveRelease,
                     Audit, Out)

import retailer_to_sp.models

from shops.models import Shop
from products.models import Product

# Logger

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

type_choices = {
    'normal': 'normal',
    'expired': 'expired',
    'damaged': 'damaged',
    'discarded': 'discarded',
    'disposed': 'disposed',
    'missing': 'missing'
}

state_choices = {
    'available': 'available',
    'reserved': 'reserved',
    'shipped': 'shipped',
    'ordered': 'ordered',
    'canceled': 'canceled'
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


class PutawayCommonFunctions(object):

    @classmethod
    def create_putaway(cls, warehouse, putaway_type, putaway_type_id, sku, batch_id, quantity, putaway_quantity):
        if warehouse.shop_type.shop_type == 'sp':
            putaway_obj = Putaway.objects.create(warehouse=warehouse, putaway_type=putaway_type,
                                                 putaway_type_id=putaway_type_id, sku=sku,
                                                 batch_id=batch_id, quantity=quantity,
                                                 putaway_quantity=putaway_quantity)
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


class OutCommonFunctions(object):

    @classmethod
    def create_out(cls, warehouse, out_type, out_type_id, sku, batch_id, quantity):
        if warehouse.shop_type.shop_type == 'sp':
            in_obj = Out.objects.create(warehouse=warehouse, out_type=out_type, out_type_id=out_type_id, sku=sku,
                                        batch_id=batch_id, quantity=quantity)
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
        Pickup.objects.create(warehouse=warehouse, pickup_type=pickup_type, pickup_type_id=pickup_type_id, sku=sku,
                              quantity=quantity, status=status)

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
    def create_warehouse_inventory(cls, warehouse, sku, inventory_type, inventory_state, quantity, in_stock):

        ware_house_inventory_obj = WarehouseInventory.objects.filter(
            warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                inventory_state=inventory_state).last(), inventory_type=InventoryType.objects.filter(
                inventory_type=inventory_type).last(), in_stock=in_stock).last()

        if ware_house_inventory_obj:
            ware_house_quantity = quantity + ware_house_inventory_obj.quantity
            ware_house_inventory_obj.quantity = ware_house_quantity
            ware_house_inventory_obj.save()
        else:
            WarehouseInventory.objects.get_or_create(
                warehouse=warehouse,
                sku=sku,
                inventory_state=InventoryState.objects.filter(inventory_state=inventory_state).last(),
                inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(),
                in_stock=in_stock, quantity=quantity)

    @classmethod
    def filtered_warehouse_inventory_items(cls, **kwargs):
        inven_items = WarehouseInventory.objects.filter(**kwargs)
        return inven_items


class CommonPickBinInvFunction(object):

    @classmethod
    def create_pick_bin_inventory(cls, warehouse, pickup, batch_id, bin, quantity, pickup_quantity):
        PickupBinInventory.objects.create(warehouse=warehouse, pickup=pickup, batch_id=batch_id, bin=bin,
                                          quantity=quantity, pickup_quantity=pickup_quantity)

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
        Q(inventory_type=InventoryType.objects.filter(inventory_type='normal').last()),
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
        Q(inventory_type=InventoryType.objects.filter(inventory_type='normal').last()),
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
    def create_reserved_order(cls, reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        products = params['products']
        transaction_type = params['transaction_type']

        for prod_id, ordered_qty in products.items():
            warehouse_obj = WarehouseInventory.objects.filter(warehouse=Shop.objects.get(id=shop_id),
                                                              sku=Product.objects.get(id=int(prod_id)),
                                                              inventory_type=InventoryType.objects.filter(
                                                                  inventory_type='normal').last(),
                                                              inventory_state=InventoryState.objects.filter(
                                                                  inventory_state='reserved').last())
            if warehouse_obj.exists():
                w_obj = warehouse_obj.last()
                w_obj.quantity = ordered_qty + w_obj.quantity
                w_obj.save()
            else:
                WarehouseInventory.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                  sku=Product.objects.get(id=int(prod_id)),
                                                  inventory_type=InventoryType.objects.filter(
                                                      inventory_type='normal').last(),
                                                  inventory_state=InventoryState.objects.filter(
                                                      inventory_state='reserved').last(),
                                                  quantity=ordered_qty, in_stock='t')
            win = WarehouseInventory.objects.filter(sku__id=int(prod_id), quantity__gt=0,
                                                    inventory_state__inventory_state='available').order_by('created_at')
            WarehouseInternalInventoryChange.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                            sku=Product.objects.get(id=int(prod_id)),
                                                            transaction_type=transaction_type,
                                                            transaction_id=transaction_id,
                                                            initial_type=InventoryType.objects.filter(
                                                                inventory_type='normal').last(),
                                                            final_type=InventoryType.objects.filter(
                                                                inventory_type='normal').last(),
                                                            initial_stage=InventoryState.objects.filter(
                                                                inventory_state='available').last(),
                                                            final_stage=InventoryState.objects.filter(
                                                                inventory_state='reserved').last(),
                                                            quantity=ordered_qty)
            OrderReserveRelease.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                               sku=Product.objects.get(id=int(prod_id)),
                                               warehouse_internal_inventory_reserve=WarehouseInternalInventoryChange.objects.all().last(),
                                               reserved_time=WarehouseInternalInventoryChange.objects.all().last().created_at)

            for k in win:
                wu = WarehouseInventory.objects.filter(id=k.id)
                qty = wu.last().quantity
                if ordered_qty == 0:
                    break
                if ordered_qty >= qty:
                    remain = 0
                    ordered_qty = ordered_qty - qty
                    ware_obj = wu.last()
                    ware_obj.quantity = remain
                    ware_obj.save()
                    # wu.update(quantity=remain)
                else:
                    qty = qty - ordered_qty
                    ware_obj = wu.last()
                    ware_obj.quantity = qty
                    ware_obj.save()
                    # wu.update(quantity=qty)
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
    def create_bin_internal_inventory_change(cls, shop_id, sku, batch_id, final_bin_id, initial_type,
                                             final_type, transaction_type, transaction_id, quantity):
        """

        :param shop_id:
        :param sku:
        :param batch_id:
        :param initial_bin:
        :param final_bin_id:
        :param initial_type:
        :param final_type:
        :param transaction_type:
        :param transaction_id:
        :param quantity:
        :param inventory_csv:
        :return:
        """
        try:
            BinInternalInventoryChange.objects.create(warehouse_id=shop_id.id, sku=sku,
                                                      batch_id=batch_id,
                                                      final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                warehouse=Shop.objects.get(
                                                                                    id=shop_id.id)),
                                                      initial_inventory_type=initial_type,
                                                      final_inventory_type=final_type,
                                                      transaction_type=transaction_type,
                                                      transaction_id=transaction_id,
                                                      quantity=quantity)
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
                                                    inventory_type__inventory_type=InventoryType.objects.get(
                                                        inventory_type=inventory_type),
                                                    inventory_state__inventory_state=InventoryState.objects.get(
                                                        inventory_state=inventory_state),
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
                                                 inventory_type__inventory_type=InventoryType.objects.get(
                                                     inventory_type=inventory_type),
                                                 inventory_state__inventory_state=InventoryState.objects.get(
                                                     inventory_state=inventory_state))


class InternalWarehouseChange(object):
    @classmethod
    def create_warehouse_inventory_change(cls, warehouse, sku, transaction_type, transaction_id, initial_type,
                                          initial_stage,
                                          final_type, final_stage, quantity, inventory_csv):
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
            WarehouseInternalInventoryChange.objects.create(warehouse=warehouse,
                                                            sku=sku, transaction_type=transaction_type,
                                                            transaction_id=transaction_id, initial_stage=initial_stage,
                                                            final_stage=final_stage, quantity=quantity,
                                                            initial_type=initial_type, final_type=final_type,
                                                            inventory_csv=inventory_csv)
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
                                                                                     inventory_movement_type=inventory_movement_type, )

            return stock_movement_csv_object

        except Exception as e:
            error_logger.error(e)


def updating_tables_on_putaway(sh, bin_id, put_away, batch_id, inv_type, inv_state, t, val, put_away_status, pu):
    """

    :param sh:
    :param bin_id:
    :param put_away:
    :param batch_id:
    :param inv_type:
    :param inv_state:
    :param t:
    :param val:
    :param put_away_status:
    :param pu:
    :return:
    """
    bin_inventory_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(warehouse=sh, bin=Bin.objects.filter(
        bin_id=bin_id).last(),
                                                                               sku=put_away.last().sku,
                                                                               batch_id=batch_id,
                                                                               inventory_type=InventoryType.objects.filter(
                                                                                   inventory_type=inv_type).last(),
                                                                               in_stock=t)
    if bin_inventory_obj.exists():
        bin_inventory_obj = bin_inventory_obj.last()
        bin_quantity = val + bin_inventory_obj.quantity
        bin_inventory_obj.quantity = bin_quantity
        bin_inventory_obj.save()
        CommonWarehouseInventoryFunctions.create_warehouse_inventory(sh, pu[0].sku, inv_type, inv_state, val,
                                                                     True)
    else:
        BinInventory.objects.create(warehouse=sh, bin=Bin.objects.filter(bin_id=bin_id).last(), sku=put_away.last().sku,
                                    batch_id=batch_id, inventory_type=InventoryType.objects.filter(
                inventory_type=inv_type).last(), quantity=val, in_stock=t)
        CommonWarehouseInventoryFunctions.create_warehouse_inventory(sh, pu[0].sku, inv_type, inv_state, val,
                                                                     True)

    if put_away_status is True:
        PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(),
                                           bin=CommonBinInventoryFunctions.get_filtered_bin_inventory().last(),
                                           putaway_quantity=val, putaway_status=True,
                                           sku=pu[0].sku, batch_id=pu[0].batch_id,
                                           putaway_type=pu[0].putaway_type)
    else:
        PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(),
                                           bin=CommonBinInventoryFunctions.get_filtered_bin_inventory().last(),
                                           putaway_quantity=val, putaway_status=False,
                                           sku=pu[0].sku, batch_id=pu[0].batch_id,
                                           putaway_type=pu[0].putaway_type)

    transaction_type = 'put_away_type'
    transaction_id = put_away[0].id
    initial_type = InventoryType.objects.filter(inventory_type='new').last(),
    initial_stage = InventoryState.objects.filter(inventory_state='new').last(),
    final_type = InventoryType.objects.filter(inventory_type='normal').last(),
    final_stage = InventoryState.objects.filter(inventory_state='available').last(),
    WareHouseInternalInventoryChange.create_warehouse_inventory_change(sh, pu[0].sku, transaction_type, transaction_id,
                                                                       initial_type[0], initial_stage[0],
                                                                       final_type[0], final_stage[0], val)

    final_bin_id = bin_id
    initial_type = InventoryType.objects.filter(inventory_type='new').last(),
    final_type = InventoryType.objects.filter(inventory_type='normal').last(),
    transaction_type = 'put_away_type'
    transaction_id = put_away[0].id
    quantity = val
    InternalInventoryChange.create_bin_internal_inventory_change(sh, pu[0].sku, batch_id, final_bin_id, initial_type[0],
                                                                 final_type[0], transaction_type,
                                                                 transaction_id, quantity)


def common_for_release(prod_list, shop_id, transaction_type, transaction_id, order_status):
    cart = retailer_to_sp.models.Cart.objects.get(order_id=transaction_id)
    for prod in prod_list:
        ordered_product_reserved = WarehouseInventory.objects.filter(sku__id=prod,
                                                                     inventory_state__inventory_state='reserved')
        if ordered_product_reserved.exists():
            reserved_qty = ordered_product_reserved.last().quantity
            if reserved_qty == 0:
                return
            ordered_id = ordered_product_reserved.last().id
            wim = WarehouseInventory.objects.filter(sku__id=prod, inventory_type__inventory_type='normal',
                                                    inventory_state__inventory_state='available')
            available_qty = wim.last().quantity
            if order_status == 'ordered':
                ware_obj = wim.last()
                ware_obj.quantity = available_qty
                ware_obj.save()
                # wim.update(quantity=available_qty)
                order_ware = WarehouseInventory.objects.filter(sku__id=prod,
                                                               inventory_state=InventoryState.objects.filter(
                                                                   inventory_state='ordered').last()).last()
                if order_ware:
                    qty = order_ware.quantity
                    for i in cart.rt_cart_list.filter(cart_product=prod):
                        order_ware.quantity = qty + i.no_of_pieces
                        order_ware.save()
                else:
                    WarehouseInventory.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                      sku=Product.objects.get(id=prod),
                                                      inventory_state=InventoryState.objects.filter(
                                                          inventory_state='ordered').last(), quantity=reserved_qty,
                                                      in_stock=True,
                                                      inventory_type=InventoryType.objects.filter(
                                                          inventory_type='normal').last()
                                                      )

                for i in cart.rt_cart_list.filter(cart_product=prod):
                    qty = WarehouseInventory.objects.filter(id=ordered_id, sku=i.cart_product).last().quantity
                    WarehouseInventory.objects.filter(id=ordered_id, sku=i.cart_product).update_or_create(
                        quantity=qty - i.no_of_pieces)
            else:
                for i in cart.rt_cart_list.filter(cart_product=prod):
                    ware_obj = wim.last()
                    ware_obj.quantity = (available_qty + i.no_of_pieces)
                    ware_obj.save()
                # wim.update(quantity=available_qty+reserved_qty)
                for i in cart.rt_cart_list.filter(cart_product=prod):
                    qty = WarehouseInventory.objects.filter(id=ordered_id, sku=i.cart_product).last().quantity
                    WarehouseInventory.objects.filter(id=ordered_id, sku=i.cart_product).update_or_create(
                        quantity=qty - i.no_of_pieces)
                # WarehouseInventory.objects.filter(id=ordered_id).update(quantity=0)
            warehouse_details = WarehouseInternalInventoryChange.objects.filter(transaction_id=transaction_id,
                                                                                transaction_type='reserved',
                                                                                status=True)
            # update those Ware house inventory which status is True
            warehouse_details.update(status=False)
            quant = [i.no_of_pieces for i in cart.rt_cart_list.filter(cart_product=prod)]
            quantity = lambda x: x[0]
            WarehouseInternalInventoryChange.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                            sku=Product.objects.get(id=prod),
                                                            transaction_type=transaction_type,
                                                            transaction_id=transaction_id,
                                                            initial_type=InventoryType.objects.filter(
                                                                inventory_type='normal').last(),
                                                            final_type=InventoryType.objects.filter(
                                                                inventory_type='normal').last(),
                                                            initial_stage=InventoryState.objects.filter(
                                                                inventory_state='reserved').last(),
                                                            final_stage=InventoryState.objects.filter(
                                                                inventory_state=order_status).last(),
                                                            quantity=quantity(quant))
            order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=Shop.objects.get(id=shop_id),
                                                                   sku=Product.objects.get(id=prod),
                                                                   warehouse_internal_inventory_release=None)
            order_reserve_obj.update(
                warehouse_internal_inventory_release=WarehouseInternalInventoryChange.objects.all().last(),
                release_time=datetime.now())


def cancel_order(instance):
    """

    :param instance: order instance
    :return:
    """
    # get the queryset object form warehouse internal inventory model
    ware_house_internal = WarehouseInternalInventoryChange.objects.filter(
        transaction_id=instance.order_no, final_stage=4, transaction_type='ordered')
    # fetch all sku
    sku_id = [p.sku.id for p in ware_house_internal]
    # fetch all quantity
    quantity = [p.quantity for p in ware_house_internal]
    # iterate over sku and quantity
    for prod, qty in zip(sku_id, quantity):
        # get the queryset from warehouse inventory model for normal and available
        wim = WarehouseInventory.objects.filter(sku__id=prod,
                                                inventory_state__inventory_state='available',
                                                inventory_type__inventory_type='normal')
        wim_quantity = wim[0].quantity
        wim.update(quantity=wim_quantity + qty)

        # get the queryset from warehouse inventory model for ordered and normal
        wim_ordered = WarehouseInventory.objects.filter(sku__id=prod,
                                                        inventory_state__inventory_state='ordered',
                                                        inventory_type__inventory_type='normal')
        wim_ordered_quantity = wim_ordered[0].quantity
        wim_ordered.update(quantity=wim_ordered_quantity - qty)
        # initialize the transaction type, initial stage, final stage and inventory type
        transaction_type = 'canceled'
        initial_type = 'normal'
        initial_stage = 'ordered'
        final_type = 'normal'
        final_stage = 'available'
        inventory_type = 'normal'
        # create the data in Warehouse internal inventory model
        WarehouseInternalInventoryChange.objects.create(warehouse=wim[0].warehouse,
                                                        sku=wim[0].sku,
                                                        transaction_type=transaction_type,
                                                        transaction_id=ware_house_internal[0].transaction_id,
                                                        initial_stage=InventoryState.objects.get(
                                                            inventory_state=initial_stage),
                                                        final_stage=InventoryState.objects.get(
                                                            inventory_state=final_stage),
                                                        initial_type=InventoryType.objects.get(
                                                            inventory_type=initial_type),
                                                        final_type=InventoryType.objects.get(inventory_type=final_type),
                                                        inventory_type=InventoryType.objects.get(
                                                            inventory_type=inventory_type),
                                                        quantity=qty)


# def cancel_order_for_warehouse(instance):
#     """
#
#     :param instance: order instance
#     :return:
#     """
#     # get the queryset object form warehouse internal inventory model
#     ware_house_internal = WarehouseInternalInventoryChange.objects.filter(
#         transaction_id=instance.order_no, final_stage=4, transaction_type='ordered')
#     # fetch all sku
#     sku_id = [p.sku.id for p in ware_house_internal]
#     # fetch all quantity
#     quantity = [p.quantity for p in ware_house_internal]
#     # iterate over sku and quantity
#     for prod, qty in zip(sku_id, quantity):
#         # get the queryset from warehouse inventory model
#         wim = WarehouseInventory.objects.filter(sku__id=prod,
#                                                 inventory_state__inventory_state='available',
#                                                 inventory_type__inventory_type='normal')
#         # initialize the transaction type, initial stage, final stage and inventory type
#         transaction_type = 'canceled'
#         initial_stage = 'ordered'
#         final_stage = 'canceled'
#         inventory_type = 'normal'
#         # create the data in Warehouse internal inventory model
#         WarehouseInternalInventoryChange.objects.create(warehouse=wim[0].warehouse,
#                                                         sku=wim[0].sku,
#                                                         transaction_type=transaction_type,
#                                                         transaction_id=ware_house_internal[0].transaction_id,
#                                                         initial_stage=InventoryState.objects.get(inventory_state=initial_stage),
#                                                             final_stage=InventoryState.objects.get(inventory_state=final_stage),
#                                                         inventory_type=InventoryType.objects.get(inventory_type=inventory_type),
#                                                         quantity=qty)


def cancel_order_with_pick(instance):
    """

    :param instance: order instance
    :return:

    """
    with transaction.atomic():
        # get the queryset object from Pickup Bin Inventory Model
        pickup_bin_object = PickupBinInventory.objects.filter(pickup__pickup_type_id=instance.order_no)
        # iterate over the PickupBin Inventory object
        for pickup_bin in pickup_bin_object:
            # if pick up status is pickup creation
            if (pickup_bin.pickup.status == 'pickup_creation') or (pickup_bin.pickup.status == 'picking_assigned'):
                put_away_object = Putaway.objects.filter(warehouse=pickup_bin.warehouse, putaway_type='CANCELLED',
                                                         putaway_type_id=instance.order_no, sku=pickup_bin.bin.sku,
                                                         batch_id=pickup_bin.batch_id,
                                                         )
                if put_away_object.exists():
                    quantity = put_away_object[0].quantity + pickup_bin.quantity
                    pick_up_bin_quantity = pickup_bin.quantity
                else:
                    quantity = pickup_bin.quantity
                    pick_up_bin_quantity = pickup_bin.quantity
                status = 'Order_Cancelled'
            elif pickup_bin.pickup.status == 'picking_complete':
                quantity = 0
                pick_up_bin_quantity = 0
                if instance.rt_order_order_product.all():
                    if (instance.rt_order_order_product.all()[0].shipment_status == 'READY_TO_SHIP') or \
                            (instance.rt_order_order_product.all()[0].shipment_status == 'READY_TO_DISPATCH'):
                        for pickup_order in pickup_bin.pickup.orderedproductbatch_set.all():
                            if pickup_bin.bin.id == pickup_order.bin.id:
                                put_away_object = Putaway.objects.filter(warehouse=pickup_bin.warehouse,
                                                                         putaway_type='CANCELLED',
                                                                         putaway_type_id=instance.order_no,
                                                                         sku=pickup_bin.bin.sku,
                                                                         batch_id=pickup_bin.batch_id,
                                                                         )
                                if put_away_object.exists():
                                    quantity = put_away_object[0].quantity + pickup_order.quantity
                                    pick_up_bin_quantity = pickup_order.quantity
                                else:
                                    quantity = pickup_order.quantity
                                    pick_up_bin_quantity = pickup_order.quantity
                        if quantity == 0 and pick_up_bin_quantity == 0:
                            continue
                        quantity = quantity
                        status = 'Shipment_Cancelled'
                        pick_up_bin_quantity = pick_up_bin_quantity
                    else:
                        put_away_object = Putaway.objects.filter(warehouse=pickup_bin.warehouse,
                                                                 putaway_type='CANCELLED',
                                                                 putaway_type_id=instance.order_no,
                                                                 sku=pickup_bin.bin.sku,
                                                                 batch_id=pickup_bin.batch_id,
                                                                 )
                        if put_away_object.exists():
                            quantity = put_away_object[0].quantity + pickup_bin.pickup_quantity
                            pick_up_bin_quantity = pickup_bin.pickup_quantity
                            status = 'Shipment_Cancelled'
                        else:
                            quantity = pickup_bin.pickup_quantity
                            pick_up_bin_quantity = pickup_bin.pickup_quantity
                            status = 'Shipment_Cancelled'
                else:
                    put_away_object = Putaway.objects.filter(warehouse=pickup_bin.warehouse, putaway_type='CANCELLED',
                                                             putaway_type_id=instance.order_no, sku=pickup_bin.bin.sku,
                                                             batch_id=pickup_bin.batch_id,
                                                             )
                    if put_away_object.exists():
                        quantity = put_away_object[0].quantity + pickup_bin.pickup_quantity
                        pick_up_bin_quantity = pickup_bin.pickup_quantity
                        status = 'Pickup_Cancelled'
                    else:
                        quantity = pickup_bin.pickup_quantity
                        pick_up_bin_quantity = pickup_bin.pickup_quantity
                        status = 'Pickup_Cancelled'

            # update or create put away model
            pu, _ = Putaway.objects.update_or_create(putaway_user=instance.last_modified_by,
                                                     warehouse=pickup_bin.warehouse, putaway_type='CANCELLED',
                                                     putaway_type_id=instance.order_no, sku=pickup_bin.bin.sku,
                                                     batch_id=pickup_bin.batch_id,
                                                     defaults={'quantity': quantity,
                                                               'putaway_quantity': 0})
            # update or create put away bin inventory model
            PutawayBinInventory.objects.update_or_create(warehouse=pickup_bin.warehouse, sku=pickup_bin.bin.sku,
                                                         batch_id=pickup_bin.batch_id, putaway_type=status,
                                                         putaway=pu, bin=pickup_bin.bin, putaway_status=False,
                                                         defaults={'putaway_quantity': pick_up_bin_quantity})
            # get the queryset filter from Pickup model
        pickup_obj = Pickup.objects.filter(pickup_type_id=instance.order_no)
        # iterate the pickup objects and set the status picking cancelled
        for obj in pickup_obj:
            obj.status = 'picking_cancelled'
            obj.save()


class AuditInventory(object):
    """This class is used for to store data in different models while audit file upload """

    @classmethod
    def audit_exist_batch_id(cls, data, key, value, audit_inventory_obj, batch_id):
        """

        :param data: list of csv data
        :param key: Inventory type
        :param value: Quantity
        :param audit_inventory_obj: object of Audit inventory Model
        :return:
        """
        # filter in Bin inventory table to get batch id for particular sku, warehouse and bin in
        # bin_inv = BinInventory.objects.filter(warehouse=data[0],
        #                                       bin=Bin.objects.filter(bin_id=data[4]).last(),
        #                                       sku=Product.objects.filter(
        #                                           product_sku=data[1][-17:]).last()).last()


        # call function to create and update Bin inventory for specific Inventory Type
        AuditInventory.update_or_create_bin_inventory_for_audit(data[0], data[4],
                                                                data[1][-17:],
                                                                batch_id,
                                                                InventoryType.objects.filter(
                                                                    inventory_type=key).last(),
                                                                value, True)

        # call function to create and update Ware House Inventory for specific Inventory Type
        AuditInventory.update_or_create_warehouse_inventory_for_audit(
            data[0], data[1][-17:],
            CommonInventoryStateFunctions.filter_inventory_state(inventory_state='available').last(),
            InventoryType.objects.filter(inventory_type=key).last(),
            BinInventory.available_qty_with_inventory_type(data[0], Product.objects.filter(
                product_sku=data[1][-17:]).last().id, InventoryType.objects.filter(
                inventory_type=key).last().id), True, batch_id, data[4])

        # call function to create and update Ware House Internal Inventory for specific Inventory Type
        transaction_type = 'audit_adjustment'
        AuditInventory.create_warehouse_inventory_change_for_audit(
            Shop.objects.get(id=data[0]).id, Product.objects.get(
                product_sku=data[1][-17:]), transaction_type, audit_inventory_obj[0].id,
            CommonInventoryStateFunctions.filter_inventory_state(inventory_state='available').last(),
            CommonInventoryStateFunctions.filter_inventory_state(inventory_state='available').last(),
            InventoryType.objects.filter(inventory_type=key).last(), value)

    @classmethod
    def update_or_create_bin_inventory_for_audit(cls, warehouse, bin_id, sku, batch_id, inventory_type, quantity,
                                                 in_stock):
        """

        :param warehouse:warehouse id
        :param bin_id: bin id
        :param sku: sku
        :param batch_id: batch id
        :param inventory_type: type of inventory
        :param quantity: quantity
        :param in_stock: True or False
        :return: None
        """

        # filter in Bin inventory model to check whether the combination of warehouse, bin id, sku id, batch and
        # inventory type is exist or not if it is found then update quantity otherwise create new data set in a model
        try:
            bin_inv_obj = BinInventory.objects.filter(warehouse=warehouse, bin__bin_id=bin_id, sku=sku,
                                                      batch_id=batch_id,
                                                      inventory_type=inventory_type, in_stock=in_stock).last()
            if bin_inv_obj:
                bin_inv_obj.quantity = quantity
                bin_inv_obj.save()
            else:
                BinInventory.objects.get_or_create(warehouse=Shop.objects.filter(id=warehouse)[0],
                                                   bin=Bin.objects.filter(bin_id=bin_id)[0],
                                                   sku=Product.objects.filter(product_sku=sku)[0], batch_id=batch_id,
                                                   inventory_type=inventory_type, quantity=quantity,
                                                   in_stock=in_stock)
        except:
            pass

    @classmethod
    def update_or_create_warehouse_inventory_for_audit(cls, warehouse, sku, inventory_state, inventory_type, quantity,
                                                       in_stock, batch_id, bin_id):
        """

        :param warehouse: warehouse
        :param sku: sku
        :param inventory_state: state of Inventory
        :param inventory_type: type of Inventory
        :param quantity: quantity
        :param in_stock: True otherwise False
        :return: None
        """
        # filter in Warehouse inventory model to check whether the combination of warehouse, sku id, inventory state,
        # inventory type is exist or not if it is found then update quantity otherwise create new data set in a model
        if inventory_type.inventory_type == 'normal':
            ware_house_inventory_obj = WarehouseInventory.objects.filter(
                warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                    inventory_state=inventory_state).last(), inventory_type=InventoryType.objects.filter(
                    inventory_type=inventory_type).last(), in_stock=in_stock).last()
            # get all quantity for same sku in warehouse except inventory type is normal
            all_ware_house_inventory_obj = BinInventory.objects.filter(warehouse=warehouse, bin__bin_id=bin_id, sku=sku,
                                                                       batch_id=batch_id, in_stock=in_stock)

            # check the object is exist or not
            if all_ware_house_inventory_obj.exists():
                all_ware_house_quantity = 0
                # get the quantity
                for in_ware_house in all_ware_house_inventory_obj:
                    all_ware_house_quantity = in_ware_house.quantity + all_ware_house_quantity
                if all_ware_house_quantity > ware_house_inventory_obj.quantity:
                    final_quantity = 0
                    reserved_inv_type_quantity = all_ware_house_quantity - ware_house_inventory_obj.quantity
                    ware_house_inventory_obj.quantity = final_quantity
                    ware_house_inventory_obj.save()
                    reserved_ware = WarehouseInventory.objects.filter(
                        warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                            inventory_state='reserved').last(), inventory_type=InventoryType.objects.filter(
                            inventory_type='normal').last(), in_stock=in_stock).last()
                    if reserved_ware is None:
                        pass
                    else:
                        if reserved_inv_type_quantity > reserved_ware.quantity:
                            reserved_ware_quantity = 0
                            ordered_next_quantity = reserved_inv_type_quantity - reserved_ware.quantity
                            reserved_ware.quantity = reserved_ware_quantity
                            reserved_ware.save()
                            ordered_ware = WarehouseInventory.objects.filter(
                                warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                                    inventory_state='ordered').last(), inventory_type=InventoryType.objects.filter(
                                    inventory_type='normal').last(), in_stock=in_stock).last()
                            if ordered_ware is None:
                                pass
                            else:
                                if ordered_next_quantity > ordered_ware.quantity:
                                    ordered_ware_quantity = 0
                                    ordered_ware.quantity = ordered_ware_quantity
                                    ordered_ware.save()
                                else:
                                    ordered_ware.quantity = ordered_next_quantity
                                    ordered_ware.save()

                        else:
                            reserved_ware.quantity = reserved_inv_type_quantity
                            reserved_ware.save()
                            ordered_ware = WarehouseInventory.objects.filter(
                                warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                                    inventory_state='ordered').last(), inventory_type=InventoryType.objects.filter(
                                    inventory_type='normal').last(), in_stock=in_stock).last()
                            if ordered_ware is None:
                                pass
                            else:
                                ordered_ware_quantity = 0
                                ordered_ware.quantity = ordered_ware_quantity
                                ordered_ware.save()
                else:
                    if quantity is None:
                        quantity = 0
                    ware_house_inventory_obj.quantity = quantity
                    ware_house_inventory_obj.save()

                ware_house_inventory_obj = WarehouseInventory.objects.filter(
                    warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                        inventory_state=inventory_state).last(), inventory_type=InventoryType.objects.filter(
                        inventory_type=inventory_type).last(), in_stock=in_stock).last()

                if ware_house_inventory_obj:
                    if quantity is None:
                        quantity = 0
                    ware_house_inventory_obj.quantity = quantity
                    ware_house_inventory_obj.save()
                else:
                    WarehouseInventory.objects.get_or_create(
                        warehouse=Shop.objects.filter(id=warehouse)[0],
                        sku=Product.objects.filter(product_sku=sku)[0],
                        inventory_state=InventoryState.objects.filter(inventory_state=inventory_state).last(),
                        inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(),
                        in_stock=in_stock, quantity=quantity)
        else:
            ware_house_inventory_obj = WarehouseInventory.objects.filter(
                warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                    inventory_state=inventory_state).last(), inventory_type=InventoryType.objects.filter(
                    inventory_type=inventory_type).last(), in_stock=in_stock).last()

            if ware_house_inventory_obj:
                if quantity is None:
                    quantity = 0
                ware_house_inventory_obj.quantity = quantity
                ware_house_inventory_obj.save()
            else:
                WarehouseInventory.objects.get_or_create(
                    warehouse=Shop.objects.filter(id=warehouse)[0],
                    sku=Product.objects.filter(product_sku=sku)[0],
                    inventory_state=InventoryState.objects.filter(inventory_state=inventory_state).last(),
                    inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(),
                    in_stock=in_stock, quantity=quantity)

    @classmethod
    def create_audit_entry(cls, uploaded_by, upload_csv):
        """

        :param uploaded_by: User object
        :param upload_csv: File object
        :return: queryset of stock movement csv
        """
        try:
            # Create data in Audit Model while Audit Upload CSV
            audit_object = Audit.objects.get_or_create(uploaded_by=uploaded_by, upload_csv=upload_csv)
            return audit_object

        except Exception as e:
            error_logger.error(e)

    @classmethod
    def create_warehouse_inventory_change_for_audit(cls, warehouse, sku, transaction_type, transaction_id,
                                                    initial_stage, final_stage, inventory_type, quantity):
        """

        :param warehouse: warehouse obj
        :param sku: sku obj
        :param transaction_type: type of transaction
        :param transaction_id: transaction id
        :param initial_stage: initial stage obj
        :param final_stage: final stage obj
        :param inventory_type: inventory type obj
        :param quantity: quantity
        :return: None
        """
        try:
            # Create data in WareHouse Internal Inventory Model
            WarehouseInternalInventoryChange.objects.create(warehouse_id=warehouse,
                                                            sku=sku, transaction_type=transaction_type,
                                                            transaction_id=transaction_id, initial_stage=initial_stage,
                                                            final_stage=final_stage, quantity=quantity,
                                                            inventory_type=inventory_type)
        except Exception as e:
            error_logger.error(e)


def create_or_update_bin_inv(batch_id, warehouse, sku, bin_id, inv_type, in_stock, qty):
    bin_inv_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(batch_id=batch_id,
                                                                         warehouse=warehouse, sku=sku,
                                                                         bin__bin_id=bin_id,
                                                                         inventory_type=inv_type, in_stock=in_stock)
    if bin_inv_obj.exists():
        bin_inv_obj = bin_inv_obj.last()
        available_qty = bin_inv_obj.quantity
        bin_inv_obj.quantity = (available_qty + qty)
        bin_inv_obj.save()
    else:
        CommonBinInventoryFunctions.create_bin_inventory(warehouse, bin_id, sku, batch_id,
                                                         inv_type, qty, in_stock)


def common_on_return_and_partial(shipment):
    with transaction.atomic():
        putaway_qty = 0
        inv_type = {'E': InventoryType.objects.get(inventory_type='expired'),
                    'D': InventoryType.objects.get(inventory_type='damaged'),
                    'N': InventoryType.objects.get(inventory_type='normal')}
        for shipment_product in shipment.rt_order_product_order_product_mapping.all():
            for shipment_product_batch in shipment_product.rt_ordered_product_mapping.all():
                # first bin with non 0 inventory for a batch or last empty bin
                shipment_product_batch_bin_list = PickupBinInventory.objects.filter(
                    shipment_batch=shipment_product_batch)
                bin_id_for_input = None
                shipment_product_batch_bin_temp = None
                for shipment_product_batch_bin in shipment_product_batch_bin_list:
                    if shipment_product_batch_bin.bin.quantity == 0:
                        bin_id_for_input=shipment_product_batch_bin.bin
                        continue
                    else:
                        bin_id_for_input = shipment_product_batch_bin.bin
                        break
                if shipment_product_batch.returned_qty > 0 or shipment_product_batch.returned_damage_qty > 0 \
                        or shipment_product_batch.delivered_qty > 0:
                    putaway_qty = shipment_product_batch.returned_qty + shipment_product_batch.returned_damage_qty
                    if putaway_qty == 0:
                        continue
                    else:
                        In.objects.create(warehouse=shipment_product_batch.pickup.warehouse, in_type='RETURN',
                                          in_type_id=shipment.id, sku=shipment_product_batch.pickup.sku,
                                          batch_id=shipment_product_batch.batch_id, quantity=putaway_qty)
                        pu, _ = Putaway.objects.update_or_create(putaway_user=shipment.last_modified_by,
                                                                 warehouse=shipment_product_batch.pickup.warehouse,
                                                                 putaway_type='RETURNED',
                                                                 putaway_type_id=shipment.invoice_no,
                                                                 sku=shipment_product_batch.pickup.sku,
                                                                 batch_id=shipment_product_batch.batch_id,
                                                                 defaults={'quantity': putaway_qty,
                                                                           'putaway_quantity': 0})
                        PutawayBinInventory.objects.update_or_create(warehouse=shipment_product_batch.pickup.warehouse,
                                                                     sku=shipment_product_batch.pickup.sku,
                                                                     batch_id=shipment_product_batch.batch_id,
                                                                     putaway_type='RETURNED',
                                                                     putaway=pu, bin=bin_id_for_input,
                                                                     putaway_status=False,
                                                                     defaults={'putaway_quantity': putaway_qty})

                else:

                    # put_away_object = Putaway.objects.filter(putaway_user=shipment.last_modified_by,
                    #                                          warehouse=shipment_product_batch.pickup.warehouse,
                    #                                          putaway_type='PAR_SHIPMENT',
                    #                                          putaway_type_id=shipment.order.order_no,
                    #                                          sku=shipment_product_batch.pickup.sku,
                    #                                          batch_id=shipment_product_batch.batch_id)
                    #
                    # if put_away_object.exists():
                    #     qty = i.expired_qty + i.damaged_qty
                    # else:
                    #     qty = i.expired_qty + i.damaged_qty
                    partial_ship_qty = (shipment_product_batch.pickup_quantity - shipment_product_batch.quantity)
                    if partial_ship_qty <= 0:
                        continue
                    else:
                        pu, _ = Putaway.objects.update_or_create(putaway_user=shipment.last_modified_by,
                                                                 warehouse=shipment_product_batch.pickup.warehouse,
                                                                 putaway_type='PAR_SHIPMENT',
                                                                 putaway_type_id=shipment.order.order_no,
                                                                 sku=shipment_product_batch.pickup.sku,
                                                                 batch_id=shipment_product_batch.batch_id,
                                                                 defaults={'quantity': partial_ship_qty, 'putaway_quantity': 0})

                        PutawayBinInventory.objects.update_or_create(warehouse=shipment_product_batch.pickup.warehouse,
                                                                     sku=shipment_product_batch.pickup.sku,
                                                                     batch_id=shipment_product_batch.batch_id,
                                                                     putaway_type='PAR_SHIPMENT',
                                                                     putaway=pu, bin=bin_id_for_input,
                                                                     putaway_status=False,
                                                                     defaults={'putaway_quantity': partial_ship_qty})


def create_batch_id(sku, expiry_date):

    """

    :param sku: product sku
    :param expiry_date: expiry date
    :return:
    """
    try:
        try:
            batch_id = '{}{}'.format(sku, datetime.strptime(expiry_date, '%d-%m-%y').strftime('%d%m%y'))

        except:
            try:
                batch_id = '{}{}'.format(sku, datetime.strptime(expiry_date, '%d-%m-%Y').strftime('%d%m%y'))
            except:
                try:
                    batch_id = '{}{}'.format(sku, datetime.strptime(expiry_date, '%d/%m/%Y').strftime('%d%m%y'))
                except:
                    batch_id = '{}{}'.format(sku, datetime.strptime(expiry_date, '%d/%m/%y').strftime('%d%m%y'))
        return batch_id
    except Exception as e:
        error_logger.error(e.message)


def get_expiry_date(batch_id):
    """

    :param batch_id:
    :return: expiry date
    """
    if len(batch_id) == 23:
        expiry_date = batch_id[17:19] + '/' + batch_id[19:21] + '/' + '20' + batch_id[21:23]
    else:
        expiry_date = '30/' + batch_id[17:19] + '/20' + batch_id[19:21]
    return expiry_date


def set_expiry_date(batch_id):
    """

    :param batch_id: batch id
    :return: expiry date
    """
    if len(batch_id) == 23:
        expiry_date = batch_id[17:19] + '/' + batch_id[19:21] + '/' + batch_id[21:23]
    else:
        expiry_date = '30/' + batch_id[17:19] + '/' + batch_id[19:21]
    return expiry_date


class WareHouseInternalInventoryChange(object):
    @classmethod
    def create_warehouse_inventory_change(cls, warehouse, sku, transaction_type, transaction_id,
                                          initial_type, initial_stage, final_type, final_stage, quantity):
        """

        :param warehouse:
        :param sku:
        :param transaction_type:
        :param transaction_id:
        :param initial_type:
        :param initial_stage:
        :param final_type:
        :param final_stage:
        :param quantity:
        :return:
        """
        try:
            # Create data in WareHouse Internal Inventory Model
            WarehouseInternalInventoryChange.objects.create(warehouse_id=warehouse.id,
                                                            sku=sku, transaction_type=transaction_type,
                                                            transaction_id=transaction_id,
                                                            initial_type=initial_type,
                                                            initial_stage=initial_stage,
                                                            final_type=final_type,
                                                            final_stage=final_stage,
                                                            quantity=quantity,
                                                            )
        except Exception as e:
            error_logger.error(e)


def cancel_ordered(request, obj, ordered_inventory_state, initial_stage, bin_id):
    if obj.putaway.putaway_quantity == 0:
        obj.putaway.putaway_quantity = obj.putaway_quantity
    else:
        obj.putaway.putaway_quantity = obj.putaway_quantity + obj.putaway.putaway_quantity
    normal_inventory_type = 'normal',
    available_inventory_state = 'available',
    available_quantity = obj.putaway_quantity
    ordered_quantity = int(-obj.putaway_quantity)
    transaction_type = 'put_away_type'
    transaction_id = obj.putaway_id
    initial_type = InventoryType.objects.filter(inventory_type='normal').last(),
    final_type = InventoryType.objects.filter(inventory_type='normal').last(),
    final_stage = InventoryState.objects.filter(inventory_state='available').last(),
    try:
        initial_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
        final_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
    except:
        raise forms.ValidationError("Bin Id is not associate with this Warehouse.")
    quantity = available_quantity
    batch_id = obj.batch_id
    bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse, bin__bin_id=bin_id.bin.bin_id, sku=obj.sku, batch_id=batch_id,
                                              inventory_type=initial_type[0], in_stock=True).last()
    if bin_inv_obj:
        bin_quantity = bin_inv_obj.quantity
        final_quantity = bin_quantity + quantity
        bin_inv_obj.quantity = final_quantity
        bin_inv_obj.save()
    else:

        BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku, batch_id=batch_id,
                                           inventory_type=initial_type[0], quantity=quantity, in_stock=True)

    CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                 normal_inventory_type[0],
                                                                 available_inventory_state[0],
                                                                 available_quantity, True)
    CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                 normal_inventory_type[0],
                                                                 ordered_inventory_state[0],
                                                                 ordered_quantity, True)
    WareHouseInternalInventoryChange.create_warehouse_inventory_change(obj.warehouse, obj.sku,
                                                                       transaction_type,
                                                                       transaction_id,
                                                                       initial_type[0],
                                                                       initial_stage[0],
                                                                       final_type[0], final_stage[0],
                                                                       available_quantity)
    BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                              batch_id=batch_id,
                                              initial_bin=Bin.objects.get(bin_id=initial_bin_id,
                                                                          warehouse=obj.warehouse),
                                              final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                        warehouse=obj.warehouse),
                                              initial_inventory_type=initial_type[0],
                                              final_inventory_type=final_type[0],
                                              transaction_type=transaction_type,
                                              transaction_id=transaction_id,
                                              quantity=quantity)

    obj.putaway.putaway_user = request
    obj.putaway.save()
    obj.putaway_status = True
    obj.save()


def cancel_shipment(request, obj, ordered_inventory_state, initial_stage, shipment_obj, bin_id):
    if obj.putaway.putaway_quantity == 0:
        obj.putaway.putaway_quantity = obj.putaway_quantity
    else:
        obj.putaway.putaway_quantity = obj.putaway_quantity + obj.putaway.putaway_quantity
    obj.putaway.putaway_user = request
    obj.putaway.save()
    transaction_type = 'put_away_type'
    transaction_id = obj.putaway_id
    initial_type = InventoryType.objects.filter(inventory_type='normal').last(),
    type_expired = InventoryType.objects.filter(inventory_type="expired").last()
    type_damaged = InventoryType.objects.filter(inventory_type="damaged").last()
    final_stage = InventoryState.objects.filter(inventory_state='available').last(),
    normal_inventory_type = 'normal',
    expired_inventory_type = 'expired',
    damaged_inventory_type = 'damaged',
    available_inventory_state = 'available',
    try:
        initial_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
        final_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
    except:
        raise forms.ValidationError("Bin Id is not associate with this Warehouse.")
    batch_id = obj.batch_id
    for i in shipment_obj:
        for shipped_obj in i.rt_ordered_product_mapping.all():
            if obj.sku_id == shipped_obj.bin.sku.product_sku:
                for pick_bin in shipped_obj.rt_pickup_batch_mapping.all():
                    if pick_bin.bin.bin.bin_id == obj.bin.bin.bin_id:
                        expired_qty = shipped_obj.expired_qty
                        damaged_qty = shipped_obj.damaged_qty
                        if expired_qty > 0:
                            bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse,
                                                                      bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      inventory_type=type_expired,
                                                                      in_stock=True).last()
                            if bin_inv_obj:
                                bin_quantity = bin_inv_obj.quantity
                                final_quantity = bin_quantity + expired_qty
                                bin_inv_obj.quantity = final_quantity
                                bin_inv_obj.save()
                            else:

                                BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku,
                                                                   batch_id=batch_id,
                                                                   inventory_type=type_expired, quantity=expired_qty,
                                                                   in_stock=True)
                        if damaged_qty > 0:
                            bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse,
                                                                      bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      inventory_type=type_damaged,
                                                                      in_stock=True).last()
                            if bin_inv_obj:
                                bin_quantity = bin_inv_obj.quantity
                                final_quantity = bin_quantity + damaged_qty
                                bin_inv_obj.quantity = final_quantity
                                bin_inv_obj.save()
                            else:

                                BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku,
                                                                   batch_id=batch_id,
                                                                   inventory_type=type_damaged, quantity=damaged_qty,
                                                                   in_stock=True)
                        deduct_quantity = expired_qty + damaged_qty
                        ordered_quantity = int(-deduct_quantity)
                        obj.putaway_status = True
                        if expired_qty > 0:
                            CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                                         expired_inventory_type[0],
                                                                                         available_inventory_state[0],
                                                                                         expired_qty, True)
                            WareHouseInternalInventoryChange.create_warehouse_inventory_change(obj.warehouse, obj.sku,
                                                                                               transaction_type,
                                                                                               transaction_id,
                                                                                               initial_type[0],
                                                                                               initial_stage[0],
                                                                                               type_expired,
                                                                                               final_stage[0],
                                                                                               expired_qty)
                            BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      initial_bin=Bin.objects.get(bin_id=initial_bin_id,
                                                                                                  warehouse=obj.warehouse),
                                                                      final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                warehouse=obj.warehouse),
                                                                      initial_inventory_type=initial_type[0],
                                                                      final_inventory_type=type_expired,
                                                                      transaction_type=transaction_type,
                                                                      transaction_id=transaction_id,
                                                                      quantity=expired_qty)
                        if damaged_qty > 0:
                            CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                                         damaged_inventory_type[0],
                                                                                         available_inventory_state[0],
                                                                                         damaged_qty, True)
                            WareHouseInternalInventoryChange.create_warehouse_inventory_change(obj.warehouse, obj.sku,
                                                                                               transaction_type,
                                                                                               transaction_id,
                                                                                               initial_type[0],
                                                                                               initial_stage[0],
                                                                                               type_damaged,
                                                                                               final_stage[0],
                                                                                               damaged_qty)
                            BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      initial_bin=Bin.objects.get(bin_id=initial_bin_id,
                                                                                                  warehouse=obj.warehouse),
                                                                      final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                warehouse=obj.warehouse),
                                                                      initial_inventory_type=initial_type[0],
                                                                      final_inventory_type=type_damaged,
                                                                      transaction_type=transaction_type,
                                                                      transaction_id=transaction_id,
                                                                      quantity=damaged_qty)
                        CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                                     normal_inventory_type[0],
                                                                                     ordered_inventory_state[0],
                                                                                     ordered_quantity, True)
                        obj.putaway_status = True
                        obj.save()
                    else:
                        pass
            else:
                pass


def cancel_returned(request, obj, ordered_inventory_state, initial_stage, shipment_obj, bin_id):
    if obj.putaway.putaway_quantity == 0:
        obj.putaway.putaway_quantity = obj.putaway_quantity
    else:
        obj.putaway.putaway_quantity = obj.putaway_quantity + obj.putaway.putaway_quantity
    obj.putaway.putaway_user = request
    obj.putaway.save()
    transaction_type = 'put_away_type'
    transaction_id = obj.putaway_id
    initial_type = InventoryType.objects.filter(inventory_type='normal').last(),
    type_damaged = InventoryType.objects.filter(inventory_type="damaged").last()
    final_stage = InventoryState.objects.filter(inventory_state='available').last(),
    normal_inventory_type = 'normal',
    damaged_inventory_type = 'damaged',
    available_inventory_state = 'available',
    try:
        initial_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
        final_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
    except:
        raise forms.ValidationError("Bin Id is not associate with this Warehouse.")
    batch_id = obj.batch_id
    for i in shipment_obj:
        for shipped_obj in i.rt_ordered_product_mapping.all():
            if obj.sku_id == shipped_obj.bin.sku.product_sku:
                for pick_bin in shipped_obj.rt_pickup_batch_mapping.all():
                    if pick_bin.bin.bin.bin_id == obj.bin.bin.bin_id:
                        normal_qty = shipped_obj.returned_qty
                        returned_damaged_qty = shipped_obj.returned_damage_qty
                        if normal_qty > 0:
                            bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse,
                                                                      bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      inventory_type=initial_type[0],
                                                                      in_stock=True).last()
                            if bin_inv_obj:
                                bin_quantity = bin_inv_obj.quantity
                                final_quantity = bin_quantity + normal_qty
                                bin_inv_obj.quantity = final_quantity
                                bin_inv_obj.save()
                            else:

                                BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku,
                                                                   batch_id=batch_id,
                                                                   inventory_type=initial_type[0], quantity=normal_qty,
                                                                   in_stock=True)
                        if returned_damaged_qty > 0:
                            bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse,
                                                                      bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      inventory_type=type_damaged,
                                                                      in_stock=True).last()
                            if bin_inv_obj:
                                bin_quantity = bin_inv_obj.quantity
                                final_quantity = bin_quantity + returned_damaged_qty
                                bin_inv_obj.quantity = final_quantity
                                bin_inv_obj.save()
                            else:

                                BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku,
                                                                   batch_id=batch_id,
                                                                   inventory_type=type_damaged,
                                                                   quantity=returned_damaged_qty,
                                                                   in_stock=True)

                        deduct_quantity = normal_qty + returned_damaged_qty
                        ordered_quantity = int(-deduct_quantity)
                        obj.putaway_status = True
                        if normal_qty > 0:
                            CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                                         normal_inventory_type[0],
                                                                                         available_inventory_state[0],
                                                                                         normal_qty, True)
                            WareHouseInternalInventoryChange.create_warehouse_inventory_change(obj.warehouse, obj.sku,
                                                                                               transaction_type,
                                                                                               transaction_id,
                                                                                               initial_type[0],
                                                                                               initial_stage[0],
                                                                                               initial_type[0],
                                                                                               final_stage[0],
                                                                                               normal_qty)
                            BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      initial_bin=Bin.objects.get(bin_id=initial_bin_id,
                                                                                                  warehouse=obj.warehouse),
                                                                      final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                warehouse=obj.warehouse),
                                                                      initial_inventory_type=initial_type[0],
                                                                      final_inventory_type=initial_type[0],
                                                                      transaction_type=transaction_type,
                                                                      transaction_id=transaction_id,
                                                                      quantity=normal_qty)
                        if returned_damaged_qty > 0:
                            CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                                         damaged_inventory_type[0],
                                                                                         available_inventory_state[0],
                                                                                         returned_damaged_qty, True)
                            WareHouseInternalInventoryChange.create_warehouse_inventory_change(obj.warehouse, obj.sku,
                                                                                               transaction_type,
                                                                                               transaction_id,
                                                                                               initial_type[0],
                                                                                               initial_stage[0],
                                                                                               type_damaged,
                                                                                               final_stage[0],
                                                                                               returned_damaged_qty)
                            BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                      batch_id=batch_id,
                                                                      initial_bin=Bin.objects.get(bin_id=initial_bin_id,
                                                                                                  warehouse=obj.warehouse),
                                                                      final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                warehouse=obj.warehouse),
                                                                      initial_inventory_type=initial_type[0],
                                                                      final_inventory_type=type_damaged,
                                                                      transaction_type=transaction_type,
                                                                      transaction_id=transaction_id,
                                                                      quantity=returned_damaged_qty)
                        CommonWarehouseInventoryFunctions.create_warehouse_inventory(obj.warehouse, obj.sku,
                                                                                     normal_inventory_type[0],
                                                                                     ordered_inventory_state[0],
                                                                                     ordered_quantity, True)
                        obj.putaway_status = True
                        obj.save()

                    else:
                        pass
            else:
                pass
