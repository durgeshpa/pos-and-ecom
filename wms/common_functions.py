# python imports
import codecs
import csv
import datetime
import functools
import json
import logging

from celery.task import task
from decouple import config
# django imports
from django import forms
from django.db import transaction
from django.db.models import Sum, Q
from rest_framework import status
from rest_framework.response import Response

# app imports
from audit.models import AUDIT_PRODUCT_STATUS, AuditProduct
from products.models import Product, ParentProduct, ProductPrice
from shops.models import Shop
from wms.common_validators import get_csv_file_data
from .models import (Bin, BinInventory, Putaway, PutawayBinInventory, Pickup, WarehouseInventory,
                     InventoryState, InventoryType, WarehouseInternalInventoryChange, In, PickupBinInventory,
                     BinInternalInventoryChange, StockMovementCSVUpload, StockCorrectionChange, OrderReserveRelease,
                     Audit, Out, Zone, WarehouseAssortment)

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
    def create_putaway_with_putaway_bin_inventory(cls, bi, inventory_type, putaway_type, putaway_type_id, qty,
                                                  putaway_status):
        """
        Creates entry in Putaway and PutawayBinInventory
        Params:
            bi : BinInventory instance
            inventory_type : InventoryType instance
            putaway_type : String type identifier for transaction type
            putaway_type_id : String type identifier for transaction type
            qty : Total Quantity to create putaway for
            putaway_status : True/False
        """

        pu_obj = cls.create_putaway(bi.warehouse, putaway_type, putaway_type_id, bi.sku, bi.batch_id, qty,
                                    0, inventory_type)
        # PutawayBinInventory.objects.create(warehouse=pu_obj.warehouse, sku=pu_obj.sku,
        #                                    batch_id=pu_obj.batch_id, bin=bi,
        #                                    putaway_type=putaway_type, putaway=pu_obj,
        #                                    putaway_status=putaway_status,
        #                                    putaway_quantity=qty)

    @classmethod
    def create_putaway(cls, warehouse, putaway_type, putaway_type_id, sku, batch_id, quantity, putaway_quantity,
                       inventory_type):
        if warehouse.shop_type.shop_type in ['sp', 'f']:
            if putaway_quantity == 0:
                putaway_status = Putaway.PUTAWAY_STATUS_CHOICE.NEW
            elif putaway_quantity == quantity:
                putaway_status = Putaway.PUTAWAY_STATUS_CHOICE.COMPLETED
            else:
                putaway_status = None
            putaway_obj = Putaway.objects.create(warehouse=warehouse, putaway_type=putaway_type,
                                                 putaway_type_id=putaway_type_id, sku=sku,
                                                 batch_id=batch_id, quantity=quantity,
                                                 putaway_quantity=putaway_quantity,
                                                 inventory_type=inventory_type)
            if putaway_status is not None:
                putaway_obj.status = putaway_status
                putaway_obj.save()
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

    @classmethod
    def get_suggested_bins_for_putaway(cls, warehouse, sku, batch_id, inventory_type):
        """ Returns the Bins suggested where the given SKU can be kept"""
        suggested_bins = set()
        zone = WarehouseAssortmentCommonFunction.get_product_zone(warehouse, sku)
        queryset = BinInventory.objects.filter(warehouse=warehouse, bin__zone=zone, inventory_type=inventory_type, sku=sku)
        if queryset.filter(Q(quantity__gt=0)|Q(to_be_picked_qty__gt=0), batch_id=batch_id).exists():
            bin_list = queryset.filter(Q(quantity__gt=0)|Q(to_be_picked_qty__gt=0),sku=sku, batch_id=batch_id)\
                               .values_list('bin__bin_id', flat=True).distinct('bin')[:3]
            suggested_bins.update(bin_list)
        if len(suggested_bins) == 0:
            bins_to_exclude = queryset.filter(~Q(batch_id=batch_id),Q(quantity__gt=0)|Q(to_be_picked_qty__gt=0))\
                                      .values_list('bin_id', flat=True)
            bin_list = queryset.exclude(bin_id__in=bins_to_exclude)\
                               .values_list('bin__bin_id', flat=True).distinct('bin')[:3]
            suggested_bins.update(bin_list)
        return suggested_bins

class InCommonFunctions(object):

    @classmethod
    def create_in(cls, warehouse, in_type, in_type_id, sku, batch_id, quantity, putaway_quantity, inventory_type,
                  weight=0, manufacturing_date=None):
        if warehouse.shop_type.shop_type in ['sp', 'f']:
            in_obj = In.objects.create(warehouse=warehouse, in_type=in_type, in_type_id=in_type_id, sku=sku,
                                       batch_id=batch_id, inventory_type=inventory_type,
                                       quantity=quantity, expiry_date=get_expiry_date_db(batch_id), weight=weight,
                                       manufacturing_date=manufacturing_date)
            PutawayCommonFunctions.create_putaway(in_obj.warehouse, in_obj.in_type, in_obj.id, in_obj.sku,
                                                  in_obj.batch_id, in_obj.quantity, putaway_quantity,
                                                  in_obj.inventory_type)
            return in_obj

    @classmethod
    def create_only_in(cls, warehouse, in_type, in_type_id, sku, batch_id, quantity, inventory_type, weight=0,
                       manufacturing_date=None):
        if warehouse.shop_type.shop_type in ['sp', 'f']:
            in_obj = In.objects.create(warehouse=warehouse, in_type=in_type, in_type_id=in_type_id, sku=sku,
                                       batch_id=batch_id, quantity=quantity, expiry_date=get_expiry_date_db(batch_id),
                                       inventory_type=inventory_type, weight=weight, manufacturing_date=manufacturing_date)
            return in_obj

    @classmethod
    def get_filtered_in(cls, **kwargs):
        in_data = In.objects.filter(**kwargs)
        return in_data


class OutCommonFunctions(object):

    @classmethod
    def create_out(cls, warehouse, out_type, out_type_id, sku, batch_id, quantity, inventory_type):
        if warehouse.shop_type.shop_type in ['sp', 'f']:
            in_obj = Out.objects.create(warehouse=warehouse, out_type=out_type, out_type_id=out_type_id, sku=sku,
                                        batch_id=batch_id, quantity=quantity, inventory_type=inventory_type)
            return in_obj

    @classmethod
    def get_filtered_in(cls, **kwargs):
        in_data = In.objects.filter(**kwargs)
        return in_data


