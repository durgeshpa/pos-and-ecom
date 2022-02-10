import json
import logging

from django.db import transaction
from django.db.models import Q, TextField, Sum
from django.db.models.functions import Cast
from django.http import HttpResponse

# Create your views here.
from django.utils import timezone

from accounts.models import User
from global_config.views import get_config
from gram_to_brand.common_functions import get_grned_product_qty_by_grn_id
from retailer_backend.common_function import checkNotShopAndMapping, getShopMapping
from retailer_to_sp.models import Order, Cart, CartProductMapping, PickerDashboard, generate_picklist_id, \
    OrderedProductMapping, OrderedProduct, OrderedProductBatch, Trip
from retailer_to_sp.views import TRIP_ORDER_STATUS_MAP, TRIP_SHIPMENT_STATUS_MAP
from shops.models import Shop, ParentRetailerMapping
from whc.models import AutoOrderProcessing, SourceDestinationMapping
from wms.common_functions import get_stock, OrderManagement, InCommonFunctions, \
    CommonPickupFunctions, CommonPickBinInvFunction, InternalInventoryChange, CommonWarehouseInventoryFunctions, \
    CommonBinInventoryFunctions, get_expiry_date
from wms.models import InventoryType, OrderReserveRelease, PutawayBinInventory, InventoryState, BinInventory, \
    PickupBinInventory, Pickup, Putaway, Bin
from wms.views import shipment_out_inventory_change

from gram_to_brand.models import GRNOrder, Cart as POCarts, CartProductMapping as POCartProductMappings, \
    Order as Ordered, GRNOrderProductMapping, Document
from brand.models import Brand, Vendor
from addresses.models import Address
from products.models import Product, ParentProduct, ProductVendorMapping, ProductPrice, PriceSlab

info_logger = logging.getLogger('file-info')


