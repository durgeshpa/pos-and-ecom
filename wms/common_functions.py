import logging
from .models import (Bin, BinInventory, Putaway, PutawayBinInventory, Pickup, WarehouseInventory,
                     InventoryState, InventoryType, WarehouseInternalInventoryChange, In, PickupBinInventory,
                     BinInternalInventoryChange, StockMovementCSVUpload, StockCorrectionChange)

# from gram_to_brand.models import GRNOrderProductMapping
from shops.models import Shop
from products.models import Product
from retailer_to_sp.models import Cart, Order, OrderedProduct
from sp_to_gram.models import OrderedProductReserved
from django.db.models import Sum, Q
from datetime import datetime
import functools
import json
from celery.task import task
from datetime import datetime, timedelta


# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

class PutawayCommonFunctions(object):

    @classmethod
    def create_putaway(cls, warehouse, putaway_type, putaway_type_id, sku, batch_id, quantity, putaway_quantity):
        if warehouse.shop_type.shop_type=='sp':
            Putaway.objects.create(warehouse=warehouse, putaway_type=putaway_type, putaway_type_id=putaway_type_id, sku=sku,
                                   batch_id=batch_id, quantity=quantity, putaway_quantity=putaway_quantity)

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
    def create_in(cls, warehouse, in_type, in_type_id, sku, batch_id, quantity):
        if warehouse.shop_type.shop_type == 'sp':
            in_obj = In.objects.create(warehouse=warehouse, in_type=in_type, in_type_id=in_type_id, sku=sku,
                                       batch_id=batch_id, quantity=quantity)
            PutawayCommonFunctions.create_putaway(in_obj.warehouse, in_obj.in_type, in_obj.id, in_obj.sku,
                                                  in_obj.batch_id, in_obj.quantity, 0)
            return in_obj

    @classmethod
    def get_filtered_in(cls, **kwargs):
        in_data = In.objects.filter(**kwargs)
        return in_data


class CommonBinInventoryFunctions(object):

    @classmethod
    def update_or_create_bin_inventory(cls, warehouse, bin, sku, batch_id, inventory_type, quantity, in_stock):
        BinInventory.objects.update_or_create(warehouse=warehouse, bin=bin, sku=sku, batch_id=batch_id,
                                              inventory_type=inventory_type,
                                              defaults={'quantity':quantity, 'in_stock':in_stock})

    @classmethod
    def create_bin_inventory(cls, warehouse, bin, sku, batch_id, inventory_type, quantity, in_stock):
        BinInventory.objects.get_or_create(warehouse=warehouse, bin=bin, sku=sku, batch_id=batch_id,
                                    inventory_type=inventory_type, quantity=quantity, in_stock=in_stock)

    @classmethod
    def filter_bin_inventory(cls, warehouse, sku, batch_id, bin_obj, inventory_type):
        return BinInventory.objects.filter(warehouse=warehouse, sku=sku, batch_id=batch_id, bin=bin_obj,
                                           inventory_type__inventory_type=inventory_type)


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
    return WarehouseInventory.objects.filter(
        Q(warehouse=shop),
        Q(quantity__gt=0),
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
            Q(in_stock='t')
        ).aggregate(total=Sum('quantity')).get('total')

        return product_availability

    else:
        product_availability = WarehouseInventory.objects.filter(
            Q(sku__id=sku_id),
            Q(quantity__gt=0),
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
                                                    transaction_id=transaction_id, initial_stage='available',
                                                    final_stage='reserved', quantity=ordered_qty)
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
        for i in sku_id:
            ordered_product_reserved = WarehouseInventory.objects.filter(
                sku__id=i, inventory_state__inventory_state='reserved')
            if ordered_product_reserved.exists():
                reserved_qty = ordered_product_reserved.last().quantity
                ordered_id = ordered_product_reserved.last().id
                wim = WarehouseInventory.objects.filter(sku__id=i,inventory_state__inventory_state='available')
                available_qty = wim.last().quantity
                wim.update(quantity=available_qty+reserved_qty)
                WarehouseInventory.objects.filter(id=ordered_id).update(quantity=0)
                WarehouseInternalInventoryChange.objects.create(warehouse=Shop.objects.get(id=shop_id),
                                                        sku=Product.objects.get(id=i),
                                                        transaction_type=transaction_type,
                                                        transaction_id=transaction_id,
                                                        initial_stage='reserved', final_stage='available',
                                                        quantity=reserved_qty)


class InternalInventoryChange(object):
    @classmethod
    def create_bin_internal_inventory_change(cls, shop_id, sku, batch_id, bin_id, final_bin_id, initial_type,
                                             final_type, quantity, inventory_csv):
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
        WarehouseInventory.objects.update_or_create(warehouse=warehouse, sku=sku,
                                                    inventory_type__inventory_type=InventoryType.objects.get(inventory_type=inventory_type),
                                                    inventory_state__inventory_state=InventoryState.objects.get(inventory_state=inventory_state),
                                                    defaults={'quantity': quantity, 'in_stock': in_stock})

    @classmethod
    def create_warehouse_inventory(cls, warehouse, sku, inventory_type, inventory_state, quantity, in_stock):
        WarehouseInventory.objects.get_or_create(warehouse=warehouse, sku=sku,
                                                 inventory_type=inventory_type, inventory_state=inventory_state,
                                                 quantity=quantity, in_stock=in_stock)

    @classmethod
    def filter_warehouse_inventory(cls, warehouse, sku, inventory_state, inventory_type):
        return WarehouseInventory.objects.filter(warehouse=warehouse, sku=sku,
                                                 inventory_type__inventory_type=InventoryType.objects.get(inventory_type=inventory_type),
                                                 inventory_state__inventory_state=InventoryState.objects.get(inventory_state=inventory_state))


class InternalWarehouseChange(object):
    @classmethod
    def create_warehouse_inventory_change(cls, warehouse, sku, transaction_type, transaction_id, initial_stage,
                                          final_stage, inventory_type, quantity, inventory_csv):
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
        try:
            stock_movement_csv_object = StockMovementCSVUpload.objects.get_or_create(uploaded_by=uploaded_by,
                                                                                     upload_csv=upload_csv,
                                                                                     inventory_movement_type=inventory_movement_type,)

            return stock_movement_csv_object

        except Exception as e:
            error_logger.error(e)