class CommonBinInventoryFunctions(object):

    @classmethod
    @transaction.atomic
    def update_bin_inventory_with_transaction_log(cls, warehouse, bin, sku, batch_id, initial_inventory_type,
                                                  final_inventory_time, quantity, in_stock, tr_type, tr_id, weight=0):
        bin_inv_obj = cls.update_or_create_bin_inventory(warehouse, bin, sku, batch_id, final_inventory_time, quantity,
                                                         in_stock, weight)
        BinInternalInventoryChange.objects.create(warehouse=warehouse, sku=sku,
                                                  batch_id=batch_id,
                                                  final_bin=bin,
                                                  initial_inventory_type=initial_inventory_type,
                                                  final_inventory_type=final_inventory_time,
                                                  transaction_type=tr_type,
                                                  transaction_id=tr_id,
                                                  quantity=abs(quantity))
        return bin_inv_obj

    @classmethod
    @transaction.atomic
    def update_or_create_bin_inventory(cls, warehouse, bin, sku, batch_id, inventory_type, quantity, in_stock, weight=0):
        bin_inv_obj = BinInventory.objects.select_for_update().\
                                           filter(warehouse=warehouse, bin__bin_id=bin, sku=sku, batch_id=batch_id,
                                                  inventory_type=inventory_type, in_stock=in_stock).last()
        if bin_inv_obj:
            bin_quantity = bin_inv_obj.quantity
            final_quantity = bin_quantity + quantity
            bin_inv_obj.quantity = final_quantity
            bin_inv_obj.weight = bin_inv_obj.weight + weight
            bin_inv_obj.save()
        else:
            bin_inv_obj, created = BinInventory.objects.get_or_create(warehouse=warehouse, bin=bin, sku=sku,
                                                                      batch_id=batch_id, inventory_type=inventory_type,
                                                                      quantity=quantity, in_stock=in_stock,
                                                                      weight=weight)
        return bin_inv_obj

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

    @classmethod
    def deduct_to_be_picked_from_bin(cls, qty_picked, bin_inv_obj):
        obj = BinInventory.objects.select_for_update().get(pk=bin_inv_obj.id)
        obj.to_be_picked_qty = obj.to_be_picked_qty - qty_picked
        obj.save()

    @classmethod
    def add_to_be_picked_to_bin(cls, qty, bin_inv_obj):
        obj = BinInventory.objects.select_for_update().get(pk=bin_inv_obj.id)
        obj.to_be_picked_qty = obj.to_be_picked_qty + qty
        obj.save()

    @classmethod
    @transaction.atomic
    def product_shift_across_bins(cls, data):
        """
        Move product from one bin to the other bin
        Refreshes the pickup list if required
        """
        warehouse = data['warehouse']
        source_bin = data['s_bin']
        target_bin = data['t_bin']
        batch_id = data['batch_id']
        sku = get_sku_from_batch(batch_id)
        qty = data['qty']
        inventory_type = data['inventory_type']
        tr_type = 'bin_shift'
        tr_id = 'bin_shift'
        try:
            with transaction.atomic():
                source_bin_inv_object = BinInventory.objects.select_for_update().filter(
                    warehouse=warehouse, bin_id=source_bin, batch_id=batch_id,
                    inventory_type=inventory_type,
                    sku__product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL).last()

                target_bin_inv_object = BinInventory.objects.select_for_update().filter(
                    warehouse=warehouse, bin_id=target_bin, batch_id=batch_id,
                    inventory_type=inventory_type,
                    sku__product_type=Product.PRODUCT_TYPE_CHOICE.NORMAL).last()
                if source_bin_inv_object.quantity < qty:
                    qty_to_deduct_from_bin_inv = source_bin_inv_object.quantity
                    total_qty_to_move_from_pickup = qty - qty_to_deduct_from_bin_inv
                else:
                    qty_to_deduct_from_bin_inv = qty
                    total_qty_to_move_from_pickup = 0

                if qty_to_deduct_from_bin_inv > 0:
                    # CommonBinInventoryFunctions.update_bin_inventory_with_transaction_log(warehouse, source_bin, sku,
                    #                                                                       batch_id,
                    #                                                                       inventory_type,
                    #                                                                       inventory_type,
                    #                                                                       -1 * qty_to_deduct_from_bin_inv,
                    #                                                                       True, tr_type_deduct, tr_id)
                    #
                    # target_bin_inv_object = CommonBinInventoryFunctions.update_bin_inventory_with_transaction_log(
                    #     warehouse, target_bin, sku, batch_id, inventory_type, inventory_type,
                    #     qty_to_deduct_from_bin_inv,
                    #     True, tr_type_add, tr_id)

                    source_bin_inv_object = cls.update_or_create_bin_inventory(warehouse, source_bin, sku, batch_id,
                                                                        inventory_type, -1*qty_to_deduct_from_bin_inv,
                                                                        True)

                    target_bin_inv_object = cls.update_or_create_bin_inventory(warehouse, target_bin, sku, batch_id,
                                                                        inventory_type, qty_to_deduct_from_bin_inv,
                                                                        True)
                    BinInternalInventoryChange.objects.create(warehouse=warehouse, sku=sku,
                                                              batch_id=batch_id,
                                                              initial_bin=source_bin,
                                                              final_bin=target_bin,
                                                              initial_inventory_type=inventory_type,
                                                              final_inventory_type=inventory_type,
                                                              transaction_type=tr_type,
                                                              transaction_id=tr_id,
                                                              quantity=abs(qty))

                if total_qty_to_move_from_pickup > 0:
                    CommonBinInventoryFunctions.deduct_to_be_picked_from_bin(total_qty_to_move_from_pickup,
                                                                             source_bin_inv_object)
                    CommonBinInventoryFunctions.add_to_be_picked_to_bin(total_qty_to_move_from_pickup,
                                                                            target_bin_inv_object)
                    pickup_bin_qs = PickupBinInventory.objects.select_for_update().filter(
                        warehouse=warehouse, batch_id=batch_id, bin=source_bin_inv_object,
                        pickup__status__in=['pickup_creation', 'picking_assigned'], quantity__gt=0,
                        pickup_quantity__isnull=True).order_by('id')
                    for pb in pickup_bin_qs:
                        qty_to_move_from_pickup = 0
                        if total_qty_to_move_from_pickup > pb.quantity:
                            qty_to_move_from_pickup = pb.quantity
                            total_qty_to_move_from_pickup -= qty_to_move_from_pickup
                            pb.quantity = 0
                            pb.save()
                        elif total_qty_to_move_from_pickup > 0:
                            qty_to_move_from_pickup = total_qty_to_move_from_pickup
                            pb.quantity = pb.quantity - qty_to_move_from_pickup
                            total_qty_to_move_from_pickup = 0
                            pb.save()

                        pbi = PickupBinInventory.objects.filter(warehouse=pb.warehouse, batch_id=pb.batch_id,
                                                                pickup=pb.pickup, bin=target_bin_inv_object).last()
                        if not pbi:
                            PickupBinInventory.objects.create(warehouse=pb.warehouse, batch_id=pb.batch_id,
                                                              pickup=pb.pickup, bin=target_bin_inv_object,
                                                              quantity=qty_to_move_from_pickup)
                        else:
                            pbi.quantity += qty_to_move_from_pickup
                            pbi.save()
        except Exception as e:
            info_logger.error('product_shift_across_bins | '.join(e.args) if len(e.args) > 0 else 'Unknown Error')
            raise Exception('Product movement failed!')


class CommonPickupFunctions(object):

    @classmethod
    def create_pickup_entry(cls, warehouse, pickup_type, pickup_type_id, sku, quantity, status, inventory_type):
        return Pickup.objects.create(warehouse=warehouse, pickup_type=pickup_type, pickup_type_id=pickup_type_id, sku=sku,
                                     quantity=quantity, status=status, inventory_type=inventory_type)

    @classmethod
    def get_filtered_pickup(cls, **kwargs):
        pickup_data = Pickup.objects.filter(**kwargs).exclude(status='picking_cancelled')
        return pickup_data


class CommonInventoryStateFunctions(object):

    @classmethod
    def filter_inventory_state(cls, **kwargs):
        inv_state = InventoryState.objects.filter(**kwargs)
        return inv_state


