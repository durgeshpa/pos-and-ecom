# python imports
import functools
import json
import logging
from datetime import datetime
from celery.task import task

# django imports
from django.db.models import Sum, Q
from django.db import transaction

# app imports
from .models import (Bin, BinInventory, Putaway, PutawayBinInventory, Pickup, WarehouseInventory,
                     InventoryState, InventoryType, WarehouseInternalInventoryChange, In, PickupBinInventory,
                     BinInternalInventoryChange, StockMovementCSVUpload, StockCorrectionChange, OrderReserveRelease,
                     Audit)


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


def updating_tables_on_putaway(sh, bin_id, put_away, batch_id, inv_type, inv_state, t, val, put_away_status, pu):
    CommonBinInventoryFunctions.update_or_create_bin_inventory(sh, Bin.objects.filter(bin_id=bin_id).last(),
                                                               put_away.last().sku, batch_id,
                                                               InventoryType.objects.filter(
                                                                   inventory_type=inv_type).last(), val, t)
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
    CommonWarehouseInventoryFunctions.create_warehouse_inventory(sh, put_away.last().sku,
                                                                 CommonInventoryStateFunctions.filter_inventory_state(inventory_state=inv_state).last(),
                                                                 InventoryType.objects.filter(inventory_type=inv_type).last(),
                                                                 BinInventory.available_qty(sh.id, put_away.last().sku.id), t)


def common_for_release(prod_list, shop_id, transaction_type, transaction_id, order_status):
    for prod in prod_list:
        ordered_product_reserved = WarehouseInventory.objects.filter(sku__id=prod, inventory_state__inventory_state='reserved')
        if ordered_product_reserved.exists():
            reserved_qty = ordered_product_reserved.last().quantity
            if reserved_qty == 0:
                return
            ordered_id = ordered_product_reserved.last().id
            wim = WarehouseInventory.objects.filter(sku__id=prod,inventory_state__inventory_state='available')
            available_qty = wim.last().quantity
            if order_status == 'ordered':
                wim.update(quantity=available_qty)
                WarehouseInventory.objects.filter(id=ordered_id).update(quantity=reserved_qty,inventory_state=InventoryState.objects.filter(inventory_state='ordered').last())
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
    pickup_object = PickupBinInventory.objects.filter(pickup__pickup_type_id=instance.order_no)
    inv_type = {'N': InventoryType.objects.get(inventory_type='normal')}
    for pickup in pickup_object:
        pick_up_bin_quantity = pickup.pickup_quantity

        # Bin Model Update
        bin_inv_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(bin__bin_id=pickup.bin.bin.bin_id,
                                                                             sku__id=pickup.pickup.sku.id,
                                                                             batch_id=pickup.batch_id,
                                                                             inventory_type=inv_type['N'],
                                                                             quantity__gt=0)
        bin_inv_qty = bin_inv_obj.last().quantity
        bin_inv_obj.update(quantity=bin_inv_qty + pick_up_bin_quantity)
        if pick_up_bin_quantity == 0:
            pass
        else:
            pu, _ = Putaway.objects.update_or_create(warehouse=pickup.warehouse, putaway_type='SHIPMENT',
                                                     putaway_type_id=instance.order_no, sku=pickup.bin.sku,
                                                     batch_id=pickup.batch_id, defaults={'quantity': pick_up_bin_quantity,
                                                                                    'putaway_quantity': pick_up_bin_quantity})
            PutawayBinInventory.objects.update_or_create(warehouse=pickup.warehouse, sku=pickup.bin.sku,
                                                         batch_id=pickup.batch_id, putaway_type='SHIPMENT',
                                                         putaway=pu, bin=pickup.bin, putaway_status=True,
                                                         defaults={'putaway_quantity': pick_up_bin_quantity})
        cancel_order(instance)


