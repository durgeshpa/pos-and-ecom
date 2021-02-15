import json
import logging

from django.db import transaction
from django.db.models import Q, TextField
from django.db.models.functions import Cast, datetime
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from django.utils import timezone

from accounts.models import User
from addresses.models import Address
from global_config.views import get_config
from gram_to_brand.common_functions import get_grned_product_qty_by_grn_id
from retailer_backend.common_function import checkNotShopAndMapping, getShopMapping
from retailer_to_sp.models import Order, Cart, CartProductMapping, PickerDashboard, generate_picklist_id, \
    populate_data_on_qc_pass, OrderedProductMapping, OrderedProduct, OrderedProductBatch
from shops.models import Shop
from whc.models import AutoOrderProcessing, SourceDestinationMapping
from wms.common_functions import get_stock, OrderManagement, PutawayCommonFunctions, InCommonFunctions, \
    CommonPickupFunctions, CommonPickBinInvFunction, InternalInventoryChange, CommonWarehouseInventoryFunctions, \
    CommonBinInventoryFunctions, get_expiry_date
from wms.models import InventoryType, OrderReserveRelease, PutawayBinInventory, InventoryState, BinInventory, \
    PickupBinInventory, Pickup

from gram_to_brand.models import GRNOrder,Cart as POCarts, CartProductMapping as POCartProductMappings
from brand.models import Brand, Vendor
from addresses.models import State, Address
from products.models import Product, ParentProduct, ProductVendorMapping
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
        auto_processing_entry.retailer_shop = self.retailer_shop
        return auto_processing_entry

    @transaction.atomic
    def reserve_order(self, auto_processing_entry):
        product_quantity_dict = {cp.cart_product_id: cp.qty for cp in
                                 CartProductMapping.objects.filter(cart=auto_processing_entry.cart)}
        self.__reserve_cart(auto_processing_entry.cart, product_quantity_dict)
        info_logger.info("WarehouseConsolidation|place_order_by_grn| Cart Reserved, cart id-{}".format(
            auto_processing_entry.cart_id))
        return auto_processing_entry

    @transaction.atomic
    def place_order(self, auto_processing_entry):
        order = self.__place_order(auto_processing_entry.cart)
        auto_processing_entry.order = order
        info_logger.info("WarehouseConsolidation|place_order_by_grn| Order Placed, order id-{}"
                         .format(auto_processing_entry.order_id))
        return auto_processing_entry

    @transaction.atomic
    def assign_picker(self, auto_processing_entry):
        picker_dashboard_obj = PickerDashboard.objects.filter(order=auto_processing_entry.order,
                                                              picking_status="picking_pending").last()
        if picker_dashboard_obj is None:
            info_logger.info("WarehouseConsolidation|assign_picker| picker dashboard entry does not exists,"
                             " order id-{}"
                             .format(auto_processing_entry.order.order_no))
            raise Exception("Picker could not be assigned")
        picker_dashboard_obj.picker_boy = self.user
        picker_dashboard_obj.picking_status = PickerDashboard.PICKING_ASSIGNED
        picker_dashboard_obj.save()
        info_logger.info("WarehouseConsolidation|assign_picker| picker assigned, order id-{}"
                         .format(auto_processing_entry.order.order_no))
        return auto_processing_entry

    @transaction.atomic
    def complete_pickup(self, auto_processing_entry):
        order_no = auto_processing_entry.order.order_no
        info_logger.info("WarehouseConsolidation|complete_pickup| Started, order id-{}".format(order_no))
        self.__complete_pickup(order_no)
        info_logger.info("WarehouseConsolidation|complete_pickup| Completed, order id-{}".format(order_no))
        picker_dashboard_obj = PickerDashboard.objects.filter(order=auto_processing_entry.order,
                                                              picking_status="picking_assigned").last()
        picker_dashboard_obj.picking_status = 'picking_complete'
        picker_dashboard_obj.save()
        info_logger.info("WarehouseConsolidation|assign_picker| picker dashboard updated, order id-{}"
                         .format(auto_processing_entry.order.order_no))
        auto_processing_entry.order.order_status = Order.PICKING_COMPLETE
        auto_processing_entry.order.save()
        info_logger.info("WarehouseConsolidation|complete_pickup| Order Status Updated, order id-{}, status-{}"
                         .format(order_no, Order.PICKING_COMPLETE))
        return auto_processing_entry


    @transaction.atomic
    def create_shipment(self, auto_processing_entry):

        info_logger.info("WarehouseConsolidation|create_shipment|Started, order id-{}"
                         .format(auto_processing_entry.order.id))
        self.__create_shipment(auto_processing_entry.cart, auto_processing_entry.order)
        info_logger.info("WarehouseConsolidation|create_shipment|Shipment Created, order id-{}"
                         .format(auto_processing_entry.order.id))
        return auto_processing_entry



    @transaction.atomic
    def shipment_qc(self, auto_processing_entry):

        info_logger.info("WarehouseConsolidation|shipment_qc|Started, order id-{}"
                         .format(auto_processing_entry.order.id))
        self.__shipment_qc(auto_processing_entry.order)
        info_logger.info("WarehouseConsolidation|shipment_qc|QC Done, order id-{}"
                         .format(auto_processing_entry.order.id))
        return auto_processing_entry

    def __shipment_qc(self, order):
        shipments = OrderedProduct.objects.filter(order=order)
        if shipments.exists():
            shipments.update(shipment_status=OrderedProduct.READY_TO_SHIP)
            return
        info_logger.info("WarehouseConsolidation|shipment_qc|No Shipment found, order id-{}".format(order.id))
        raise Exception("Exception|WarehouseConsolidation|shipment_qc|Shipment QC could not be done")


    def __create_shipment(self, cart, order):
        shipment = OrderedProduct(order=order)
        shipment.save()
        info_logger.info("WarehouseConsolidation|create_shipment|Shipment Object Created, shipment id-{}"
                         .format(shipment.id))
        cart_products = CartProductMapping.objects.values('cart_product', 'cart_product__product_name',
                                                          'cart_product__product_sku', 'no_of_pieces') \
            .filter(cart_id=cart.id)
        for item in cart_products:
            pick_up_obj = Pickup.objects.filter(sku_id=item['cart_product__product_sku'],
                                                pickup_type_id=order.order_no) \
                .exclude(status='picking_cancelled').last()
            OrderedProductMapping.objects.create(ordered_product=shipment, product_id=item['cart_product'],
                                                 shipped_qty=pick_up_obj.pickup_quantity,
                                                 picked_pieces=pick_up_obj.pickup_quantity)

            pick_bin_inv = PickupBinInventory.objects.filter(pickup=pick_up_obj)
            for i in pick_bin_inv:
                ordered_product_mapping = shipment.rt_order_product_order_product_mapping.filter(
                    product_id=pick_up_obj.sku.id).last()
                shipment_product_batch = OrderedProductBatch.objects.create(
                    batch_id=i.batch_id,
                    bin_ids=i.bin.bin.bin_id,
                    pickup_inventory=i,
                    ordered_product_mapping=ordered_product_mapping,
                    pickup=i.pickup,
                    bin=i.bin,  # redundant
                    quantity=i.pickup_quantity,
                    pickup_quantity=i.pickup_quantity,
                    expiry_date=get_expiry_date(i.batch_id),
                    delivered_qty=ordered_product_mapping.delivered_qty,
                    ordered_pieces=i.quantity
                )
                i.shipment_batch = shipment_product_batch
                i.save()
            info_logger.info("WarehouseConsolidation|create_shipment|Shipment Product Mapping Added, "
                             "shipment id-{}, sku-{}"
                             .format(shipment.id, pick_up_obj.sku.id))

    def __complete_pickup(self, order_no):
        state_picked = InventoryState.objects.filter(inventory_state='picked').last()
        state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()
        state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()
        tr_type = "picked"
        pickup_bin_inventory_objects = PickupBinInventory.objects.filter(pickup__pickup_type_id=order_no,
                                                                         pickup__status='picking_assigned')
        for pbi in pickup_bin_inventory_objects:
            tr_id = pbi.pickup_id
            warehouse = pbi.bin.warehouse
            sku = pbi.bin.sku
            inventory_type = pbi.bin.inventory_type
            CommonBinInventoryFunctions.deduct_to_be_picked_from_bin(pbi.quantity, pbi.bin)

            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                warehouse, sku, inventory_type, state_to_be_picked, -1 * pbi.quantity, tr_type, tr_id)

            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                warehouse, sku, inventory_type, state_total_available, -1 * pbi.quantity, tr_type, tr_id)

            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                warehouse, sku, inventory_type, state_picked, pbi.quantity, tr_type, tr_id)

            pbi.pickup_quantity = pbi.quantity
            pbi.last_picked_at = timezone.now()
            pbi.save()
            Pickup.objects.filter(id=tr_id).update(pickup_quantity=pbi.quantity, status='picking_complete')
            info_logger.info("WarehouseConsolidation|complete_pickup| Picking done |order id-{}, sku-{}"
                             .format(order_no, sku))

    @transaction.atomic
    def generate_picklist(self, auto_processing_entry):
        in_ids = InCommonFunctions.get_filtered_in(in_type='GRN', in_type_id=auto_processing_entry.grn.grn_id) \
            .annotate(idc=Cast('pk', TextField())) \
            .values_list('idc', flat=True)
        putaway_bin_inventories = PutawayBinInventory.objects.filter(putaway__putaway_type='GRN',
                                                                     putaway__putaway_type_id__in=in_ids)
        putaway_batch_bin_dict = {
            pbi.sku_id: {'batch_id': pbi.batch_id, 'bin_id': pbi.bin_id, 'qty': pbi.putaway_quantity}
            for pbi in putaway_bin_inventories}
        self.__generate_picklist(auto_processing_entry.cart, auto_processing_entry.order, putaway_batch_bin_dict)
        info_logger.info("WarehouseConsolidation|generate_picklist| Picklist Generated, order id-{}"
                         .format(auto_processing_entry.order_id))
        auto_processing_entry.order.order_status = 'PICKUP_CREATED'
        auto_processing_entry.order.save()
        info_logger.info("WarehouseConsolidation|generate_picklist| Order Status Changed | order id-{}, status-{}"
                         .format(auto_processing_entry.order.order_no, auto_processing_entry.order.order_status))
        PickerDashboard.objects.create(order=auto_processing_entry.order, picking_status="picking_pending",
                                       picklist_id=generate_picklist_id("00"))
        info_logger.info("WarehouseConsolidation|generate_picklist| Picker Dashboard entry created | order id-{}"
                         .format(auto_processing_entry.order.order_no))
        return auto_processing_entry

    def __generate_picklist(self, cart, order, sku_bin_dict):
        state_to_be_picked = InventoryState.objects.filter(inventory_state='to_be_picked').last()
        state_ordered = InventoryState.objects.filter(inventory_state='ordered').last()
        type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        shop = Shop.objects.filter(id=order.seller_shop.id).last()
        tr_type = "pickup_created"
        for order_product in order.ordered_cart.rt_cart_list.all():
            pickup_object = CommonPickupFunctions.create_pickup_entry(shop, 'Order', order.order_no,
                                                                      order_product.cart_product,
                                                                      order_product.no_of_pieces,
                                                                      'pickup_creation', type_normal)

            tr_id = pickup_object.pk
            sku_id = pickup_object.sku_id
            batch_id = sku_bin_dict[sku_id]['batch_id']
            bin_id = sku_bin_dict[sku_id]['bin_id']
            qty_to_be_picked = order_product.no_of_pieces
            bin_inventory_obj = BinInventory.objects.filter(id=bin_id).last()
            if bin_inventory_obj is None:
                info_logger.info("WarehouseConsolidation|generate_picklist| BinInventory Object does not exists| "
                                 "order id-{}, sku-{}, bin-{}, warehouse-{}"
                                 .format(order.order_no, sku_id, bin_id, shop.id))
                raise Exception('Picklist Generation Failed')

            bin_inventory_obj.quantity = bin_inventory_obj.quantity - qty_to_be_picked
            bin_inventory_obj.to_be_picked_qty += qty_to_be_picked
            bin_inventory_obj.save()

            CommonPickBinInvFunction.create_pick_bin_inventory(shop, pickup_object, batch_id, bin_inventory_obj,
                                                               quantity=qty_to_be_picked,
                                                               bin_quantity=bin_inventory_obj.quantity,
                                                               pickup_quantity=None)
            InternalInventoryChange.create_bin_internal_inventory_change(shop, pickup_object.sku, batch_id,
                                                                         bin_inventory_obj.bin,
                                                                         type_normal, type_normal,
                                                                         tr_type, tr_id, qty_to_be_picked)

            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                shop, pickup_object.sku, type_normal, state_ordered, -1 * qty_to_be_picked,
                tr_type, tr_id)

            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                shop, pickup_object.sku, type_normal, state_to_be_picked, qty_to_be_picked,
                tr_type, tr_id)

            info_logger.info("WarehouseConsolidation|generate_picklist| Pickup Generated| order id-{}, sku-{}"
                             .format(order.order_no, sku_id))

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
        cart = Cart.objects.create(last_modified_by=self.user, cart_status='active', cart_type='AUTO',
                                   approval_status=False,
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
                             .format(product_id, cart.id, qty))
        return cart


