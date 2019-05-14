import datetime
import json
from celery.task import task
from sp_to_gram.models import OrderedProductReserved, OrderedProductMapping
from gram_to_brand.models import (
    OrderedProductReserved as GramOrderedProductReserved)
from retailer_to_sp.models import (Cart,)
from django.db.models import Sum, Q


@task
def create_reserved_order(shop_id, products, cart_id):
    products = json.loads(products)
    cart = Cart.objects.get(pk=cart_id)
    grns = OrderedProductMapping.objects.filter(
        Q(shop__id=shop_id),
        Q(product__id__in=products.keys()),
        Q(available_qty__gt=0),
        Q(expiry_date__gt=datetime.datetime.today())
        ).order_by('product_id','available_qty')

    for grn in grns:
        remaining_qty = products[grn.product.id]
        if remaining_qty:
            deduct_qty = min(grn.available_qty, remaining_qty)
            grn.available_qty -= deduct_qty
            remaining_qty -= deduct_qty
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
