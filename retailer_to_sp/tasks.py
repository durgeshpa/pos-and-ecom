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


class UpdateOrderStatusAndCreatePicker(object):

    def __init__(self, shipment_id, close_order_checked, changed_data):
        super().__init__()
        shipment = OrderedProduct.objects.get(id=shipment_id)
        order =  Order.objects.get(rt_order_order_product=shipment_id)

        self.update_order_status(order, shipment, close_order_checked, changed_data)

        if (close_order_checked and
                (shipment.shipment_status != shipment.CLOSED and
                 not order.order_closed)):
            self.update_sp_qty(order, shipment)
            order.picker_order.update(picking_status="picking_complete")

    def update_order_status(self, order, shipment, close_order_checked, changed_data):
        shipment_products_dict = order.rt_order_order_product.aggregate(
                delivered_qty = Sum('rt_order_product_order_product_mapping__delivered_qty'),
                shipped_qty = Sum('rt_order_product_order_product_mapping__shipped_qty'),
                returned_qty = Sum('rt_order_product_order_product_mapping__returned_qty'),
                damaged_qty = Sum('rt_order_product_order_product_mapping__damaged_qty'),)
        cart_products_dict = order.ordered_cart.rt_cart_list.aggregate(total_no_of_pieces = Sum('no_of_pieces'))

        total_delivered_qty = shipment_products_dict.get('delivered_qty')

        total_shipped_qty = shipment_products_dict.get('shipped_qty')

        total_returned_qty = shipment_products_dict.get('returned_qty')

        total_damaged_qty = shipment_products_dict.get('damaged_qty')

        ordered_qty = cart_products_dict.get('total_no_of_pieces')

        order = shipment.order

        if ordered_qty == (total_delivered_qty + total_returned_qty + total_damaged_qty):
            order.order_status = 'SHIPPED'

        elif (total_returned_qty == total_shipped_qty or
              (total_damaged_qty + total_returned_qty) == total_shipped_qty):
            if order.order_closed:
                order.order_status = Order.DENIED_AND_CLOSED
            else:
                order.order_status = 'DENIED'

        elif (total_delivered_qty == 0 and total_shipped_qty > 0 and
              total_returned_qty == 0 and total_damaged_qty == 0):
            order.order_status = 'DISPATCH_PENDING'

        elif (ordered_qty - total_delivered_qty) > 0 and total_delivered_qty > 0:
            if order.order_closed:
                order.order_status = Order.PARTIALLY_SHIPPED_AND_CLOSED
            else:
                order.order_status = 'PARTIALLY_SHIPPED'

        if close_order_checked and not order.order_closed:
            order.order_closed = True

        order.save()

        self.create_picker(order, shipment, ordered_qty, shipment_products_dict.get('shipped_qty',0), changed_data, close_order_checked)

    def create_picker(self, order, shipment, ordered_qty, shipped_qty, changed_data, close_order_checked):
        change_value = shipment.shipment_status == shipment.READY_TO_SHIP
        if 'shipment_status' in changed_data and change_value and (not close_order_checked):

            if int(ordered_qty) > shipped_qty:
                try:
                    pincode = "00" #form.instance.order.shipping_address.pincode
                except:
                    pincode = "00"
                PickerDashboard.objects.create(
                    order=order,
                    picking_status="picking_pending",
                    picklist_id= generate_picklist_id(pincode) #get_random_string(12).lower(),#
                    )

    def update_sp_qty(self, order, shipment):
        cart = order.ordered_cart
        shipment_products = shipment.rt_order_product_order_product_mapping.all().values_list('product__id', flat=True)
        reserved_products = OrderedProductReserved.objects.filter(cart=cart, product__id__in=shipment_products, 
                                                                  reserve_status=OrderedProductReserved.ORDERED,
                                                                  reserved_qty__gt=0).order_by('reserved_qty')
        for ordered_product_reserved in reserved_products:
            grn = ordered_product_reserved.order_product_reserved
            grn.available_qty += (ordered_product_reserved.reserved_qty -
                                  ordered_product_reserved.shipped_qty)
            grn.save()
            ordered_product_reserved.save()

@task
def update_order_status_and_create_picker(shipment_id, close_order_checked, changed_data):
    UpdateOrderStatusAndCreatePicker(shipment_id, close_order_checked, changed_data)