def start_auto_processing(request):
    process_auto_order()
    return HttpResponse("done")


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
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.ORDERED:
        entry_to_process = order_processor.generate_picklist(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.PICKUP_CREATED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.PICKUP_CREATED:
        entry_to_process = order_processor.assign_picker(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.PICKING_ASSIGNED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.PICKING_ASSIGNED:
        entry_to_process = order_processor.complete_pickup(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.PICKUP_COMPLETED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.PICKUP_COMPLETED:
        entry_to_process = order_processor.create_shipment(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.SHIPMENT_CREATED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.SHIPMENT_CREATED:
        entry_to_process = order_processor.shipment_qc(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.QC_DONE
    entry_to_process.save()
    return entry_to_process.state


def process_auto_po_gen(request):

    is_wh_consolidation_on = get_config('is_wh_consolidation_on', False)
    if not is_wh_consolidation_on:
        return
    wh_consolidation_destination = get_config('wh_consolidation_destination')
    if wh_consolidation_destination is None:
        info_logger.info("process_auto_po_generation|wh_consolidation_destination is not defined ")
        return
    buyer_shop = Shop.objects.filter(pk=wh_consolidation_destination).last()
    if buyer_shop is None:
        info_logger.info("process_auto_po_generation|no buyer found with id -{}".format(buyer_shop))
        return
    shipp_bill_address = Address.objects.filter(shop_name=buyer_shop).last()
    wh_consolidation_vendor = get_config('wh_consolidation_vendor')
    if wh_consolidation_vendor is None:
        info_logger.info("process_auto_po_generation|wh_consolidation_destination is not defined ")
        return
    supplier = Vendor.objects.filter(pk=wh_consolidation_vendor).last()
    if supplier is None:
        info_logger.info("process_auto_po_generation|no vendor found with id -{}".format(supplier))
        return
    user_id = get_config('user')
    if user_id is None:
        info_logger.info("process_auto_po_generation|user is not defined ")
        return
    user = User.objects.filter(pk=user_id).last()
    if user is None:
        info_logger.info("process_auto_po_generation|no User found with id -{}".format(user_id))
        return

    info_logger.info("process_auto_po_generation|STARTED")

    # fetching all delivered items
    delivered_items = AutoOrderProcessing.objects.filter(state=AutoOrderProcessing.ORDER_PROCESSING_STATUS.DELIVERED)

    # using grn_id getting ordered products
    for delivered_item in delivered_items:
        grn_item = GRNOrder.objects.filter(grn_id=delivered_item.grn).values(
         'order__ordered_cart','order__ordered_cart__brand','order__ordered_cart__po_validity_date',
         'order__ordered_cart__payment_term', 'order__ordered_cart__delivery_term',
         'order__ordered_cart__cart_product_mapping_csv',
        )

        # from grn_item filtering mapped products
        for grn in grn_item:
            cart_id = po_from_grn(grn, supplier, shipp_bill_address, user)
            AutoOrderProcessing.objects.filter(grn=delivered_item.grn.id).update(
                auto_po=cart_id.id, state=AutoOrderProcessing.ORDER_PROCESSING_STATUS.PO_CREATED)
            info_logger.info("updated AutoOrderProcessing for PO_CREATED.")
        info_logger.info("process_auto_po_generation|COMPLETED")
    info_logger.info("process_auto_po_generation no delivered_item item found")
    return HttpResponse("done")


def po_from_grn(grn, supplier, shipp_bill_address, user):
    brand = Brand.objects.get(id=grn['order__ordered_cart__brand'])
    with transaction.atomic():
        # creating cart
        cart_instance = POCarts.objects.create(brand=brand, supplier_name=supplier, supplier_state=supplier.state,
                                            gf_shipping_address=shipp_bill_address,
                                            gf_billing_address=shipp_bill_address,
                                            po_validity_date=grn['order__ordered_cart__po_validity_date'],
                                            payment_term=grn['order__ordered_cart__payment_term'],
                                            delivery_term=grn['order__ordered_cart__delivery_term'],
                                            po_status="OPEN", po_raised_by=user, cart_product_mapping_csv=
                                            grn['order__ordered_cart__cart_product_mapping_csv'])

        carts = POCartProductMappings.objects.filter(cart_id=grn['order__ordered_cart']).values(
            'cart_parent_product__parent_id','cart_product__id', '_tax_percentage', 'inner_case_size',
            'case_size', 'number_of_cases','scheme', 'no_of_pieces', 'vendor_product', 'price',
            'per_unit_price', 'vendor_product__brand_to_gram_price_unit',
            'vendor_product__case_size', 'vendor_product__product_mrp', 'vendor_product__product_price')
        for cart in carts:
            parent_product = ParentProduct.objects.get(parent_id=cart['cart_parent_product__parent_id'])
            product = Product.objects.get(id=cart['cart_product__id'])

            cart_mapped = POCartProductMappings.objects.filter(cart=cart_instance,
                                                            cart_parent_product=parent_product)

            if not cart_mapped:
                product_mapping = ProductVendorMapping.objects.create(vendor=supplier, product=product,
                                                                      product_price=cart[
                                                                          'vendor_product__product_price'],
                                                                      case_size=cart['vendor_product__case_size'],
                                                                      product_mrp=cart[
                                                                          'vendor_product__product_mrp'],
                                                                      status=True)

                POCartProductMappings.objects.create(cart=cart_instance, cart_parent_product=parent_product,
                                                  cart_product=product, _tax_percentage=cart['_tax_percentage'],
                                                  inner_case_size=cart['inner_case_size'], case_size=cart['case_size'],
                                                  number_of_cases=cart['number_of_cases'], scheme=cart['scheme'],
                                                  no_of_pieces=cart['no_of_pieces'], vendor_product=product_mapping,
                                                  price=float(cart['price']))
    return cart_instance