class AutoOrderProcessor:
    type_normal = InventoryType.objects.filter(inventory_type="normal").last()

    def __init__(self, retailer_shop, user, supplier, shipp_bill_address, bin_list, vehicle_no):
        self.retailer_shop = retailer_shop
        self.user = user
        self.supplier = supplier
        self.shipp_bill_address = shipp_bill_address
        self.bin_list = bin_list
        self.vehicle_no = vehicle_no

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

        auto_processing_entry.cart = cart
        auto_processing_entry.retailer_shop = self.retailer_shop
        return auto_processing_entry

    @transaction.atomic
    def reserve_order(self, auto_processing_entry):
        product_quantity_dict = {cp.cart_product_id: float(cp.qty) for cp in
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
                         .format(order.order_no))
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
        if picker_dashboard_obj:
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

    @transaction.atomic
    def create_trip(self, auto_processing_entry):

        info_logger.info("WarehouseConsolidation|create_trip|Started, order id-{}"
                         .format(auto_processing_entry.order.id))
        trip = Trip(seller_shop=auto_processing_entry.order.seller_shop, delivery_boy=self.user,
                    vehicle_no=self.vehicle_no, trip_status=Trip.READY)
        trip.save()
        shipments = OrderedProduct.objects.filter(order=auto_processing_entry.order)
        if shipments:
            shipments.update(trip=trip)
        auto_processing_entry.order.order_status = Order.READY_TO_DISPATCH
        auto_processing_entry.order.save()
        info_logger.info("WarehouseConsolidation|create_trip|Trip Created, order id-{}"
                         .format(auto_processing_entry.order.id))
        return auto_processing_entry

    @transaction.atomic
    def start_trip(self, auto_processing_entry):
        info_logger.info("WarehouseConsolidation|start_trip|Started, order id-{}"
                         .format(auto_processing_entry.order.id))
        shipments = OrderedProduct.objects.filter(order=auto_processing_entry.order)
        for shipment in shipments:
            shipment.trip.trip_status = Trip.STARTED
            shipment.trip.save()
        info_logger.info("WarehouseConsolidation|start_trip|trip status updated, order id-{}"
                         .format(auto_processing_entry.order.id))
        shipment_out_inventory_change(shipments, TRIP_SHIPMENT_STATUS_MAP[Trip.STARTED])
        info_logger.info("WarehouseConsolidation|start_trip|inventory changes done, order id-{}"
                         .format(auto_processing_entry.order.id))
        auto_processing_entry.order.order_status = Order.DISPATCHED
        auto_processing_entry.order.save()
        info_logger.info("WarehouseConsolidation|start_trip|Completed, order id-{}"
                         .format(auto_processing_entry.order.id))
        return auto_processing_entry

    def complete_trip(self, auto_processing_entry):
        info_logger.info("WarehouseConsolidation|complete_trip|Started, order id-{}"
                         .format(auto_processing_entry.order.id))
        shipments = OrderedProduct.objects.filter(order=auto_processing_entry.order)
        for shipment in shipments:
            products_in_shipment = OrderedProductMapping.objects.filter(ordered_product=shipment)
            for p in products_in_shipment:
                p.delivered_qty = p.shipped_qty
                p.save()
            shipment.shipment_status = 'FULLY_DELIVERED_AND_VERIFIED'
            shipment.trip.completed_at = timezone.now()
            shipment.trip.trip_status = Trip.RETURN_VERIFIED
            shipment.trip.save()
            shipment.save()
        auto_processing_entry.order.order_status = TRIP_ORDER_STATUS_MAP[Trip.COMPLETED]
        auto_processing_entry.order.save()
        info_logger.info("WarehouseConsolidation|complete_trip|Completed, order id-{}"
                         .format(auto_processing_entry.order.id))
        return auto_processing_entry

    def __shipment_qc(self, order):
        shipments = OrderedProduct.objects.filter(order=order)
        if shipments.exists():
            shipment = shipments.last()
            shipment.shipment_status = OrderedProduct.READY_TO_SHIP
            shipment.save()
            shipment.shipment_status = OrderedProduct.MOVED_TO_DISPATCH
            shipment.save()
            shipment.rt_order_product_order_product_mapping.all().update(is_qc_done=True)
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
        pickup_objects = Pickup.objects.filter(pickup_type_id=order_no, status='picking_assigned')
        for p in pickup_objects:
            pickup_bin_inventory_objects = PickupBinInventory.objects.filter(pickup=p)
            picked_qty = 0
            for pbi in pickup_bin_inventory_objects:
                tr_id = pbi.pickup_id
                warehouse = pbi.bin.warehouse
                sku = pbi.bin.sku
                inventory_type = pbi.bin.inventory_type
                picked_qty += pbi.quantity
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
            p.pickup_quantity = picked_qty
            p.status = 'picking_complete'
            p.save()
            info_logger.info("WarehouseConsolidation|complete_pickup| Picking done |order id-{}, sku-{}"
                             .format(order_no, sku))

    @transaction.atomic
    def generate_picklist(self, auto_processing_entry):
        in_ids = InCommonFunctions.get_filtered_in(in_type='GRN', in_type_id=auto_processing_entry.grn.grn_id) \
            .annotate(idc=Cast('pk', TextField())) \
            .values_list('idc', flat=True)
        putaway_bin_inventories = PutawayBinInventory.objects.filter(putaway__putaway_type='GRN',
                                                                     putaway__putaway_type_id__in=in_ids)
        putaway_batch_bin_dict = {}
        for pbi in putaway_bin_inventories:
            if putaway_batch_bin_dict.get(pbi.sku_id) is None:
                putaway_batch_bin_dict[pbi.sku_id] = []
            putaway_batch_bin_dict[pbi.sku_id].append(
                {'batch_id': pbi.batch_id, 'bin_id': pbi.bin_id, 'qty': pbi.putaway_quantity})
        self.__generate_picklist(auto_processing_entry.cart, auto_processing_entry.order, putaway_batch_bin_dict)
        info_logger.info("WarehouseConsolidation|generate_picklist| Picklist Generated, order id-{}"
                         .format(auto_processing_entry.order.order_no))
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
            for item in sku_bin_dict[sku_id]:
                batch_id = item['batch_id']
                bin_id = item['bin_id']
                qty_to_be_picked = item['qty']
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
                shop, pickup_object.sku, type_normal, state_ordered, -1 * pickup_object.quantity,
                tr_type, tr_id)

            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(
                shop, pickup_object.sku, type_normal, state_to_be_picked, pickup_object.quantity,
                tr_type, tr_id)

            info_logger.info("WarehouseConsolidation|generate_picklist| Pickup Generated| order id-{}, sku-{}"
                             .format(order.order_no, sku_id))

    def __place_order(self, cart):
        order_reserve_obj = OrderReserveRelease.objects.filter(warehouse=cart.seller_shop,
                                                               transaction_id=cart.cart_no,
                                                               warehouse_internal_inventory_release=None,
                                                               ).last()
        if order_reserve_obj is None:
            info_logger.info(
                "WarehouseConsolidation|place_order_by_grn|place_order|Order Reserve Entry not found, order id-{}"
                    .format(cart.cart_no))
            return False
        order = Order.objects.create(last_modified_by=self.user, ordered_by=self.user, ordered_cart=cart)

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
            "WarehouseConsolidation|place_order_by_grn|place_order|Order Created, order id-{}".format(order.order_no))

        sku_id = [i.cart_product.id for i in cart.rt_cart_list.all()]
        reserved_args = json.dumps({
            'shop_id': cart.seller_shop_id,
            'transaction_id': cart.cart_no,
            'transaction_type': 'ordered',
            'order_status': order.order_status,
            'order_number': order.order_no
        })
        order_result = OrderManagement.release_blocking_from_order(reserved_args, sku_id)
        if order_result is False:
            order.delete()
            info_logger.info("WarehouseConsolidation|place_order_by_grn|place_order|"
                             "Blocking could not be released, order deleted, cart no-{}".format(cart.cart_no))
            return False
        info_logger.info(
            "WarehouseConsolidation|place_order_by_grn|place_order|Blocking released, cart id-{}".format(cart.id))
        return order

    def __reserve_cart(self, cart, product_quantity_dict):
        """Creates entry in order reserve release for each product in the cart"""
        if len(product_quantity_dict) > 0:
            reserved_args = json.dumps({
                'shop_id': cart.seller_shop_id,
                'transaction_id': cart.cart_no,
                'products': product_quantity_dict,
                'transaction_type': 'reserved'
            })
            OrderManagement.create_reserved_order(reserved_args)
            return
        info_logger.info(
            "WarehouseConsolidation|reserve_cart|No product in cart, cart id-{}".format(cart.id))
        raise Exception("Reserve cart failed, No product in the cart")

    def __add_products_to_cart(self, seller_shop, buyer_shop, product_quantity_dict, available_stock):
        "Creates cart and adds the product in created cart"
        cart = Cart.objects.create(last_modified_by=self.user, cart_status='active', cart_type='AUTO',
                                   approval_status=False,
                                   seller_shop=seller_shop, buyer_shop=buyer_shop)
        info_logger.info("WarehouseConsolidation|add_products_to_cart|Cart Created, cart id-{}, cart no-{}"
                         .format(cart.id, cart.cart_no))
        for product_id, qty in product_quantity_dict.items():
            available_qty = available_stock.get(product_id, 0)
            info_logger.info("WarehouseConsolidation|add_products_to_cart|product id-{}, grned qty-{}, available qty-{}"
                             .format(product_id, qty, available_qty))
            if available_qty <= 0:
                continue
            if qty > available_qty:
                qty = available_qty

            product = Product.objects.filter(pk=product_id).last()
            product_price = self.__get_product_price(product, seller_shop, buyer_shop)
            CartProductMapping.objects.create(cart=cart, cart_product_id=product_id, qty=qty, no_of_pieces=qty,
                                              cart_product_price=product_price)
            info_logger.info("WarehouseConsolidation|add_products_to_cart|product id-{}, cart id-{}, qty added-{}"
                             .format(product_id, cart.id, qty))
        return cart

    def __get_product_price(self, product, seller_shop, buyer_shop):
        """
        Returns the current approved product price for this product and shop combination,
        Creates the price using product_mrp if price doesn't alredy exists
        """
        price = product.get_current_shop_price(seller_shop.id, buyer_shop.id)
        if price is None:
            price = self.__create_price_using_mrp(product, seller_shop)
        return price

    def __create_price_using_mrp(self, product, seller_shop):
        """
        Creates the price for specific product and seller shop combination using product MRP
        """
        price = ProductPrice.objects.create(product=product, seller_shop=seller_shop, mrp=product.product_mrp,
                                            approval_status=ProductPrice.APPROVED, status=True)
        PriceSlab.objects.create(product_price=price, start_value=0, end_value=0, selling_price=product.product_mrp)
        return price

    @transaction.atomic
    def process_putaway(self, auto_processing_entry):
        in_ids = InCommonFunctions.get_filtered_in(in_type='GRN', in_type_id=auto_processing_entry.grn.grn_id) \
            .annotate(idc=Cast('pk', TextField())) \
            .values_list('idc', flat=True)
        putaway_entries = Putaway.objects.filter(putaway_type='GRN', putaway_type_id__in=in_ids)

        info_logger.info("WarehouseConsolidation|process_putaway| Started| grn id-{}"
                         .format(auto_processing_entry.grn_id))

        self.__process_putaway(auto_processing_entry, putaway_entries)

        info_logger.info("WarehouseConsolidation|process_putaway| Completed | grn id-{}"
                         .format(auto_processing_entry.grn_id))
        return auto_processing_entry

    def __process_putaway(self, auto_processing_entry, putaway_entries):

        transaction_type = 'put_away_type'
        initial_type = InventoryType.objects.filter(inventory_type='new').last()
        final_type = InventoryType.objects.filter(inventory_type='normal').last()
        state_total_available = InventoryState.objects.filter(inventory_state='total_available').last()

        for entry in putaway_entries:

            warehouse = entry.warehouse
            putaway_qty = entry.quantity
            sku = entry.sku
            batch_id = entry.batch_id
            transaction_id = entry.id

            bin_selected = self.select_bin(batch_id, sku)
            if bin_selected is None:
                info_logger.info('WarehouseConsolidation|process_putaway|'
                                 'Putaway could not be processed, sku-{}, batchid-{}'
                                 .format(sku, batch_id))
                raise Exception('WarehouseConsolidation|process_putaway|'
                                'Putaway could not be processed, sku-{}, batchid-{}'
                                .format(sku, batch_id))

            info_logger.info("WarehouseConsolidation|process_putaway| putaway started | "
                             "grn id-{}, batch-{}, bin-{}"
                             .format(auto_processing_entry.grn_id, batch_id, bin_selected.bin_id))

            bin_inventory_obj = self.update_bin_inventory(batch_id, bin_selected, putaway_qty, sku, warehouse)

            InternalInventoryChange.create_bin_internal_inventory_change(warehouse, sku, batch_id,
                                                                         bin_selected.bin_id,
                                                                         initial_type,
                                                                         final_type, transaction_type,
                                                                         transaction_id, putaway_qty)

            CommonWarehouseInventoryFunctions.create_warehouse_inventory_with_transaction_log(warehouse, sku,
                                                                                              self.type_normal,
                                                                                              state_total_available,
                                                                                              putaway_qty,
                                                                                              transaction_type,
                                                                                              transaction_id)

            PutawayBinInventory.objects.create(warehouse=warehouse, putaway=entry,
                                               bin=bin_inventory_obj,
                                               putaway_quantity=putaway_qty, putaway_status=True,
                                               sku=sku, batch_id=batch_id,
                                               putaway_type=entry.putaway_type)

            entry.putaway_quantity = putaway_qty
            entry.putaway_user = self.user
            entry.put_away_status = True
            entry.save()
            info_logger.info("WarehouseConsolidation|process_putaway| putaway done | "
                             "grn id-{}, batch-{}, bin-{}"
                             .format(auto_processing_entry.grn_id, batch_id, bin_selected.bin_id))

    def update_bin_inventory(self, batch_id, bin_selected, putaway_qty, sku, warehouse):
        bin_inventory_obj = CommonBinInventoryFunctions.get_filtered_bin_inventory(warehouse=warehouse,
                                                                                   bin=bin_selected,
                                                                                   sku=sku,
                                                                                   batch_id=batch_id,
                                                                                   inventory_type=self.type_normal)
        if bin_inventory_obj.exists():
            bin_inventory_obj = bin_inventory_obj.last()
            bin_inventory_obj.quantity = bin_inventory_obj.quantity + putaway_qty
            bin_inventory_obj.save()
        else:
            bin_inventory_obj = BinInventory.objects.create(warehouse=warehouse, bin=bin_selected,
                                                            sku=sku, batch_id=batch_id,
                                                            inventory_type=self.type_normal,
                                                            quantity=putaway_qty, in_stock=True)
        return bin_inventory_obj

    def select_bin(self, batch_id, sku):
        bin_selected = None
        for bin in self.bin_list:
            bin_inventory = CommonBinInventoryFunctions.get_filtered_bin_inventory(sku=sku, bin=bin) \
                .exclude(batch_id=batch_id)
            if bin_inventory.exists():
                qs = bin_inventory.filter(inventory_type=self.type_normal) \
                    .aggregate(available=Sum('quantity'), to_be_picked=Sum('to_be_picked_qty'))
                total = qs['available'] + qs['to_be_picked']
                if total > 0:
                    info_logger.info('WarehouseConsolidation|process_putaway|'
                                     'This product with sku {} and batch_id {} can not be placed in the bin'
                                     .format(sku, batch_id))
                    continue
            bin_selected = bin
            break
        return bin_selected

    @transaction.atomic
    def process_auto_po_gen(self, auto_processing_entry):

        grn_order = GRNOrder.objects.filter(id=auto_processing_entry.grn_id).values(
            'order__order_no',
            'order__ordered_cart', 'order__ordered_cart__brand', 'order__ordered_cart__po_validity_date',
            'order__ordered_cart__payment_term', 'order__ordered_cart__delivery_term',
            'order__ordered_cart__po_status',
            'order__ordered_cart__cart_product_mapping_csv',
        )
        if not grn_order.exists():
            raise Exception("WarehouseConsolidation|process_auto_po_gen| No GRN found with ID {}"
                            .format(auto_processing_entry.grn_id))

        po = self.po_from_grn(grn_order.last())
        if not po:
            raise Exception("WarehouseConsolidation|process_auto_po_gen| PO generation failed, GRN ID {}"
                            .format(auto_processing_entry.grn_id))
        auto_processing_entry.auto_po = po
        info_logger.info("WarehouseConsolidation|process_auto_po_gen| PO Generaion Completed, GRN ID {}"
                         .format(auto_processing_entry.grn_id))
        return auto_processing_entry

    def po_from_grn(self, grn):
        source_po = POCarts.objects.filter(id=grn['order__ordered_cart']).last()
        get_po_qs = AutoOrderProcessing.objects.filter(source_po=source_po,
                                                       state__in=[
                                                           AutoOrderProcessing.ORDER_PROCESSING_STATUS.PO_CREATED,
                                                           AutoOrderProcessing.ORDER_PROCESSING_STATUS.AUTO_GRN_DONE])
        if get_po_qs.exists():
            cart_instance = get_po_qs.last().auto_po
        else:
            brand = Brand.objects.get(id=grn['order__ordered_cart__brand'])
            cart_instance = POCarts.objects.create(brand=brand, supplier_name=self.supplier,
                                                   supplier_state=self.supplier.state,
                                                   gf_shipping_address=self.shipp_bill_address,
                                                   gf_billing_address=self.shipp_bill_address,
                                                   po_validity_date=grn['order__ordered_cart__po_validity_date'],
                                                   payment_term=grn['order__ordered_cart__payment_term'],
                                                   delivery_term=grn['order__ordered_cart__delivery_term'],
                                                   po_raised_by=self.user, last_modified_by=self.user,
                                                   cart_product_mapping_csv=
                                                   grn['order__ordered_cart__cart_product_mapping_csv'],
                                                   po_status='OPEN')

        cart_product_mapping = POCartProductMappings.objects.filter(cart_id=grn['order__ordered_cart']).values(
            'cart_parent_product__parent_id', 'cart_product__id', '_tax_percentage', 'inner_case_size',
            'case_size', 'number_of_cases', 'scheme', 'no_of_pieces', 'vendor_product', 'price',
            'per_unit_price', 'vendor_product__brand_to_gram_price_unit',
            'vendor_product__case_size', 'vendor_product__product_mrp', 'vendor_product__product_price',
            'vendor_product__product_price_pack')
        all_source_po_product_ids = []
        for cart_pro_map in cart_product_mapping:
            parent_product = ParentProduct.objects.get(parent_id=cart_pro_map['cart_parent_product__parent_id'])
            product = Product.objects.get(id=cart_pro_map['cart_product__id'])
            all_source_po_product_ids.append(cart_pro_map['cart_product__id'])
            cart_mapped = POCartProductMappings.objects.filter(cart=cart_instance, cart_product=product)

            if cart_mapped:
                cart_mapped.update(number_of_cases=cart_pro_map['number_of_cases'],
                                   no_of_pieces=cart_pro_map['no_of_pieces'],
                                   price=float(cart_pro_map['price']))
            if not cart_mapped:
                product_mapping, _ = ProductVendorMapping.objects.get_or_create(vendor=self.supplier, product=product,
                                                                                product_price=cart_pro_map[
                                                                                    'vendor_product__product_price'],
                                                                                product_price_pack=cart_pro_map[
                                                                                    'vendor_product__product_price_pack'],
                                                                                case_size=cart_pro_map[
                                                                                    'vendor_product__case_size'],
                                                                                product_mrp=cart_pro_map[
                                                                                    'vendor_product__product_mrp'],
                                                                                status=True)
                # Creates CartProductMapping
                POCartProductMappings.objects.create(cart=cart_instance, cart_parent_product=parent_product,
                                                     cart_product=product,
                                                     _tax_percentage=cart_pro_map['_tax_percentage'],
                                                     inner_case_size=cart_pro_map['inner_case_size'],
                                                     case_size=cart_pro_map['case_size'],
                                                     number_of_cases=cart_pro_map['number_of_cases'],
                                                     scheme=cart_pro_map['scheme'],
                                                     no_of_pieces=cart_pro_map['no_of_pieces'],
                                                     vendor_product=product_mapping,
                                                     price=float(cart_pro_map['price']))

        all_po_products = POCartProductMappings.objects.filter(cart=cart_instance).values('id', 'cart_product_id')
        for p in all_po_products:
            if p['cart_product_id'] not in all_source_po_product_ids:
                POCartProductMappings.objects.filter(pk=p['id']).delete()

        return cart_instance

    @transaction.atomic
    def create_auto_grn(self, auto_processing_entry):
        info_logger.info("create_auto_grn|STARTED")

        source_grn_order = GRNOrder.objects.filter(id=auto_processing_entry.grn_id).last()
        grn_products = GRNOrderProductMapping.objects.filter(grn_order=auto_processing_entry.grn_id)
        grn_doc = Document.objects.filter(grn_order=auto_processing_entry.grn_id).values('document_number',
                                                                                         'document_image')
        order = Ordered.objects.get(ordered_cart=auto_processing_entry.auto_po_id)
        invoice_no = auto_processing_entry.order.rt_order_order_product.last().invoice_no
        grn_order = GRNOrder(order=order, invoice_no=invoice_no, invoice_date=source_grn_order.invoice_date,
                             invoice_amount=source_grn_order.invoice_amount, tcs_amount=source_grn_order.tcs_amount)
        grn_order.save()

        for doc in grn_doc:
            grn_doc = Document(grn_order=grn_order, document_number=doc['document_number'],
                               document_image=doc['document_image'])
            grn_doc.save()

        for grn_product in grn_products:
            vendor_product = ProductVendorMapping.objects.filter(vendor=self.supplier, product=grn_product.product,
                                                                 status=True).last()
            grn_obj = GRNOrderProductMapping(grn_order=grn_order, product=grn_product.product,
                                             product_invoice_price=grn_product.product_invoice_price,
                                             product_invoice_qty=grn_product.product_invoice_qty,
                                             manufacture_date=grn_product.manufacture_date,
                                             expiry_date=grn_product.expiry_date,
                                             delivered_qty=grn_product.delivered_qty,
                                             available_qty=grn_product.available_qty,
                                             returned_qty=grn_product.returned_qty,
                                             damaged_qty=grn_product.damaged_qty,
                                             vendor_product=vendor_product,
                                             batch_id=grn_product.batch_id,
                                             barcode_id=grn_product.barcode_id)
            grn_obj.save()
        auto_processing_entry.auto_grn = grn_order
        auto_processing_entry.auto_po.po_status = auto_processing_entry.source_po.po_status
        auto_processing_entry.auto_po.save()
        info_logger.info("create_auto_grn|COMPLETED")
        return auto_processing_entry


