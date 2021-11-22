import logging
import datetime
import json
from celery.task import task
from celery import Task
from sp_to_gram.models import OrderedProductReserved, OrderedProductMapping
from gram_to_brand.models import (
    OrderedProductReserved as GramOrderedProductReserved)
from retailer_to_sp.models import (Cart, Order, OrderedProduct, generate_picklist_id, PickerDashboard)
from django.db.models import Sum, Q, F
from celery.contrib import rdb

logging.getLogger('retail_to_sp_task')

@task
def create_reserved_order(reserved_args):
    params = json.loads(reserved_args)
    cart_id = params['cart_id']
    shop_id = params['shop_id']
    products = params['products']
    cart = Cart.objects.get(pk=cart_id)
    if OrderedProductReserved.objects.filter(cart=cart, reserve_status='reserved').exists():
        return "Cart items already reserved"
    grns = OrderedProductMapping.objects.filter(
        Q(shop__id=shop_id),
        Q(product__id__in=products.keys()),
        Q(available_qty__gt=0),
        Q(expiry_date__gt=datetime.datetime.today())
        ).order_by('product_id','available_qty')

    for grn in grns:
        remaining_qty = products[str(grn.product.id)]
        if remaining_qty >0:
            deduct_qty = min(grn.available_qty, remaining_qty)
            grn.available_qty -= deduct_qty
            products[str(grn.product.id)] = remaining_qty - deduct_qty
            grn.save()
            order_product_reserved = OrderedProductReserved(
                product=grn.product,
                reserved_qty=deduct_qty
            )
            order_product_reserved.order_product_reserved = grn
            order_product_reserved.cart = cart
            order_product_reserved.reserve_status = 'reserved'
            order_product_reserved.save()

@task
def update_reserved_order(shipment_products, cart_id):
    shipment_products_mapping = {i['product__id']:i['shipped_items'] for i in shipment_products}
    reserved_products = OrderedProductReserved.objects.filter(
        cart_id=cart_id,
        reserve_status=OrderedProductReserved.ORDERED,
        product__id__in=shipment_products_mapping.keys()
    )

    for rp in reserved_products:
        reserved_qty = int(rp.reserved_qty)
        shipped_qty = int(shipment_products_mapping[rp.product.id])
        if not shipped_qty or (reserved_qty == rp.shipped_qty):
            continue
        if reserved_qty > shipped_qty:
            reserved_shipped_qty = shipped_qty
        else:
            reserved_shipped_qty = reserved_qty

        rp.shipped_qty += reserved_shipped_qty
        shipment_products_mapping[rp.product.id] -= reserved_shipped_qty
        rp.save()



@task
def ordered_product_available_qty_update(
        ordered_product_ids, ordered_amount, cart_id):
    queryset = OrderedProductMapping.objects.filter(
        id__in=ordered_product_ids
    )
    remaining_amount = ordered_amount
    for product_detail in queryset:
        if product_detail.available_qty <= 0:
            continue

        if remaining_amount <= 0:
            break

        # Todo available_qty replace to sp_available_qty
        if (product_detail.available_qty >=
                remaining_amount):
            deduct_qty = remaining_amount
        else:
            deduct_qty = product_detail.available_qty

        product_detail.available_qty -= deduct_qty
        remaining_amount -= deduct_qty
        product_detail.save()
        order_product_reserved = OrderedProductReserved(
            product=product_detail.product,
            reserved_qty=deduct_qty
        )
        order_product_reserved.order_product_reserved = product_detail
        order_product_reserved.cart_id = cart_id
        order_product_reserved.reserve_status = 'reserved'
        order_product_reserved.save()


@task
def release_blocking(parent_shop_type, cart_id):
    if parent_shop_type == 'sp':
        ordered_product_reserved = OrderedProductReserved.objects.filter(
            cart__id=cart_id, reserve_status='reserved')
        if ordered_product_reserved.exists():
            for ordered_reserve in ordered_product_reserved:
                ordered_reserve.order_product_reserved.available_qty = (
                    int(ordered_reserve.order_product_reserved.available_qty) +
                    int(ordered_reserve.reserved_qty))
                ordered_reserve.order_product_reserved.save()
                ordered_reserve.delete()
    elif parent_shop_type == 'gf':
        gram_ordered_product_reserved = GramOrderedProductReserved.objects.\
            filter(cart__id=cart_id, reserve_status='reserved')
        if gram_ordered_product_reserved.exists():
            for ordered_reserve in gram_ordered_product_reserved:
                ordered_reserve.order_product_reserved.available_qty = (
                    int(ordered_reserve.order_product_reserved.available_qty) +
                    int(ordered_reserve.reserved_qty))
                ordered_reserve.order_product_reserved.save()
                ordered_reserve.delete()
    return True