class AuditInventory(object):
    """This class is used for to store data in different models while audit file upload """

    @classmethod
    def audit_exist_batch_id(cls, data, key, value, audit_inventory_obj):
        """

        :param data: list of csv data
        :param key: Inventory type
        :param value: Quantity
        :param audit_inventory_obj: object of Audit inventory Model
        :return:
        """
        # filter in Bin inventory table to get batch id for particular sku, warehouse and bin in
        bin_inv = BinInventory.objects.filter(warehouse=data[0],
                                              bin=Bin.objects.filter(bin_id=data[4]).last(),
                                              sku=Product.objects.filter(
                                                  product_sku=data[1][-17:]).last()).last()

        # call function to create and update Bin inventory for specific Inventory Type
        AuditInventory.update_or_create_bin_inventory_for_audit(data[0], data[4],
                                                                data[1][-17:],
                                                                bin_inv.batch_id,
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
                inventory_type=key).last().id), True, bin_inv.batch_id, data[4])

        # call function to create and update Ware House Internal Inventory for specific Inventory Type
        transaction_type = 'audit_adjustment'
        AuditInventory.create_warehouse_inventory_change_for_audit(
            Shop.objects.get(id=data[0]).id, Product.objects.get(
                product_sku=data[1][-17:]), transaction_type, audit_inventory_obj[0].id,
            CommonInventoryStateFunctions.filter_inventory_state(inventory_state='available').last(),
            CommonInventoryStateFunctions.filter_inventory_state(inventory_state='available').last(),
            InventoryType.objects.filter(inventory_type=key).last(), value)

    @classmethod
    def update_or_create_bin_inventory_for_audit(cls, warehouse, bin_id, sku, batch_id, inventory_type, quantity, in_stock):
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

        ware_house_inventory_obj = WarehouseInventory.objects.filter(
            warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                inventory_state=inventory_state).last(), inventory_type=InventoryType.objects.filter(
                inventory_type=inventory_type).last(), in_stock=in_stock).last()
        # get all quantity for same sku in warehouse except inventory type is normal
        all_ware_house_inventory_obj = BinInventory.objects.filter(warehouse=warehouse, bin__bin_id=bin_id, sku=sku,
                                              batch_id=batch_id,in_stock=in_stock)

        # check the object is exist or not
        if all_ware_house_inventory_obj.exists():
            all_ware_house_quantity = 0
            # get the quantity
            for in_ware_house in all_ware_house_inventory_obj:
                all_ware_house_quantity = in_ware_house.quantity + all_ware_house_quantity
            if all_ware_house_quantity >= ware_house_inventory_obj.quantity:
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
                        ordered_next_quantity = reserved_inv_type_quantity-reserved_ware.quantity
                        reserved_ware.quantity = reserved_ware_quantity
                        reserved_ware.save()
                        ordered_ware = WarehouseInventory.objects.filter(
                            warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                                inventory_state='ordered').last(), inventory_type=InventoryType.objects.filter(
                                inventory_type='normal').last(), in_stock=in_stock).last()
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



def common_on_return_and_partial(shipment):
    putaway_qty = 0
    inv_type = {'E': InventoryType.objects.get(inventory_type='expired'),
                'D': InventoryType.objects.get(inventory_type='damaged'),
                'R': InventoryType.objects.get(inventory_type='returned')}
    for i in shipment.rt_order_product_order_product_mapping.all():
        for j in i.rt_ordered_product_mapping.all():
            if j.returned_qty > 0:
                BinInventory.objects.update_or_create(batch_id=j.batch_id, warehouse=j.pickup.warehouse,
                                                      sku=j.pickup.sku, bin=j.bin.bin, inventory_type=inv_type['R'],
                                                      in_stock='t', defaults={'quantity': j.returned_qty})
                putaway_qty = j.returned_qty
                if putaway_qty ==0:
                    continue
                else:
                    pu, _ = Putaway.objects.update_or_create(warehouse=j.pickup.warehouse, putaway_type='RETURNED',
                                                             putaway_type_id=shipment.invoice_no, sku=j.pickup.sku,
                                                             batch_id=j.batch_id, defaults={'quantity': putaway_qty,
                                                                                            'putaway_quantity': putaway_qty})
                    PutawayBinInventory.objects.update_or_create(warehouse=j.pickup.warehouse, sku=j.pickup.sku,
                                                                batch_id=j.batch_id, putaway_type='RETURNED',
                                                                putaway=pu, bin=j.bin, putaway_status=True,
                                                                defaults={'putaway_quantity': putaway_qty})

            else:
                if j.damaged_qty > 0:
                    BinInventory.objects.update_or_create(batch_id=j.batch_id, warehouse=j.pickup.warehouse,
                                                      sku=j.pickup.sku, bin=j.bin.bin, inventory_type=inv_type['D'],
                                                      in_stock='t', defaults={'quantity': j.damaged_qty})
                if j.expired_qty > 0:
                    BinInventory.objects.update_or_create(batch_id=j.batch_id, warehouse=j.pickup.warehouse,sku=j.pickup.sku, bin=j.bin.bin, inventory_type=inv_type['E'],in_stock='t', defaults={'quantity':j.expired_qty})

                putaway_qty = (j.pickup_quantity - j.quantity)
                if putaway_qty < 0:
                    continue
                else:
                    pu, _ = Putaway.objects.update_or_create(warehouse=j.pickup.warehouse, putaway_type='PAR_SHIPMENT',
                                                         putaway_type_id=shipment.invoice_no, sku=j.pickup.sku,
                                                         batch_id=j.batch_id, defaults={'quantity': putaway_qty,
                                                                                        'putaway_quantity': putaway_qty})
                    PutawayBinInventory.objects.update_or_create(warehouse=j.pickup.warehouse, sku=j.pickup.sku,
                                                             batch_id=j.batch_id, putaway_type='PAR_SHIPMENT',
                                                             putaway=pu, bin=j.bin, putaway_status=True,
                                                             defaults={'putaway_quantity': putaway_qty})