from celery.task import task
from sp_to_gram.models import OrderedProductReserved


@task
def update_reserve_quatity(**kwargs):
    kwargs.get('model').objects.filter(
        product=kwargs.get('product'),
        reserved_qty=kwargs.get('reserved_qty')
    ).update(
        order_product_reserved=kwargs.get('order_product_reserved'),
        cart=kwargs.get('cart'),
        reserve_status='reserved')


@task
def release_blocking(parent_mapping, cart_id):
    parent_shop_type = parent_mapping.parent.shop_type.shop_type
    if parent_shop_type == 'sp':
        ordered_product_reserved = OrderedProductReserved.objects.filter(
            cart__id=cart_id, reserve_status='reserved')
        if ordered_product_reserved.exists():
            for ordered_reserve in ordered_product_reserved:
                ordered_reserve.order_product_reserved.available_qty = int(
                    ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
                ordered_reserve.order_product_reserved.save()
                ordered_reserve.delete()
    elif parent_mapping.parent.shop_type.shop_type == 'gf':
        if GramOrderedProductReserved.objects.filter(cart__id=cart_id,reserve_status='reserved').exists():
            for ordered_reserve in GramOrderedProductReserved.objects.filter(cart__id=cart_id,reserve_status='reserved'):
                ordered_reserve.order_product_reserved.available_qty = int(
                    ordered_reserve.order_product_reserved.available_qty) + int(ordered_reserve.reserved_qty)
                ordered_reserve.order_product_reserved.save()
                ordered_reserve.delete()
    return True