class CommonWarehouseInventoryFunctions(object):
    @classmethod
    @transaction.atomic
    def create_warehouse_inventory_with_transaction_log(cls, warehouse, product, inventory_type, inventory_state, quantity,
                                                        transaction_type, transaction_id, in_stock=True, weight=0):
        """
        Create/Update entry in WarehouseInventory
        Create entry in WarehouseInternalInventoryChange
        Params :
            warehouse : Shop instance
            product : Product instance
            inventory_type : InventoryType instance
            inventory_state : InventoryState instance
            quantity : integer transaction quantity, positive if increasing the quantity, negative is decreasing the quantity
            transaction_type : string identifier for transaction
            transaction_id : string identifier for transaction
        Returns :
            WarehouseInventory and WarehouseInternalInventoryChange
        """

        info_logger.info("Warehouse Inventory Update Started| Warehouse-{}, SKU-{}, Inventory Type-{}, "
                         "Inventory State-{}, Quantity-{}, Transaction type-{}, Transaction ID-{}"
                         .format(warehouse.id, product.product_sku, inventory_type.inventory_type,
                                 inventory_state.inventory_state, quantity, transaction_type, transaction_id))
        wi = cls.create_warehouse_inventory(warehouse, product, inventory_type, inventory_state, quantity, in_stock, weight)
        wii = WarehouseInternalInventoryChange.objects.create(warehouse=warehouse, sku=product,
                                                              transaction_type=transaction_type,
                                                              transaction_id=transaction_id,
                                                              inventory_type=inventory_type,
                                                              inventory_state=inventory_state,
                                                              quantity=quantity,
                                                              weight=weight)
        info_logger.info("Warehouse Inventory Update| Done")
        return wi, wii

    @classmethod
    def create_warehouse_inventory(cls, warehouse, sku, inventory_type, inventory_state, quantity, in_stock, weight=0):

        ware_house_inventory_obj = WarehouseInventory.objects.select_for_update().filter(
            warehouse=warehouse, sku=sku, inventory_state=InventoryState.objects.filter(
                inventory_state=inventory_state).last(), inventory_type=InventoryType.objects.filter(
                inventory_type=inventory_type).last(), in_stock=in_stock).last()

        if ware_house_inventory_obj:
            ware_house_quantity = quantity + ware_house_inventory_obj.quantity
            ware_house_weight = weight + ware_house_inventory_obj.weight
            ware_house_inventory_obj.weight = ware_house_weight
            ware_house_inventory_obj.quantity = ware_house_quantity
            ware_house_inventory_obj.save()
        else:
            ware_house_inventory_obj = WarehouseInventory.objects.get_or_create(
                                warehouse=warehouse,
                                sku=sku,
                                inventory_state=InventoryState.objects.filter(inventory_state=inventory_state).last(),
                                inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(),
                                in_stock=in_stock, quantity=quantity, weight=weight
                            )
        return ware_house_inventory_obj

    @classmethod
    def create_warehouse_inventory_stock_correction(cls, warehouse, sku, inventory_type, inventory_state, quantity, in_stock):
        # This function is only used for update warehouse inventory while stock correction change method
        """

        :param warehouse:
        :param sku:
        :param inventory_type:
        :param inventory_state:
        :param quantity:
        :param in_stock:
        :return:
        """
        if inventory_state == "available":
            inventory_state = InventoryState.objects.filter(inventory_state="total_available").last()
        ware_house_inventory_obj = WarehouseInventory.objects.filter(
            warehouse=warehouse, sku=sku, inventory_state=inventory_state, inventory_type=InventoryType.objects.filter(
                inventory_type=inventory_type).last(), in_stock=in_stock).last()

        quantity = BinInventory.objects.filter(Q(warehouse=warehouse),
                                              Q(sku=sku),
                                              Q(inventory_type__id=
                                                InventoryType.objects.filter(inventory_type=inventory_type)[0].id),
                                              Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')
        if ware_house_inventory_obj:
            if quantity is None:
                quantity = 0
            ware_house_inventory_obj.quantity = quantity
            ware_house_inventory_obj.save()
        else:
            if quantity is None:
                quantity = 0
            WarehouseInventory.objects.get_or_create(
                warehouse=warehouse,
                sku=sku,
                inventory_state=inventory_state,
                inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(),
                in_stock=in_stock, quantity=quantity)

    @classmethod
    def create_warehouse_inventory_stock_correction_weight(cls, warehouse, sku, inventory_type, inventory_state, weight,
                                                    in_stock):
        # This function is only used for update warehouse inventory while stock correction change method
        """
        :param warehouse:
        :param sku:
        :param inventory_type:
        :param inventory_state:
        :param weight:
        :param in_stock:
        :return:
        """
        ware_house_inventory_obj = WarehouseInventory.objects.filter(
            warehouse=warehouse, sku=sku, inventory_state=inventory_state, inventory_type=InventoryType.objects.filter(
                inventory_type=inventory_type).last(), in_stock=in_stock).last()

        weight = BinInventory.objects.filter(Q(warehouse=warehouse),
                                               Q(sku=sku),
                                               Q(inventory_type__id=
                                                 InventoryType.objects.filter(inventory_type=inventory_type)[0].id),
                                               Q(weight__gt=0)).aggregate(total=Sum('weight')).get('total')
        if weight is None:
            weight = 0
        if ware_house_inventory_obj:
            ware_house_inventory_obj.weight = weight
            ware_house_inventory_obj.save()
        else:
            WarehouseInventory.objects.get_or_create(
                warehouse=warehouse,
                sku=sku,
                inventory_state=inventory_state,
                inventory_type=InventoryType.objects.filter(inventory_type=inventory_type).last(),
                in_stock=in_stock, quantity=0, weight=weight)

    @classmethod
    def filtered_warehouse_inventory_items(cls, **kwargs):
        inven_items = WarehouseInventory.objects.filter(**kwargs)
        return inven_items


class CommonPickBinInvFunction(object):

    @classmethod
    def create_pick_bin_inventory(cls, warehouse, pickup, batch_id, bin, quantity, bin_quantity, pickup_quantity):
        PickupBinInventory.objects.create(warehouse=warehouse, pickup=pickup, batch_id=batch_id, bin=bin,
                                          quantity=quantity, pickup_quantity=pickup_quantity, bin_quantity=bin_quantity)

    @classmethod
    def get_filtered_pick_bin_inv(cls, **kwargs):
        pick_bin_inv = PickupBinInventory.objects.filter(**kwargs).exclude(pickup__status='picking_cancelled')
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


def add_discounted_product_quantity(shop, inventory_type, sku_qty_dict):
    """
    Taken in the dictionary of product and their stock,
    checks and add in that if any discounted product stock is available
    """

    product_ids = sku_qty_dict.keys()
    discounted_products = Product.objects.filter(id__in=product_ids, discounted_sku__isnull=False)\
                                         .values('id','discounted_sku__id')
    discounted_product_dict = {p['discounted_sku__id']:p['id'] for p in discounted_products}
    if len(discounted_product_dict) > 0:
        stock = get_stock(shop, inventory_type, discounted_product_dict.keys())
        for product_id, qty in stock.items():
            sku_qty_dict[discounted_product_dict[product_id]] += qty
    return sku_qty_dict


def get_stock(shop, inventory_type, product_id_list=None):
    inventory_states = InventoryState.objects.filter(inventory_state__in=['reserved', 'ordered',
                                                                          'to_be_picked', 'total_available'])
    query_set = WarehouseInventory.objects.filter(warehouse=shop,
                                                  inventory_type=inventory_type,
                                                  quantity__gt=0,
                                                  inventory_state__in=inventory_states)
    if product_id_list is not None:
        if len(product_id_list) > 0:
            query_set = query_set.filter(sku__id__in=product_id_list)

    sku_qty_dict = {}
    for item in query_set:
        if sku_qty_dict.get(item.sku.id) is None:
            sku_qty_dict[item.sku.id] = 0
        inventory_state = item.inventory_state.inventory_state
        if inventory_state == 'total_available':
            sku_qty_dict[item.sku.id] += item.quantity
        elif inventory_state == 'reserved':
            sku_qty_dict[item.sku.id] -= item.quantity
        elif inventory_state == 'ordered':
            sku_qty_dict[item.sku.id] -= item.quantity
        elif inventory_state == 'to_be_picked':
            sku_qty_dict[item.sku.id] -= item.quantity
    return sku_qty_dict


def get_visibility_changes(shop, product):
    visibility_changes = {}
    if isinstance(product, int):
        product = Product.objects.filter(id=product).last()
        if not product:
            return visibility_changes

    visibility_changes[product.id] = False
    child_siblings = Product.objects.filter(
        parent_product=ParentProduct.objects.filter(id=product.parent_product.id).last(), status='active'
    )
    min_exp_date_data = {
        'id': '',
        'exp': None
    }
    for child in child_siblings:
        product_price_entries = child.product_pro_price.filter(seller_shop=shop, approval_status=2, status=True)
        if not product_price_entries:
            visibility_changes[child.id] = False
            continue
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        product_qty_dict = get_stock(shop, type_normal, [child.id])
        if len(product_qty_dict) == 0:
            visibility_changes[child.id] = False
            continue
        if AuditProduct.objects.filter(warehouse=shop, sku=child, status=AUDIT_PRODUCT_STATUS.BLOCKED).exists():
            visibility_changes[child.id] = False
            continue
        if child.reason_for_child_sku == 'offer':
            visibility_changes[child.id] = True
            continue
        if child.product_type == Product.PRODUCT_TYPE_CHOICE.DISCOUNTED:
            visibility_changes[child.id] = True
            continue
        sum_qty_warehouse_entries = product_qty_dict[child.id]
        if sum_qty_warehouse_entries == 0 or int(sum_qty_warehouse_entries/child.product_inner_case_size)==0:
            visibility_changes[child.id] = False
            continue
        if sum_qty_warehouse_entries <= 2*(int(child.product_inner_case_size)):
            visibility_changes[child.id] = True
            continue
        bin_data = BinInventory.objects.filter(
            Q(warehouse=shop),
            Q(sku=child),
            Q(inventory_type=InventoryType.objects.filter(inventory_type='normal').last()),
            quantity__gt=0
        )
        for data in bin_data:
            if ProductPrice.objects.filter(product=data.sku, approval_status=2, status=True,
                                           seller_shop=shop).exists():
                exp_date_str = get_expiry_date(batch_id=data.batch_id)
                exp_date = datetime.datetime.strptime(exp_date_str, "%d/%m/%Y")
                if not min_exp_date_data.get('exp', None):
                    min_exp_date_data['exp'] = exp_date
                    min_exp_date_data['id'] = data.sku.id

                elif exp_date == min_exp_date_data.get('exp'):
                    visibility_changes[min_exp_date_data['id']] = True
                    min_exp_date_data['exp'] = exp_date
                    min_exp_date_data['id'] = data.sku.id

                elif exp_date < min_exp_date_data.get('exp'):
                    visibility_changes[min_exp_date_data['id']] = False
                    min_exp_date_data['exp'] = exp_date
                    min_exp_date_data['id'] = data.sku.id
                else:
                    visibility_changes[child.id] = False
    if min_exp_date_data.get('id'):
        visibility_changes[min_exp_date_data['id']] = True
    return visibility_changes


class OrderManagement(object):

    @classmethod
    @task
    def create_reserved_order(cls, reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        products = params['products']
        transaction_type = params['transaction_type']
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        state_available = InventoryState.objects.filter(inventory_state='available').last()
        state_reserved = InventoryState.objects.filter(inventory_state='reserved').last()
        state_ordered = InventoryState.objects.filter(inventory_state='ordered').last()
        for prod_id, ordered_qty in products.items():
            shop = Shop.objects.get(id=shop_id)
            product = Product.objects.get(id=int(prod_id))
            reserved = OrderReserveRelease.objects.filter(warehouse=shop,
                                                          sku=product,
                                                          transaction_id=transaction_id).last()

            if reserved is not None:
                if reserved.warehouse_internal_inventory_release is None:
                    continue

            warehouse_inventory, warehouse_internal_inventory = \
                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                shop, product, type_normal, state_reserved, ordered_qty, transaction_type, transaction_id )

            OrderReserveRelease.objects.create(warehouse=shop,
                                               sku=product,
                                               transaction_id=transaction_id,
                                               warehouse_internal_inventory_reserve=warehouse_internal_inventory,
                                               reserved_time=warehouse_internal_inventory.created_at)

    @classmethod
    @task
    def release_blocking(cls, reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        transaction_type = params['transaction_type']
        order_status = params['order_status']
        order_no = params['order_number'] if 'order_number' in params else None
        common_for_release(sku_id, shop_id, transaction_type, transaction_id, order_status, order_no)

    @classmethod
    def release_blocking_from_order(cls, reserved_args, sku_id=False):
        params = json.loads(reserved_args)
        transaction_id = params['transaction_id']
        shop_id = params['shop_id']
        transaction_type = params['transaction_type']
        order_status = params['order_status']
        order_no = params['order_number']
        result = common_for_release(sku_id, shop_id, transaction_type, transaction_id, order_status, order_no)
        if result is False:
            return False


class InternalInventoryChange(object):
    @classmethod
    def create_bin_internal_inventory_change(cls, shop_id, sku, batch_id, final_bin_id, initial_type,
                                             final_type, transaction_type, transaction_id, quantity,
                                             weight=0):
        """

        :param shop_id:
        :param sku:
        :param batch_id:
        :param final_bin_id:
        :param initial_type:
        :param final_type:
        :param transaction_type:
        :param transaction_id:
        :param quantity:
        :param weight:
        :return:
        """

        BinInternalInventoryChange.objects.create(warehouse_id=shop_id.id, sku=sku,
                                                  batch_id=batch_id,
                                                  final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                            warehouse=Shop.objects.get(
                                                                                id=shop_id.id)),
                                                  initial_inventory_type=initial_type,
                                                  final_inventory_type=final_type,
                                                  transaction_type=transaction_type,
                                                  transaction_id=transaction_id,
                                                  quantity=quantity,
                                                  weight=weight)


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

        WarehouseInternalInventoryChange.objects.create(warehouse=warehouse,
                                                        sku=sku, transaction_type=transaction_type,
                                                        transaction_id=transaction_id, initial_stage=initial_stage,
                                                        final_stage=final_stage, quantity=quantity,
                                                        initial_type=initial_type, final_type=final_type,
                                                        inventory_csv=inventory_csv)



class InternalStockCorrectionChange(object):
    @classmethod
    def create_stock_inventory_change(cls, warehouse, stock_sku, batch_id, stock_bin_id, correction_type,
                                      quantity, inventory_csv, inventory_type, weight=0):
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
                                                 quantity=quantity, inventory_csv=inventory_csv,
                                                 inventory_type=inventory_type, weight=weight)
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


