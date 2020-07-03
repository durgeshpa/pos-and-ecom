from .models import (Bin, BinInventory, Putaway, PutawayBinInventory, Pickup, WarehouseInventory,
                     InventoryState, InventoryType, WarehouseInternalInventoryChange, In, PickupBinInventory)
from shops.models import Shop
from django.db.models import Sum, Q
import functools
import json
from celery.task import task
from products.models import Product, ProductPrice


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
    def create_in(cls, warehouse, in_type, in_type_id, sku, batch_id, quantity):
        if warehouse.shop_type.shop_type == 'sp':
            in_obj = In.objects.create(warehouse=warehouse, in_type=in_type, in_type_id=in_type_id,
                                   sku=sku, batch_id=batch_id, quantity=quantity)

            PutawayCommonFunctions.create_putaway(in_obj.warehouse, in_obj.in_type, in_obj.id, in_obj.sku, in_obj.batch_id, in_obj.quantity, 0)
            return in_obj

    @classmethod
    def get_filtered_in(cls, **kwargs):
        in_data = In.objects.filter(**kwargs)
        return in_data


class CommonBinInventoryFunctions(object):

    @classmethod
    def update_or_create_bin_inventory(cls, warehouse, bin, sku, batch_id, inventory_type, quantity, in_stock):
        BinInventory.objects.update_or_create(warehouse=warehouse, bin=bin, sku=sku, batch_id=batch_id,
                                      defaults={'inventory_type':inventory_type,'quantity':quantity, 'in_stock':in_stock})

    @classmethod
    def get_filtered_bin_inventory(cls, **kwargs):
        bin_inv_data = BinInventory.objects.filter(**kwargs)
        return bin_inv_data


class CommonPickupFunctions(object):

    @classmethod
    def create_pickup_entry(cls, warehouse, pickup_type, pickup_type_id, sku, quantity):
        Pickup.objects.create(warehouse=warehouse, pickup_type=pickup_type, pickup_type_id=pickup_type_id, sku=sku, quantity=quantity)


class CommonInventoryStateFunctions(object):

    @classmethod
    def filter_inventory_state(cls, **kwargs):
        inv_state = InventoryState.objects.filter(**kwargs)
        return inv_state


class CommonWarehouseInventoryFunctions(object):

    @classmethod
    def create_warehouse_inventory(cls, warehouse, sku, inventory_state,inventory_type,quantity,in_stock):
        if type_choices[inventory_type] and state_choices[inventory_state]:
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
        Q(inventory_state='available'),
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
            Q(inventory_state='available'),
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
            Q(inventory_state='available'),
            Q(in_stock='t')
        ).aggregate(total=Sum('quantity')).get('total')

        return product_availability

    else:
        product_availability = WarehouseInventory.objects.filter(
            Q(sku__id=sku_id),
            Q(quantity__gt=0),
            Q(inventory_state='available'),
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










