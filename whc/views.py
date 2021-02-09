import json
import logging

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from accounts.models import User
from addresses.models import Address
from global_config.views import get_config
from gram_to_brand.common_functions import get_grned_product_qty_by_grn_id
from retailer_backend.common_function import checkNotShopAndMapping, getShopMapping
from retailer_to_sp.models import Order, Cart, CartProductMapping
from shops.models import Shop
from whc.models import AutoOrderProcessing, SourceDestinationMapping
from wms.common_functions import get_stock, OrderManagement
from wms.models import InventoryType, OrderReserveRelease

info_logger = logging.getLogger('file-info')

class AutoOrderProcessor:
    type_normal = InventoryType.objects.filter(inventory_type="normal").last()

    def __init__(self, retailer_shop, user):
        self.retailer_shop = retailer_shop
        self.user = user

    @transaction.atomic
    def add_to_cart(self, auto_processing_entry):
        """
        Takes GRN ID and created Order for all the GRNed products
        """
        product_quantity_dict = get_grned_product_qty_by_grn_id(auto_processing_entry.grn_id)
        if self.retailer_shop is None:
            info_logger.info("WarehouseConsolidation|place_order_by_grn| retailer shop is not initialised")
            return
        if checkNotShopAndMapping(self.retailer_shop.id):
            info_logger.info("WarehouseConsolidation|place_order_by_grn| Retailer Shop or Shop Mapping does not exist")
            return
        parent_mapping = getShopMapping(self.retailer_shop)
        available_stock = get_stock(parent_mapping.parent, AutoOrderProcessor.type_normal,
                                    product_quantity_dict.keys())
        cart = self.__add_products_to_cart(parent_mapping.parent, parent_mapping.retailer, product_quantity_dict,
                                         available_stock)
        info_logger.info("WarehouseConsolidation|place_order_by_grn| Cart Generated, cart id-{}".format(cart.id))
        auto_processing_entry.cart=cart
        return auto_processing_entry

    @transaction.atomic
    def reserve_order(self, auto_processing_entry):
        product_quantity_dict = {cp.cart_product_id:cp.qty for cp in CartProductMapping.objects.filter(cart=auto_processing_entry.cart)}
        self.__reserve_cart(auto_processing_entry.cart, product_quantity_dict)
        info_logger.info("WarehouseConsolidation|place_order_by_grn| Cart Reserved, cart id-{}".format(auto_processing_entry.cart_id))
        return auto_processing_entry

    @transaction.atomic
    def place_order(self, auto_processing_entry):
        order = self.__place_order(auto_processing_entry.cart)
        auto_processing_entry.order = order
        info_logger.info("WarehouseConsolidation|place_order_by_grn| Order Placed, order id-{}"
                         .format(auto_processing_entry.order_id))
        return auto_processing_entry

    def __place_order(self, cart):
        order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=cart.seller_shop,
                                                               transaction_id=cart.order_id,
                                                               warehouse_internal_inventory_release=None,
                                                               ).last()
        if order_reserve_obj is None:
            info_logger.info(
                "WarehouseConsolidation|place_order_by_grn|place_order|Order Reserve Entry not found, order id-{}"
                    .format(cart.order_id))
            return False
        order = Order.objects.create(last_modified_by=self.user, ordered_by=self.user, ordered_cart=cart,
                                        order_no=cart.order_id)

        order.billing_address = Address.objects.filter(shop_name=cart.buyer_shop, address_type='billing').last()
        order.shipping_address = Address.objects.filter(shop_name=cart.buyer_shop, address_type='shipping').last()
        order.buyer_shop = cart.buyer_shop
        order.seller_shop = cart.seller_shop
        order.total_tax_amount = 0.0
        order.order_status = Order.ORDERED
        order.save()
        cart.cart_status = 'ordered'
        cart.save()
        info_logger.info(
            "WarehouseConsolidation|place_order_by_grn|place_order|Order Created, order id-{}".format(cart.order_id))

        sku_id = [i.cart_product.id for i in cart.rt_cart_list.all()]
        reserved_args = json.dumps({
            'shop_id': cart.seller_shop_id,
            'transaction_id': cart.order_id,
            'transaction_type': 'ordered',
            'order_status': order.order_status
        })
        order_result = OrderManagement.release_blocking_from_order(reserved_args, sku_id)
        if order_result is False:
            order.delete()
            info_logger.info("WarehouseConsolidation|place_order_by_grn|place_order|"
                             "Blocking could not be released, order deleted, order id-{}".format(cart.order_id))
            return False
        info_logger.info(
            "WarehouseConsolidation|place_order_by_grn|place_order|Blocking released, cart id-{}".format(cart.id))
        return order

    def __reserve_cart(self, cart, product_quantity_dict):
        """Creates entry in order reserve release for each product in the cart"""
        reserved_args = json.dumps({
            'shop_id': cart.seller_shop_id,
            'transaction_id': cart.order_id,
            'products': product_quantity_dict,
            'transaction_type': 'reserved'
        })
        OrderManagement.create_reserved_order(reserved_args)

    def __add_products_to_cart(self, seller_shop, buyer_shop, product_quantity_dict, available_stock):
        "Creates cart and adds the product in created cart"
        cart = Cart.objects.create(last_modified_by=self.user, cart_status='active', cart_type='AUTO', approval_status=False,
                    seller_shop=seller_shop, buyer_shop=buyer_shop)
        info_logger.info("WarehouseConsolidation|add_products_to_cart|Cart Created, cart id-{}, order id-{}"
                         .format(cart.id, cart.order_id))
        for product_id, qty in product_quantity_dict.items():
            cart_mapping = CartProductMapping.objects.create(cart=cart, cart_product_id=product_id)
            available_qty = available_stock.get(product_id, 0)
            info_logger.info("WarehouseConsolidation|add_products_to_cart|product id-{}, grned qty-{}, available qty-{}"
                             .format(product_id, qty, available_qty))
            if available_qty <= 0:
                continue
            if qty > available_qty:
                qty = available_qty
            cart_mapping.qty = qty
            cart_mapping.no_of_pieces = qty
            cart_mapping.save()
            info_logger.info("WarehouseConsolidation|add_products_to_cart|product id-{}, cart id-{}, qty added-{}"
                             .format(product_id, available_qty, cart.id, qty))
        return cart