class UpdateOrderStatusPickerReserveQty(object):

    def __init__(self, shipment_id, close_order_checked, shipment_products_dict,
                 total_shipped_qty, total_ordered_qty):
        super().__init__()
        self.shipment = OrderedProduct.objects.get(id=shipment_id)
        self.order = Order.objects.get(rt_order_order_product=shipment_id)
        self.close_order_checked = close_order_checked
        self.shipment_products_dict = shipment_products_dict
        self.total_shipped_qty = total_shipped_qty
        self.total_ordered_qty = total_ordered_qty
        self.cart_id = self.order.ordered_cart.id

        self.update_reserved_order()

        if (self.close_order_checked and
                (self.shipment.shipment_status != self.shipment.CLOSED and
                 not self.order.order_closed)):
            self.update_sp_qty()
            self.order.picker_order.update(picking_status="moved_to_qc")

        self.update_order_status()

    def update_order_status(self):
        if self.total_ordered_qty == self.total_shipped_qty:
            self.order.order_status = Order.FULL_SHIPMENT_CREATED
        else:
            self.order.order_status = Order.PARTIAL_SHIPMENT_CREATED

        if self.close_order_checked and not self.order.order_closed:
            self.order.order_closed = True

        self.order.save()

    def update_reserved_order(self):
        shipment_products_mapping = {i['product__id']:i['shipped_items'] for i in self.shipment_products_dict}
        logging.info(shipment_products_mapping, "update_reserved_order-Shipment Product Mapping")
        reserved_products = OrderedProductReserved.objects.filter(
            cart_id=self.cart_id,
            reserve_status=OrderedProductReserved.ORDERED,
            product__id__in=shipment_products_mapping.keys()
        )
        logging.info(reserved_products, "update_reserved_order-Reserved Product")
        for rp in reserved_products:
            reserved_qty = int(rp.reserved_qty)
            logging.info(reserved_qty, "update_reserved_order-Reserved Quantity")
            shipped_qty = int(shipment_products_mapping[rp.product.id])
            logging.info(shipped_qty, "update_reserved_order-Shipped Quantity")
            if not shipped_qty or (reserved_qty == rp.shipped_qty):
                continue
            if reserved_qty > shipped_qty:
                reserved_shipped_qty = shipped_qty
                logging.info(reserved_shipped_qty, "update_reserved_order-if block-Shipped Quantity")
            else:
                reserved_shipped_qty = reserved_qty
                logging.info(reserved_shipped_qty, "update_reserved_order-else block-Shipped Quantity")

            rp.shipped_qty += reserved_shipped_qty
            logging.info(rp.shipped_qty, "update_reserved_order-finally-RP Shipped Quantity")
            shipment_products_mapping[rp.product.id] -= reserved_shipped_qty
            rp.save()

    def update_sp_qty(self):
        shipment_products = [i['product__id'] for i in self.shipment_products_dict]
        reserved_products = OrderedProductReserved.objects.filter(
            cart_id=self.cart_id,
            reserve_status=OrderedProductReserved.ORDERED,
            reserved_qty__gt=0).order_by('reserved_qty')

        reserved_products_with_shipment = reserved_products.filter(product__id__in=shipment_products)
        for ordered_product_reserved in reserved_products_with_shipment:
            grn = ordered_product_reserved.order_product_reserved
            grn.available_qty += (ordered_product_reserved.reserved_qty -
                                  ordered_product_reserved.shipped_qty)
            grn.save()
            ordered_product_reserved.save()

        reserved_products_without_shipment = reserved_products.exclude(product__id__in=shipment_products)
        for ordered_product_reserved in reserved_products_without_shipment:
            grn = ordered_product_reserved.order_product_reserved
            grn.available_qty += (ordered_product_reserved.reserved_qty - 0)
            grn.save()
            ordered_product_reserved.save()


@task
def update_order_status_picker_reserve_qty(
        shipment_id, close_order_checked, shipment_products_dict,
        total_shipped_qty, total_ordered_qty):
    UpdateOrderStatusPickerReserveQty(
        shipment_id, close_order_checked, shipment_products_dict,
        total_shipped_qty, total_ordered_qty)