def updating_tables_on_putaway(sh, bin_id, put_away, batch_id, inv_type, inv_state, t, val, put_away_status, pu,
                               weight):
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
    :param weight:
    :return:
    """
    bin_inventory_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(warehouse=sh, bin=Bin.objects.filter(
                                                                               bin_id=bin_id, warehouse=sh).last(),
                                                                               sku=put_away.last().sku,
                                                                               batch_id=batch_id,
                                                                               inventory_type=InventoryType.objects.filter(
                                                                                   inventory_type=inv_type).last(),
                                                                               in_stock=t)
    if bin_inventory_obj.exists():
        bin_inventory_obj = bin_inventory_obj.last()
        bin_quantity = val + bin_inventory_obj.quantity
        bin_weight = weight + bin_inventory_obj.weight
        bin_inventory_obj.quantity = bin_quantity
        bin_inventory_obj.weight = bin_weight
        bin_inventory_obj.save()
    else:
        BinInventory.objects.create(warehouse=sh,
                                    bin=Bin.objects.filter(bin_id=bin_id, warehouse=sh).last(),
                                    sku=put_away.last().sku,
                                    batch_id=batch_id, inventory_type=InventoryType.objects.filter(
                                        inventory_type=inv_type).last(), quantity=val, in_stock=t,
                                    weight=weight)

    if put_away_status is True:
        PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(),
                                           bin=CommonBinInventoryFunctions.get_filtered_bin_inventory(bin_id=Bin.objects.filter(bin_id=bin_id, warehouse=sh).last()).last(),
                                           putaway_quantity=val, putaway_status=True,
                                           sku=pu[0].sku, batch_id=pu[0].batch_id,
                                           putaway_type=pu[0].putaway_type)
    else:
        PutawayBinInventory.objects.create(warehouse=sh, putaway=put_away.last(),
                                           bin=CommonBinInventoryFunctions.get_filtered_bin_inventory(bin_id=Bin.objects.filter(bin_id=bin_id, warehouse=sh).last()).last(),
                                           putaway_quantity=val, putaway_status=False,
                                           sku=pu[0].sku, batch_id=pu[0].batch_id,
                                           putaway_type=pu[0].putaway_type)
    transaction_type = 'put_away_type'
    transaction_id = put_away[0].id
    initial_type = InventoryType.objects.filter(inventory_type='new').last(),
    final_type = InventoryType.objects.filter(inventory_type='normal').last(),
    InternalInventoryChange.create_bin_internal_inventory_change(sh, pu[0].sku, batch_id, bin_id, initial_type[0],
                                                                 final_type[0], transaction_type,
                                                                 transaction_id, val, weight)

    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(sh, pu[0].sku, inv_type,
                                                                                      inv_state, val, transaction_type,
                                                                                      transaction_id, True, weight)


def common_for_release(prod_list, shop_id, transaction_type, transaction_id, order_status, order_no=None):
    """

    :param prod_list:
    :param shop_id:
    :param transaction_type:
    :param transaction_id:
    :param order_status:
    :param order_no:
    :return:
    """
    order_reserve_release = OrderReserveRelease.objects.filter(transaction_id=transaction_id,
                                                               warehouse_internal_inventory_release_id=None)
    if order_reserve_release.exists():

        for order_product in order_reserve_release:
            if order_product.sku.id not in prod_list:
                continue
            # call function for release inventory
            release_type = 'manual'
            result = common_release_for_inventory(prod_list, shop_id, transaction_type, transaction_id, order_status,
                                         order_product, release_type, order_no)
            if result is False:
                return False
    else:
        return False


def common_release_for_inventory(prod_list, shop_id, transaction_type, transaction_id, order_status, order_product,
                                 release_type, order_no=None):
    """

    :param prod_list:
    :param shop_id:
    :param transaction_type:
    :param transaction_id:
    :param order_status:
    :param order_product:
    :return:
    """
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    ordered_state = InventoryState.objects.filter(inventory_state='ordered').last()
    reserved_state = InventoryState.objects.filter(inventory_state='reserved').last()
    transaction_quantity = order_product.warehouse_internal_inventory_reserve.quantity
    with transaction.atomic():
        # warehouse condition
        shop = Shop.objects.get(id=shop_id)
        warehouse_product_reserved = WarehouseInventory.objects.filter(warehouse=shop,
                                                                       sku__id=order_product.sku.id,
                                                                       inventory_state__inventory_state='reserved').last()
        product = Product.objects.get(id=order_product.sku.id)
        if warehouse_product_reserved:
            reserved_qty = warehouse_product_reserved.quantity
            if reserved_qty == 0:
                return False
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                shop, product, type_normal, reserved_state, -1*transaction_quantity, transaction_type, transaction_id)
        if order_status != 'available':
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                shop, product, type_normal, ordered_state, transaction_quantity, transaction_type, order_no)

        order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=shop,
                                                               sku=product,
                                                               warehouse_internal_inventory_release=None,
                                                               transaction_id=transaction_id)
        order_reserve_obj.update(
            warehouse_internal_inventory_release=WarehouseInternalInventoryChange.objects.filter(
                transaction_id=transaction_id).last(),
            release_time=datetime.datetime.now(), release_type=release_type,
            ordered_quantity=transaction_quantity)


def cancel_order(instance):
    """
    Revert the WarehouseInventory for the order given
    Deducts inventory from ordered state

    :param instance: order instance
    :return:
    """
    with transaction.atomic():
        # get the queryset object form warehouse internal inventory model
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        state_ordered = InventoryState.objects.filter(inventory_state='ordered').last()
        transaction_id = instance.order_no
        transaction_type = 'ordered'
        shop = instance.seller_shop
        ware_house_internal = WarehouseInternalInventoryChange.objects.filter(
            transaction_id=transaction_id,
            inventory_state=state_ordered, transaction_type=transaction_type)

        for item in ware_house_internal:
            product = item.sku
            qty = item.quantity
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                shop, product, type_normal, state_ordered, -1*qty, transaction_type, transaction_id)


def cancel_pickup(pickup_object):
    """
    Cancels the Pickup
    Iterates over all the items in PickupBinInventory for particular Pickup,
    and add item inventory reserved for Pickup back to the BinInventory.
    Updates quantity in respective BinInventory
    Updates to_be_picked_quantity in respective BinInventory
    Makes entry in BinInternalInventoryChange as transaction type 'picking_cancelled'
    Marks Pickup status as 'picking_cancelled'

    Parameters :
        pickup_object : instance of Pickup

    """
    pickup_id = pickup_object.pk
    tr_type = "picking_cancelled"
    state_to_be_picked = InventoryState.objects.filter(inventory_state="to_be_picked").last()
    state_ordered = InventoryState.objects.filter(inventory_state="ordered").last()
    state_picked = InventoryState.objects.filter(inventory_state="picked").last()
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    pickup_bin_qs = PickupBinInventory.objects.filter(pickup=pickup_object)
    total_remaining = 0
    info_logger.info("cancel_pickup| pickup -{}, SKU-{}".format(pickup_id, pickup_object.sku))
    for item in pickup_bin_qs:
        bi_qs = BinInventory.objects.select_for_update().filter(id=item.bin_id)
        bi = bi_qs.last()
        picked_qty = item.pickup_quantity
        info_logger.info("cancel_pickup | Bin-{}, batch-{}, bin qty-{}, to be picked qty-{}, picked qty-{}"
                         .format(bi.bin_id, bi.batch_id, bi.quantity, bi.to_be_picked_qty, picked_qty))
        if picked_qty is None:
            picked_qty = 0
        remaining_qty = item.quantity - picked_qty
        total_remaining += remaining_qty
        bin_quantity = bi.quantity + remaining_qty
        to_be_picked_qty = bi.to_be_picked_qty - remaining_qty
        if to_be_picked_qty < 0:
            to_be_picked_qty = 0
        info_logger.info("cancel_pickup | updated | Bin-{}, batch-{}, quantity-{}, to_be_picked_qty-{}"
                         .format(bi.bin_id, bi.batch_id, bin_quantity, to_be_picked_qty))
        bi_qs.update(quantity=bin_quantity, to_be_picked_qty=to_be_picked_qty)
        if remaining_qty > 0:
            InternalInventoryChange.create_bin_internal_inventory_change(bi.warehouse, bi.sku, bi.batch_id,
                                                                         bi.bin,
                                                                         type_normal, type_normal,
                                                                         tr_type,
                                                                         pickup_id,
                                                                         remaining_qty)
        if picked_qty > 0:
            PutawayCommonFunctions.create_putaway_with_putaway_bin_inventory(
                bi, type_normal, tr_type, pickup_id, picked_qty, False)
            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                pickup_object.warehouse, pickup_object.sku, pickup_object.inventory_type,
                state_picked, -1 * picked_qty, tr_type, pickup_id)

            info_logger.info("cancel_pickup | created putaway | Bin-{}, batch-{}, quantity-{}"
                             .format(bi.bin_id, bi.batch_id, picked_qty))
    if total_remaining > 0:
        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
            pickup_object.warehouse, pickup_object.sku, pickup_object.inventory_type,
            state_to_be_picked, -1 * total_remaining, tr_type, pickup_id)

        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
            pickup_object.warehouse, pickup_object.sku, pickup_object.inventory_type,
            state_ordered, total_remaining, tr_type, pickup_id)

    pickup_object.status = tr_type
    pickup_object.save()

    info_logger.info("cancel_pickup | completed | Pickup-{}".format(pickup_id))


def revert_ordered_inventory(pickup_object):
    """
    Takes the Pickup instance
    calculates the remaining quantity needs to be deducted from warehouse ordered state
    deducts remaining quantity from ordered state for concerned SKU
    """
    tr_type = "order_cancelled"
    tr_id = pickup_object.pickup_type_id
    state_ordered = InventoryState.objects.filter(inventory_state="ordered").last()
    remaining_quantity = pickup_object.quantity-pickup_object.pickup_quantity

    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
        pickup_object.warehouse, pickup_object.sku, pickup_object.inventory_type,
        state_ordered, -1 * remaining_quantity, tr_type, tr_id)


def cancel_order_with_pick(instance):
    """

    :param instance: order instance
    :return:

    """
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    state_picked = InventoryState.objects.filter(inventory_state='picked').last()

    with transaction.atomic():
        pickup_qs = Pickup.objects.select_for_update().filter(pickup_type_id=instance.order_no)\
                                      .exclude(status='picking_cancelled')
        if not pickup_qs.exists():
            return
        if pickup_qs.last().status in ['pickup_creation', 'picking_assigned']:
            for pickup_object in pickup_qs:
                cancel_pickup(pickup_object)
                revert_ordered_inventory(pickup_object)
            info_logger.info('cancel_order_with_pick| Order No-{}, Cancelled Pickup'
                             .format(instance.order_no))
            return
        if pickup_qs.last().status == 'picking_complete':
            pickup_id = pickup_qs.last().id
            warehouse = pickup_qs.last().warehouse
            sku = pickup_qs.last().sku

            # get the queryset object from Pickup Bin Inventory Model
            pickup_bin_object = PickupBinInventory.objects.filter(pickup__pickup_type_id=instance.order_no)\
                                                          .exclude(pickup__status='picking_cancelled')
            # iterate over the PickupBin Inventory object
            for pickup_bin in pickup_bin_object:
                quantity = 0
                pick_up_bin_quantity = 0
                if instance.rt_order_order_product.all():
                    if (instance.rt_order_order_product.all()[0].shipment_status == 'READY_TO_SHIP') or \
                            (instance.rt_order_order_product.all()[0].shipment_status == 'READY_TO_DISPATCH'):
                        pickup_order = pickup_bin.shipment_batch
                        put_away_object = Putaway.objects.filter(warehouse=pickup_bin.warehouse,
                                                                 putaway_type='CANCELLED',
                                                                 putaway_type_id=instance.order_no,
                                                                 sku=pickup_bin.bin.sku,
                                                                 batch_id=pickup_bin.batch_id,
                                                                 inventory_type=type_normal)
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
                                                                 inventory_type=type_normal,
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
                                                             inventory_type=type_normal,
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
                pu, _ = Putaway.objects.update_or_create(warehouse=pickup_bin.warehouse, putaway_type='CANCELLED',
                                                         putaway_type_id=instance.order_no, sku=pickup_bin.bin.sku,
                                                         batch_id=pickup_bin.batch_id,
                                                         inventory_type=type_normal,
                                                         defaults={'quantity': quantity,
                                                                   'status': Putaway.PUTAWAY_STATUS_CHOICE.NEW,
                                                                   'putaway_quantity': 0})
                # update or create put away bin inventory model
                # PutawayBinInventory.objects.update_or_create(warehouse=pickup_bin.warehouse, sku=pickup_bin.bin.sku,
                #                                              batch_id=pickup_bin.batch_id, putaway_type=status,
                #                                              putaway=pu, bin=pickup_bin.bin, putaway_status=False,
                #                                              defaults={'putaway_quantity': pick_up_bin_quantity})

                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                    warehouse, pickup_bin.bin.sku, type_normal, state_picked, -1 * pick_up_bin_quantity,
                    "order_cancelled", instance.order_no)
        pickup_qs.update(status='picking_cancelled')


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
        with transaction.atomic():
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
                InventoryType.objects.filter(inventory_type=key).last(),
                InventoryType.objects.filter(inventory_type=key).last(),
                value)

            final_bin_id = data[4]
            initial_type = InventoryType.objects.filter(inventory_type=key).last(),
            final_type = InventoryType.objects.filter(inventory_type=key).last(),
            transaction_type = transaction_type
            transaction_id = audit_inventory_obj[0].id
            quantity = value
            InternalInventoryChange.create_bin_internal_inventory_change(Shop.objects.get(id=data[0]), Product.objects.get(
                    product_sku=data[1][-17:]), batch_id, final_bin_id, initial_type[0], final_type[0], transaction_type,
                                                                         transaction_id, quantity)

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
                                                   bin=Bin.objects.filter(bin_id=bin_id, warehouse=warehouse)[0],
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
                                                    initial_stage, final_stage, inventory_type, final_type, quantity):
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
                                                            initial_type=inventory_type,
                                                            final_type=final_type)
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


def common_on_return_and_partial(shipment, flag):
    with transaction.atomic():
        putaway_qty = 0
        inv_type = {'E': InventoryType.objects.get(inventory_type='expired'),
                    'D': InventoryType.objects.get(inventory_type='damaged'),
                    'N': InventoryType.objects.get(inventory_type='normal')}
        for shipment_product in shipment.rt_order_product_order_product_mapping.all():
            for shipment_product_batch in shipment_product.rt_ordered_product_mapping.all():
                # first bin with non 0 inventory for a batch or last empty bin
                shipment_product_batch_bin_list = PickupBinInventory.objects.filter(
                    shipment_batch=shipment_product_batch).exclude(pickup__status='picking_cancelled')
                bin_id_for_input = None
                shipment_product_batch_bin_temp = None
                for shipment_product_batch_bin in shipment_product_batch_bin_list:
                    if shipment_product_batch_bin.bin.quantity == 0:
                        bin_id_for_input = shipment_product_batch_bin.bin
                        continue
                    else:
                        bin_id_for_input = shipment_product_batch_bin.bin
                        break
                batch_id = shipment_product_batch.batch_id
                warehouse = shipment_product_batch.rt_pickup_batch_mapping.last().warehouse
                putaway_user = shipment.last_modified_by
                if flag == "return":
                    putaway_qty = shipment_product_batch.returned_qty + shipment_product_batch.returned_damage_qty
                    if putaway_qty == 0:
                        continue
                    else:
                        product = shipment_product_batch.ordered_product_mapping.product
                        in_type_id = shipment.id
                        putaway_type_id = shipment.invoice_no
                        if shipment_product_batch.returned_qty > 0:
                            create_in(warehouse, batch_id, product, 'RETURN', in_type_id,  inv_type['N'],
                                                             shipment_product_batch.returned_qty,)
                            create_putaway(warehouse, product, batch_id, bin_id_for_input, inv_type['N'],
                                           'RETURNED', putaway_type_id, putaway_user,
                                           shipment_product_batch.returned_qty)
                        if shipment_product_batch.returned_damage_qty > 0:
                            create_in(warehouse, batch_id, product, 'RETURN', in_type_id,  inv_type['D'],
                                      shipment_product_batch.returned_damage_qty,)
                            create_putaway(warehouse, product, batch_id, bin_id_for_input, inv_type['D'],
                                           'RETURNED', putaway_type_id, putaway_user,
                                           shipment_product_batch.returned_damage_qty)

                elif flag == "partial_shipment":
                    partial_ship_qty = (shipment_product_batch.pickup_quantity - shipment_product_batch.quantity)
                    if partial_ship_qty <= 0:
                        continue
                    else:
                        expired_qty = shipment_product_batch.expired_qty
                        if expired_qty > 0:
                            create_putaway(warehouse, shipment_product_batch.pickup.sku, batch_id, bin_id_for_input,
                                           inv_type['E'], 'PAR_SHIPMENT', shipment.order.order_no, putaway_user, expired_qty)
                        damaged_qty = shipment_product_batch.damaged_qty
                        if damaged_qty > 0:
                            create_putaway(warehouse, shipment_product_batch.pickup.sku, batch_id, bin_id_for_input,
                                           inv_type['D'], 'PAR_SHIPMENT', shipment.order.order_no, putaway_user, damaged_qty)
                        rejected_qty = shipment_product_batch.rejected_qty
                        if rejected_qty > 0:
                            create_putaway(warehouse, shipment_product_batch.pickup.sku, batch_id, bin_id_for_input,
                                           inv_type['N'], 'PAR_SHIPMENT', shipment.order.order_no, putaway_user, rejected_qty)
                else:
                    pass


def create_in(warehouse, batch_id, sku, in_type, in_type_id, inventory_type, quantity):
    iin, create = In.objects.get_or_create(warehouse=warehouse,
                                           in_type=in_type, in_type_id=in_type_id,
                                           sku=sku,
                                           batch_id=batch_id,
                                           inventory_type=inventory_type,
                                           defaults={'quantity': quantity,
                                                     'expiry_date': get_expiry_date_db(batch_id)})


def create_putaway(warehouse, sku, batch_id, bin, inventory_type, putaway_type, putaway_type_id, putaway_user, quantity):
    pu, _ = Putaway.objects.update_or_create(warehouse=warehouse,
                                             putaway_type=putaway_type,
                                             putaway_type_id=putaway_type_id,
                                             sku=sku,
                                             batch_id=batch_id,
                                             inventory_type=inventory_type,
                                             defaults={'quantity': quantity,
                                                       'status': Putaway.PUTAWAY_STATUS_CHOICE.NEW,
                                                       'putaway_quantity': 0})
    # PutawayBinInventory.objects.update_or_create(warehouse=warehouse,
    #                                              sku=sku,
    #                                              batch_id=batch_id,
    #                                              putaway_type=putaway_type,
    #                                              putaway=pu, bin=bin,
    #                                              putaway_status=False,
    #                                              defaults={'putaway_quantity': quantity})


def create_batch_id(sku, expiry_date):
    """

    :param sku: product sku
    :param expiry_date: expiry date
    :return:
    """
    try:
        sku = sku.lstrip('D')
        try:
            batch_id = '{}{}'.format(sku, datetime.datetime.strptime(expiry_date, '%d-%m-%y').strftime('%d%m%y'))

        except:
            try:
                batch_id = '{}{}'.format(sku, datetime.datetime.strptime(expiry_date, '%d-%m-%Y').strftime('%d%m%y'))
            except:
                try:
                    batch_id = '{}{}'.format(sku, datetime.datetime.strptime(expiry_date, '%d/%m/%Y').strftime('%d%m%y'))
                except:
                    batch_id = '{}{}'.format(sku, datetime.datetime.strptime(expiry_date, '%d/%m/%y').strftime('%d%m%y'))
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


def get_expiry_date_db(batch_id):
    expiry_date_db=None
    if batch_id is not None:
        if len(batch_id) == 23:
            expiry_date = batch_id[-6:-4] + '/' + batch_id[-4:-2] + '/20' + batch_id[-2:]

        if len(batch_id) == 25:
            expiry_date = batch_id[-8:-6] + '/' + batch_id[-6:-4] + '/' + batch_id[-4:]
        expiry_date_db = datetime.datetime.strptime(expiry_date, '%d/%m/%Y').strftime('%Y-%m-%d')
    return expiry_date_db

def get_manufacturing_date(batch_id):
    in_entry = In.objects.filter(in_type='GRN', batch_id=batch_id).last()
    return in_entry.manufacturing_date if in_entry else None

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

def cancel_ordered(request, obj, initial_state, bin_id):
    if obj.putaway.putaway_quantity == 0:
        obj.putaway.putaway_quantity = obj.putaway_quantity
    else:
        obj.putaway.putaway_quantity = obj.putaway_quantity + obj.putaway.putaway_quantity
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
    quantity = obj.putaway_quantity
    transaction_type = 'put_away_type'
    transaction_id = obj.putaway_id
    try:
        initial_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
        final_bin_id = Bin.objects.get(bin_id=bin_id.bin.bin_id, warehouse=obj.warehouse)
    except:
        raise forms.ValidationError("Bin Id is not associate with this Warehouse.")
    batch_id = obj.batch_id
    bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse, bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                              batch_id=batch_id,
                                              inventory_type=type_normal, in_stock=True).last()
    if bin_inv_obj:
        bin_quantity = bin_inv_obj.quantity
        final_quantity = bin_quantity + quantity
        bin_inv_obj.quantity = final_quantity
        bin_inv_obj.save()
    else:

        BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku, batch_id=batch_id,
                                           inventory_type=type_normal, quantity=quantity, in_stock=True)

    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(obj.warehouse, obj.sku,
                                                                                      type_normal,
                                                                                      state_total_available,
                                                                                      quantity,
                                                                                      transaction_type,
                                                                                      transaction_id)
    BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                              batch_id=batch_id,
                                              initial_bin=Bin.objects.get(bin_id=initial_bin_id,
                                                                          warehouse=obj.warehouse),
                                              final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                        warehouse=obj.warehouse),
                                              initial_inventory_type=type_normal,
                                              final_inventory_type=type_normal,
                                              transaction_type=transaction_type,
                                              transaction_id=transaction_id,
                                              quantity=quantity)

    obj.putaway.putaway_user = request
    obj.putaway.save()
    obj.putaway_status = True
    obj.save()


def putaway_repackaging(request, obj, initial_stage, bin_id):
    with transaction.atomic():
        if obj.putaway.putaway_quantity == 0:
            obj.putaway.putaway_quantity = obj.putaway_quantity
        else:
            obj.putaway.putaway_quantity = obj.putaway_quantity + obj.putaway.putaway_quantity
        available_quantity = obj.putaway_quantity
        transaction_type = 'put_away_type'
        transaction_id = obj.putaway_id
        initial_type = InventoryType.objects.filter(inventory_type='new').last(),
        final_type = InventoryType.objects.filter(inventory_type='normal').last(),
        final_stage = InventoryState.objects.filter(inventory_state='total_available').last(),
        try:
            initial_bin_id = ''
            if obj.bin:
                initial_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
            final_bin_id = Bin.objects.get(bin_id=bin_id.bin.bin_id, warehouse=obj.warehouse)
        except:
            raise forms.ValidationError("Bin Id is not associate with this Warehouse.")
        quantity = available_quantity
        batch_id = obj.batch_id
        bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse, bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                                  batch_id=batch_id,
                                                  inventory_type=final_type[0], in_stock=True).last()
        if bin_inv_obj:
            bin_quantity = bin_inv_obj.quantity
            final_quantity = bin_quantity + quantity
            bin_inv_obj.quantity = final_quantity
            bin_inv_obj.save()
        else:

            BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku, batch_id=batch_id,
                                               inventory_type=final_type[0], quantity=quantity, in_stock=True)

        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
            obj.warehouse, obj.sku, final_type[0], final_stage[0], available_quantity,
            transaction_type, transaction_id)

        if initial_bin_id != '':
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
        else:
            BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                      batch_id=batch_id,
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


def cancel_shipment(request, obj, initial_stage, shipment_obj, bin_id, inventory_type):
    if obj.putaway.putaway_quantity == 0:
        obj.putaway.putaway_quantity = obj.putaway_quantity
    else:
        obj.putaway.putaway_quantity = obj.putaway_quantity + obj.putaway.putaway_quantity
    obj.putaway.putaway_user = request
    obj.putaway.save()
    transaction_type = 'put_away_type'
    transaction_id = obj.putaway_id
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    type_expired = InventoryType.objects.filter(inventory_type="expired").last()
    type_damaged = InventoryType.objects.filter(inventory_type="damaged").last()
    state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
    try:
        initial_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
        final_bin_id = Bin.objects.get(bin_id=bin_id.bin.bin_id, warehouse=obj.warehouse)
    except:
        raise forms.ValidationError("Bin Id is not associate with this Warehouse.")
    batch_id = obj.batch_id
    for i in shipment_obj:
        for shipped_obj in i.rt_ordered_product_mapping.all():
            if obj.sku_id == shipped_obj.bin.sku.product_sku:
                for pick_bin in shipped_obj.rt_pickup_batch_mapping.all():
                    if pick_bin.bin.bin.bin_id == obj.bin.bin.bin_id:
                        if inventory_type == type_expired:
                            expired_qty = shipped_obj.expired_qty
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
                                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                    obj.warehouse, obj.sku, type_expired, state_total_available,
                                    expired_qty, transaction_type, transaction_id)
                                BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                          batch_id=batch_id,
                                                                          initial_bin=Bin.objects.get(
                                                                              bin_id=initial_bin_id,
                                                                              warehouse=obj.warehouse),
                                                                          final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                    warehouse=obj.warehouse),
                                                                          initial_inventory_type=type_normal,
                                                                          final_inventory_type=type_expired,
                                                                          transaction_type=transaction_type,
                                                                          transaction_id=transaction_id,
                                                                          quantity=expired_qty)
                                deduct_quantity = expired_qty
                        elif inventory_type == type_damaged:
                            damaged_qty = shipped_obj.damaged_qty
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
                                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                    obj.warehouse, obj.sku, type_damaged, state_total_available,
                                    damaged_qty, transaction_type, transaction_id)
                                BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                          batch_id=batch_id,
                                                                          initial_bin=Bin.objects.get(
                                                                              bin_id=initial_bin_id,
                                                                              warehouse=obj.warehouse),
                                                                          final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                    warehouse=obj.warehouse),
                                                                          initial_inventory_type=type_normal,
                                                                          final_inventory_type=type_damaged,
                                                                          transaction_type=transaction_type,
                                                                          transaction_id=transaction_id,
                                                                          quantity=damaged_qty)
                                deduct_quantity = damaged_qty
                        elif inventory_type == type_normal:
                            rejected_qty = shipped_obj.rejected_qty
                            if rejected_qty > 0:
                                bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse,
                                                                          bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                                                          batch_id=batch_id,
                                                                          inventory_type=type_normal,
                                                                          in_stock=True).last()
                                if bin_inv_obj:
                                    bin_quantity = bin_inv_obj.quantity
                                    final_quantity = bin_quantity + rejected_qty
                                    bin_inv_obj.quantity = final_quantity
                                    bin_inv_obj.save()
                                else:

                                    BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin,
                                                                       sku=obj.sku,
                                                                       batch_id=batch_id,
                                                                       inventory_type=type_normal,
                                                                       quantity=rejected_qty,
                                                                       in_stock=True)
                                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                    obj.warehouse, obj.sku, type_normal, state_total_available,
                                    rejected_qty, transaction_type, transaction_id)
                                BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                          batch_id=batch_id,
                                                                          initial_bin=Bin.objects.get(
                                                                              bin_id=initial_bin_id,
                                                                              warehouse=obj.warehouse),
                                                                          final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                    warehouse=obj.warehouse),
                                                                          initial_inventory_type=type_normal,
                                                                          final_inventory_type=type_normal,
                                                                          transaction_type=transaction_type,
                                                                          transaction_id=transaction_id,
                                                                          quantity=rejected_qty)
                                deduct_quantity = rejected_qty

                        ordered_quantity = int(-deduct_quantity)
                        obj.putaway_status = True
                        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                            obj.warehouse, obj.sku, type_normal, initial_stage,
                            ordered_quantity,  transaction_type, transaction_id)
                        obj.putaway_status = True
                        obj.save()
                    else:
                        pass
            else:
                pass


def cancel_returned(request, obj, initial_stage, shipment_obj, bin_id, inventory_type):
    if obj.putaway.putaway_quantity == 0:
        obj.putaway.putaway_quantity = obj.putaway_quantity
    else:
        obj.putaway.putaway_quantity = obj.putaway_quantity + obj.putaway.putaway_quantity
    obj.putaway.putaway_user = request
    obj.putaway.save()
    transaction_type = 'put_away_type'
    transaction_id = obj.putaway_id
    type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    type_damaged = InventoryType.objects.filter(inventory_type="damaged").last()
    state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
    try:
        initial_bin_id = Bin.objects.get(bin_id=obj.bin.bin.bin_id, warehouse=obj.warehouse)
        final_bin_id = Bin.objects.get(bin_id=bin_id.bin.bin_id, warehouse=obj.warehouse)
    except:
        raise forms.ValidationError("Bin Id is not associate with this Warehouse.")
    batch_id = obj.batch_id
    for i in shipment_obj:
        for shipped_obj in i.rt_ordered_product_mapping.all():
            if obj.sku_id == shipped_obj.rt_pickup_batch_mapping.last().pickup.sku.product_sku:
                for pick_bin in shipped_obj.rt_pickup_batch_mapping.all():
                    if pick_bin.bin.bin.bin_id == obj.bin.bin.bin_id:
                        normal_qty = shipped_obj.returned_qty
                        returned_damaged_qty = shipped_obj.returned_damage_qty
                        if inventory_type == type_normal:
                            if normal_qty > 0:
                                bin_inv_obj = BinInventory.objects.filter(warehouse=obj.warehouse,
                                                                          bin__bin_id=bin_id.bin.bin_id, sku=obj.sku,
                                                                          batch_id=batch_id,
                                                                          inventory_type=type_normal,
                                                                          in_stock=True).last()
                                if bin_inv_obj:
                                    bin_quantity = bin_inv_obj.quantity
                                    final_quantity = bin_quantity + normal_qty
                                    bin_inv_obj.quantity = final_quantity
                                    bin_inv_obj.save()
                                else:

                                    BinInventory.objects.get_or_create(warehouse=obj.warehouse, bin=bin_id.bin, sku=obj.sku,
                                                                       batch_id=batch_id,
                                                                       inventory_type=type_normal, quantity=normal_qty,
                                                                       in_stock=True)
                                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                    obj.warehouse, obj.sku, type_normal, state_total_available,
                                    normal_qty, transaction_type, transaction_id)
                                BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                          batch_id=batch_id,
                                                                          initial_bin=Bin.objects.get(
                                                                              bin_id=initial_bin_id,
                                                                              warehouse=obj.warehouse),
                                                                          final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                    warehouse=obj.warehouse),
                                                                          initial_inventory_type=type_normal,
                                                                          final_inventory_type=type_normal,
                                                                          transaction_type=transaction_type,
                                                                          transaction_id=transaction_id,
                                                                          quantity=normal_qty)
                            deduct_quantity = normal_qty
                        elif inventory_type == type_damaged:
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

                                CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                                    obj.warehouse, obj.sku, type_damaged, state_total_available,
                                    returned_damaged_qty, transaction_type, transaction_id)
                                BinInternalInventoryChange.objects.create(warehouse_id=obj.warehouse.id, sku=obj.sku,
                                                                          batch_id=batch_id,
                                                                          initial_bin=Bin.objects.get(
                                                                              bin_id=initial_bin_id,
                                                                              warehouse=obj.warehouse),
                                                                          final_bin=Bin.objects.get(bin_id=final_bin_id,
                                                                                                    warehouse=obj.warehouse),
                                                                          initial_inventory_type=type_normal,
                                                                          final_inventory_type=type_damaged,
                                                                          transaction_type=transaction_type,
                                                                          transaction_id=transaction_id,
                                                                          quantity=returned_damaged_qty)

                            deduct_quantity = returned_damaged_qty
                        ordered_quantity = int(-deduct_quantity)

                        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                            obj.warehouse, obj.sku, type_normal, initial_stage, ordered_quantity,
                            transaction_type, transaction_id)
                        obj.putaway_status = True
                        obj.save()

                    else:
                        pass
            else:
                pass


def inventory_in_and_out(sh, bin_id, sku, batch_id, inv_type, inv_state, t, val, put_away_status, transaction_type_obj,
                         transaction_type, inventory_movement_type):
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
                                                                               bin_id=bin_id, warehouse=sh).last(),
                                                                               sku=sku,
                                                                               batch_id=batch_id,
                                                                               inventory_type=InventoryType.objects.filter(
                                                                                   inventory_type=inv_type).last(),
                                                                               in_stock=t)
    if bin_inventory_obj.exists():
        bin_inventory_obj = bin_inventory_obj.last()
        bin_inventory_obj.quantity = val
        bin_inventory_obj.save()
    else:
        BinInventory.objects.create(warehouse=sh, bin=Bin.objects.filter(bin_id=bin_id, warehouse=sh).last(), sku=sku,
                                    batch_id=batch_id, inventory_type=InventoryType.objects.filter(
                inventory_type=inv_type).last(), quantity=val, in_stock=t)
    if transaction_type == 'stock_correction_out_type':
        pass
    else:
        if put_away_status is True:
            PutawayBinInventory.objects.create(warehouse=sh, putaway=transaction_type_obj.last(),
                                               bin=BinInventory.objects.filter(bin__bin_id=bin_id, warehouse=sh).last(),
                                               putaway_quantity=val, putaway_status=True,
                                               sku=sku, batch_id=transaction_type_obj.last().batch_id,
                                               putaway_type=transaction_type_obj.last().putaway_type)
        else:
            PutawayBinInventory.objects.create(warehouse=sh, putaway=transaction_type_obj.last(),
                                               bin=BinInventory.objects.filter(bin__bin_id=bin_id, warehouse=sh).last(),
                                               putaway_quantity=val, putaway_status=False,
                                               sku=sku, batch_id=transaction_type_obj.last().batch_id,
                                               putaway_type=transaction_type_obj.last().putaway_type)

    transaction_id = transaction_type_obj.last().id
    initial_type = InventoryType.objects.filter(inventory_type='new').last(),
    final_type = InventoryType.objects.filter(inventory_type=inv_type).last(),
    final_stage = InventoryState.objects.filter(inventory_state='total_available').last(),

    CommonWarehouseInventoryFunctions.create_warehouse_inventory_stock_correction(sh, sku, inv_type, inv_state, val,
                                                                 True)
    WarehouseInternalInventoryChange.objects.create(warehouse=sh, sku=sku, transaction_type=transaction_type,
                                                    transaction_id=transaction_id, inventory_type=final_type[0],
                                                    inventory_state=final_stage[0], quantity=val)

    InternalInventoryChange.create_bin_internal_inventory_change(sh, transaction_type_obj[0].sku, batch_id, bin_id,
                                                                 initial_type[0], final_type[0], transaction_type,
                                                                 transaction_id, val)


def inventory_in_and_out_weight(warehouse_obj, bin_obj, product_obj, batch_id, inv_type, inventory_state, weight,
                                transaction_type, transaction_id):
    """

    :param warehouse_obj:
    :param bin_obj:
    :param batch_id:
    :param inv_type:
    :param inventory_state:
    :param product_obj:
    :param weight:
    :param transaction_id
    :param transaction_type
    :return:
    """
    bin_inventory_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(warehouse=warehouse_obj, bin=bin_obj,
                                                                               sku=product_obj, batch_id=batch_id,
                                                                               inventory_type=InventoryType.objects.filter(
                                                                                   inventory_type=inv_type).last(),
                                                                               in_stock=True)
    if bin_inventory_obj.exists():
        bin_inventory_obj = bin_inventory_obj.last()
        bin_inventory_obj.weight = weight
        bin_inventory_obj.save()
    else:
        BinInventory.objects.create(warehouse=warehouse_obj, bin=bin_obj, sku=product_obj, batch_id=batch_id,
                                    inventory_type=InventoryType.objects.filter(
                                        inventory_type=inv_type).last(), quantity=0, weight=weight, in_stock=True)

    initial_type = InventoryType.objects.filter(inventory_type='new').last(),
    final_type = InventoryType.objects.filter(inventory_type=inv_type).last(),
    final_stage = InventoryState.objects.filter(inventory_state='total_available').last(),

    CommonWarehouseInventoryFunctions.create_warehouse_inventory_stock_correction_weight(warehouse_obj, product_obj,
                                                                                         inv_type, inventory_state,
                                                                                         weight, True)
    WarehouseInternalInventoryChange.objects.create(warehouse=warehouse_obj, sku=product_obj,
                                                    transaction_type=transaction_type, transaction_id=transaction_id,
                                                    inventory_type=final_type[0], inventory_state=final_stage[0],
                                                    quantity=0, weight=weight)

    InternalInventoryChange.create_bin_internal_inventory_change(warehouse_obj, product_obj, batch_id, bin_obj.bin_id,
                                                                 initial_type[0], final_type[0], transaction_type,
                                                                 transaction_id, 0, weight)


def product_batch_inventory_update_franchise(warehouse, bin_obj, shipment_product_batch, initial_type, final_type,
                                             initial_stage, final_stage):
    """
        Add single delivered product batch to franchise shop Inventory after trip is closed. From new to normal, available
        warehouse: Franchise Shop / Buyer Shop
        bin_obj: Virtual default bin for Franchise Shop
        shipment_product_batch: OrderedProductBatch
    """

    if shipment_product_batch.delivered_qty > 0:
        sku = shipment_product_batch.ordered_product_mapping.product
        # batch_id = shipment_product_batch.batch_id
        default_expiry = datetime.date(int(config('FRANCHISE_IN_DEFAULT_EXPIRY_YEAR')), 1, 1)
        batch_id = '{}{}'.format(sku.product_sku, default_expiry.strftime('%d%m%y'))
        info_logger.info("Franchise Product Batch update after Trip. Shop: {}, Batch: {}, Shipment Product Batch Id: {}".
                         format(warehouse, batch_id, shipment_product_batch.id))
        quantity = shipment_product_batch.delivered_qty
        transaction_type = 'franchise_batch_in'
        transaction_id = shipment_product_batch.id
        franchise_inventory_in(warehouse, sku, batch_id, quantity, transaction_type, transaction_id, final_type,
                               initial_type, initial_stage, final_stage, bin_obj)


def franchise_inventory_in(warehouse, sku, batch_id, quantity, transaction_type, transaction_id, final_type,
                           initial_type, initial_stage, final_stage, bin_obj, shipped=True):
    manufacturing_date = get_manufacturing_date(batch_id)
    InCommonFunctions.create_only_in(warehouse, transaction_type, transaction_id, sku, batch_id, quantity,
                                     final_type[0],0, manufacturing_date)

    putaway = PutawayCommonFunctions.create_putaway(warehouse, transaction_type, transaction_id, sku, batch_id,
                                                    quantity, quantity, final_type[0])

    bin_inv_obj = BinInventory.objects.filter(warehouse=warehouse, bin=bin_obj, sku=sku,
                                              batch_id=batch_id, inventory_type=final_type[0], in_stock=True).last()
    if bin_inv_obj:
        bin_quantity = bin_inv_obj.quantity
        final_quantity = bin_quantity + quantity
        bin_inv_obj.quantity = final_quantity
        bin_inv_obj.save()
    else:
        bin_inv_obj = BinInventory.objects.create(warehouse=warehouse, bin=bin_obj, sku=sku, batch_id=batch_id,
                                    inventory_type=final_type[0], quantity=quantity, in_stock=True)

    PutawayBinInventory.objects.create(warehouse=warehouse, putaway=putaway, bin=bin_inv_obj, putaway_quantity=quantity,
                                       putaway_status=True, sku=sku, batch_id=batch_id, putaway_type=transaction_type)

    BinInternalInventoryChange.objects.create(warehouse_id=warehouse.id, sku=sku, batch_id=batch_id, final_bin=bin_obj,
                                              initial_inventory_type=initial_type[0],
                                              final_inventory_type=final_type[0],
                                              transaction_type=transaction_type, transaction_id=transaction_id,
                                              quantity=quantity)
    CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
        warehouse, sku, final_type[0], final_stage[0], quantity, transaction_type, transaction_id)
    if transaction_type == 'franchise_returns'and shipped:
        CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
            warehouse, sku, initial_type[0], initial_stage[0], quantity * -1, transaction_type, transaction_id)


def update_visibility(shop,product,visible):
    WarehouseInventory.objects.filter(warehouse=shop,sku=product,inventory_state=InventoryState.objects.filter(
                inventory_state='total_available').last(), inventory_type=InventoryType.objects.filter(
                inventory_type='normal').last()).update(visible=visible)


def update_visibility_bulk(shop_id):
    shop = Shop.objects.filter(pk=shop_id).last()
    products = WarehouseInventory.objects.filter(warehouse=shop,inventory_state=InventoryState.objects.filter(
                inventory_state='total_available').last(), inventory_type=InventoryType.objects.filter(
                inventory_type='normal').last())
    parent_list = []
    for product in products:
        if product.sku.parent_product.id in parent_list:
            continue
        visibility_changes = get_visibility_changes(shop, product.sku)
        if visibility_changes:
            for prod_id, visibility in visibility_changes.items():
                sibling = Product.objects.filter(pk=prod_id).last()
                print(sibling,visibility)
                update_visibility(shop, sibling, visibility)
        parent_list.append(product.sku.parent_product.id)


def get_stock_available_brand_list(warehouse):
    """
    Takes in the Shop instance and returns the list of distinct brands for which normal type inventory is available
    """
    return WarehouseInventory.objects.filter(warehouse=warehouse, sku__status='active', visible=True, quantity__gt=0,
                                             inventory_state=InventoryState.objects.filter(
                                                 inventory_state='total_available').last(),
                                             inventory_type=InventoryType.objects.filter(
                                                 inventory_type='normal').last()) \
        .values_list('sku__parent_product__parent_brand', flat=True).distinct()


def get_stock_available_category_list(warehouse=None):
    """
    Takes in the Shop instance(optional) and returns the list of distinct categories for which normal type inventory is available
    """
    query_set = WarehouseInventory.objects.filter(sku__status='active', visible=True, quantity__gt=0,
                                             inventory_state=InventoryState.objects.filter(
                                                 inventory_state='total_available').last(),
                                             inventory_type=InventoryType.objects.filter(
                                                 inventory_type='normal').last())
    if warehouse:
        query_set = query_set.filter(warehouse=warehouse)
    return query_set.values_list('sku__parent_product__parent_product_pro_category__category', flat=True).distinct()


def is_product_not_eligible(product_id):
    return Product.objects.filter(id=product_id, repackaging_type='packing_material').exists()


def get_inventory_in_stock(warehouse, parent_product):
    """
    Return cumulative inventory available of all the child products for given parent and warehouse
    """
    inventory_type_normal = InventoryType.objects.filter(inventory_type='normal').last()
    child_products = parent_product.product_parent_product.all()
    child_product_ids = [p.id for p in child_products]
    stock_dict = get_stock(warehouse, inventory_type_normal, child_product_ids)
    total_inventory = sum(stock_dict.values()) if stock_dict.values() else 0
    return total_inventory


def get_earliest_expiry_date(product, shop, inventory_type, is_discounted):
    bin_data = BinInventory.objects.filter(Q(warehouse=shop), Q(sku=product), Q(inventory_type=inventory_type),
                                           quantity__gt=0
                                           )
    if is_discounted:
        bin_data = bin_data.filter(sku__product_type=Product.PRODUCT_TYPE_CHOICE.DISCOUNTED)
    earliest_expiry_date = None
    for data in bin_data:
        exp_date_str = get_expiry_date(batch_id=data.batch_id)
        exp_date = datetime.datetime.strptime(exp_date_str, "%d/%m/%Y")
        if not earliest_expiry_date:
            earliest_expiry_date = exp_date
        elif exp_date < earliest_expiry_date:
            earliest_expiry_date = exp_date
    return earliest_expiry_date.strftime('%d-%m-%Y') if earliest_expiry_date is not None else None


def get_response(msg, data=None, success=False, status_code=status.HTTP_200_OK):
    """
        General Response For API
    """
    if success:
        result = {"is_success": True, "message": msg, "response_data": data}
    else:
        if data:
            result = {"is_success": True,
                      "message": msg, "response_data": data}
        else:
            status_code = status.HTTP_406_NOT_ACCEPTABLE
            result = {"is_success": False, "message": msg, "response_data": []}

    return Response(result, status=status_code)


def serializer_error(serializer):
    """
        Serializer Error Method
    """
    errors = []
    for field in serializer.errors:
        for error in serializer.errors[field]:
            if 'non_field_errors' in field:
                result = error
            else:
                result = ''.join('{} : {}'.format(field, error))
            errors.append(result)
    return errors[0]


def get_logged_user_wise_query_set(user, queryset):
    '''
        GET Logged-in user wise queryset for grouped puaways based on criteria that matches
    '''
    if user.has_perm('wms.can_have_zone_warehouse_permission'):
        queryset = queryset.filter(zone__in=list(Zone.objects.filter(
            warehouse_id=user.shop_employee.all().last().shop_id).values_list('id', flat=True)))
    elif user.has_perm('wms.can_have_zone_supervisor_permission'):
        queryset = queryset.filter(zone__in=list(Zone.objects.filter(supervisor=user).values_list('id', flat=True)))
    elif user.has_perm('wms.can_have_zone_coordinator_permission'):
        queryset = queryset.filter(zone__in=list(Zone.objects.filter(coordinator=user).values_list('id', flat=True)))
    elif user.groups.filter(name='Putaway').exists():
        queryset = queryset.filter(putaway_user=user)
    return queryset


class ZoneCommonFunction(object):

    @classmethod
    def create_zone(cls, warehouse, supervisor, coordinator, putaway_users):
        Zone.objects.create(warehouse=warehouse, supervisor=supervisor, coordinator=coordinator,
                            putaway_users=putaway_users)

    @classmethod
    def update_putaway_users(cls, zone, putaway_users):
        """
            Update Putaway users of the Zone
        """
        zone.putaway_users.clear()
        if putaway_users:
            for user in putaway_users:
                zone.putaway_users.add(user)
        zone.save()

    @ classmethod
    def update_picker_users(cls, zone, picker_users):
        """
        Update Picker users of the Zone
        """
        zone.picker_users.clear()
        if picker_users:
            for user in picker_users:
                zone.picker_users.add(user)
        zone.save()


class WarehouseAssortmentCommonFunction(object):

    @classmethod
    def create_warehouse_assortment(cls, validated_data):
        csv_file = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        csv_file_header_list = next(csv_file)  # headers of the uploaded csv file
        # Converting headers into lowercase
        csv_file_headers = [str(ele).split(' ')[0].strip().lower() for ele in csv_file_header_list]
        uploaded_data_by_user_list = get_csv_file_data(csv_file, csv_file_headers)
        try:
            info_logger.info('Method Start to create Beat Planning')
            warehouse = Shop.objects.get(id=uploaded_data_by_user_list[0]['warehouse_id'])
            for row in uploaded_data_by_user_list:
                warehouse_assortment_object, created = WarehouseAssortment.objects.get_or_create(
                    warehouse=warehouse, product=ParentProduct.objects.filter(
                        parent_id=str(row['product_id']).strip()).last(), zone_id=int(row['zone_id']))
            info_logger.info("Method complete to create Warehouse Assortment from csv file")
        except Exception as e:
            import traceback; traceback.print_exc()
            error_logger.info(f"Something went wrong, while working with create Warehouse Assortment  "
                              f" + {str(e)}")

    @classmethod
    def get_product_zone(cls, warehouse, sku):
        zone = None
        if WarehouseAssortment.objects.filter(warehouse=warehouse, product=sku.parent_product).exists():
            zone = WarehouseAssortment.objects.filter(warehouse=warehouse, product=sku.parent_product).last().zone
        return zone

def get_sku_from_batch(batch_id):
    sku = None
    if not sku:
        sku_id = batch_id[:-6]
        sku = Product.objects.filter(product_sku=sku_id).last()
    return sku