def process_auto_order():
    is_wh_consolidation_on = get_config('is_wh_consolidation_on', False)
    if not is_wh_consolidation_on:
        return
    source_wh_id = get_config('wh_consolidation_source')
    if source_wh_id is None:
        info_logger.info("process_auto_order|wh_consolidation_source is not defined")
        return
    source_wh = Shop.objects.filter(pk=source_wh_id).last()
    if source_wh is None:
        info_logger.info("process_auto_order|no warehouse found with id -{}".format(source_wh_id))
        return
    wh_mapping = SourceDestinationMapping.objects.filter(source_wh=source_wh)
    if not wh_mapping.exists():
        info_logger.info("process_auto_order|no mapping found for this warehouse-{}".format(source_wh))
        return
    entries_to_process = AutoOrderProcessing.objects.filter(
                                            ~Q(state=AutoOrderProcessing.ORDER_PROCESSING_STATUS.DELIVERED),
                                            grn_warehouse=source_wh)
    if entries_to_process.count() == 0:
        info_logger.info("process_auto_order| no entry to process")
        return

    retailer_shop = wh_mapping.last().retailer_shop
    system_user = User.objects.filter(pk=9).last()
    order_processor = AutoOrderProcessor(retailer_shop, system_user)
    info_logger.info("process_auto_order|STARTED")
    for entry in entries_to_process:
        try:
            while True:
                current_state = entry.state
                info_logger.info("process_auto_order|GRN ID-{}, current state-{}".format(entry.grn_id, current_state))
                next_state = process_next(order_processor, entry)
                if current_state == next_state:
                    info_logger.info("process_auto_order|GRN ID-{}, could not move ahead".format(entry.grn_id))
                    break
                if next_state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.DELIVERED:
                    info_logger.info("process_auto_order|GRN ID-{}, moved to delivered state".format(entry.grn_id))
                    break
                info_logger.info("process_auto_order|GRN ID-{}, current state-{}".format(entry.grn_id, next_state))
        except Exception as e:
            info_logger.error("process_auto_order|error while processing GRN ID-{}, current state-{}"
                              .format(entry.grn_id, entry.state))
            info_logger.exception(e)
        info_logger.info("process_auto_order|COMPLETED")


def process_next(order_processor, entry_to_process):
    if entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.PUTAWAY:
        entry_to_process = order_processor.add_to_cart(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.CART_CREATED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.CART_CREATED:
        entry_to_process = order_processor.reserve_order(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.RESERVED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.RESERVED:
        entry_to_process = order_processor.place_order(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.ORDERED
    entry_to_process.save()
    return entry_to_process.state