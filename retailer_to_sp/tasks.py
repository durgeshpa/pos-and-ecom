from celery.task import task
from sp_to_gram.models import OrderedProductReserved, OrderedProductMapping
from gram_to_brand.models import (
    OrderedProductReserved as GramOrderedProductReserved)


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