def start_auto_processing(request):
    process_auto_order()
    return HttpResponse("done")


def process_auto_order():
    is_wh_consolidation_on = get_config('is_wh_consolidation_on', False)
    if not is_wh_consolidation_on:
        return
    source_wh_id_list = get_config('wh_consolidation_source') ## Addistro SP Shop
    # if source_wh_id is None:
    #     info_logger.info("process_auto_order|wh_consolidation_source is not defined")
    #     return
    # source_wh = Shop.objects.filter(pk=source_wh_id).last()
    # if source_wh is None:
    #     info_logger.info("process_auto_order|no warehouse found with id -{}".format(source_wh_id))
    #     return

    # wh_consolidation_destination = get_config('wh_consolidation_destination')
    # if wh_consolidation_destination is None:
    #     info_logger.info("process_auto_po_generation|wh_consolidation_destination is not defined ")
    #     return
    # buyer_shop = Shop.objects.filter(pk=wh_consolidation_destination).last()
    #
    # if buyer_shop is None:
    #     info_logger.info("process_auto_order|no shop found with id -{}".format(buyer_shop))
    #     return
    # shipp_bill_address = Address.objects.filter(shop_name=buyer_shop).last()

    wh_consolidation_vendor = get_config('wh_consolidation_vendor')
    if wh_consolidation_vendor is None:
        info_logger.info("process_auto_order|wh_consolidation_vendor is not defined ")
        return

    supplier = Vendor.objects.filter(pk=wh_consolidation_vendor).last()
    if supplier is None:
        info_logger.info("process_auto_order|no vendor found with id -{}".format(supplier))
        return

    user_id = get_config('wh_consolidation_user')
    if user_id is None:
        info_logger.info("process_auto_order|user is not defined ")
        return

    system_user = User.objects.filter(pk=user_id).last()
    if system_user is None:
        info_logger.info("process_auto_order|no User found with id -{}".format(user_id))
        return

    # wh_mapping = SourceDestinationMapping.objects.filter(source_wh=source_wh)
    # if not wh_mapping.exists():
    #     info_logger.info("process_auto_order|no mapping found for this warehouse-{}".format(source_wh))
    #     return
    entries_to_process = AutoOrderProcessing.objects.filter(
        ~Q(state=AutoOrderProcessing.ORDER_PROCESSING_STATUS.AUTO_GRN_DONE))
    if entries_to_process.count() == 0:
        info_logger.info("process_auto_order| no entry to process")
        return

    # virtual_bin_ids = get_config('virtual_bins')
    # if not virtual_bin_ids:
    #     return
    # bin_ids = eval(virtual_bin_ids)
    # bin_list = Bin.objects.filter(warehouse=source_wh, bin_id__in=bin_ids)
    # if not bin_list.exists():
    #     info_logger.info("process_auto_order| no bin found")
    #     return
    vehicle_no = get_config('wh_consolidation_vehicle_no', 'dummy')
    # retailer_shop = wh_mapping.last().retailer_shop
    info_logger.info("process_auto_order|STARTED")
    for entry in entries_to_process:

        wh_mapping = SourceDestinationMapping.objects.filter(source_wh=entry.grn_warehouse).last()

        if not wh_mapping:
            info_logger.info("process_auto_order|no mapping found for this warehouse-{}".format(entry.grn_warehouse))
            continue

        elif not ParentRetailerMapping.objects.filter(retailer=wh_mapping.dest_wh).exists():
            info_logger.info("process_auto_order|no mapping found for this retailer-{}".format(wh_mapping.dest_wh))
            continue

        gfdn_sp_shop = ParentRetailerMapping.objects.filter(retailer=wh_mapping.dest_wh).last().parent
        shipp_bill_address = Address.objects.filter(shop_name=gfdn_sp_shop).last()

        if not Bin.objects.filter(warehouse=entry.grn_warehouse_id, bin_type='VB', is_active=True).exists():
            info_logger.info("process_auto_order| no bin found for warehouse {}".format(entry.grn_warehouse))
            return

        bin_list = Bin.objects.filter(warehouse=entry.grn_warehouse_id, bin_type='VB', is_active=True)
        order_processor = AutoOrderProcessor(wh_mapping.retailer_shop, system_user, supplier, shipp_bill_address,
                                             bin_list, vehicle_no)
        try:
            while True:
                current_state = entry.state
                info_logger.info("process_auto_order|GRN ID-{}, current state-{}".format(entry.grn_id, current_state))
                next_state = process_next(order_processor, entry)
                if current_state == next_state:
                    info_logger.info("process_auto_order|GRN ID-{}, could not move ahead".format(entry.grn_id))
                    break
                info_logger.info("process_auto_order|GRN ID-{}, current state-{}".format(entry.grn_id, next_state))
        except Exception as e:
            info_logger.error("process_auto_order|error while processing GRN ID-{}, current state-{}"
                              .format(entry.grn_id, entry.state))
            info_logger.exception(e)
    info_logger.info("process_auto_order|COMPLETED")


def process_next(order_processor, entry_to_process):
    if entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.GRN:
        entry_to_process = order_processor.process_putaway(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.PUTAWAY
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.PUTAWAY:
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
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.QC_DONE:
        entry_to_process = order_processor.create_trip(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.TRIP_CREATED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.TRIP_CREATED:
        entry_to_process = order_processor.start_trip(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.TRIP_STARTED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.TRIP_STARTED:
        entry_to_process = order_processor.complete_trip(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.DELIVERED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.DELIVERED:
        entry_to_process = order_processor.process_auto_po_gen(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.PO_CREATED
    elif entry_to_process.state == AutoOrderProcessing.ORDER_PROCESSING_STATUS.PO_CREATED:
        entry_to_process = order_processor.create_auto_grn(entry_to_process)
        entry_to_process.state = AutoOrderProcessing.ORDER_PROCESSING_STATUS.AUTO_GRN_DONE
    entry_to_process.save()
    return entry_to_process.state
