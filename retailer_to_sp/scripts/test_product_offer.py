from decimal import Decimal

from retailer_to_sp.models import Order, CartProductMapping


def run():
    todays_orders = Order.objects.filter(created_at__gte='2022-06-17').values('order_amount', 'ordered_cart_id')
    order_total = {i['ordered_cart_id']:{'order': i['order_amount'], 'cart':0} for i in todays_orders}
    cart_products = CartProductMapping.objects.filter(cart_id__in=order_total.keys())
    print(cart_products.count())
    for p in cart_products:
        if p.cart_product_price:
            sub_total = Decimal(p.cart_product_price.get_per_piece_price(p.no_of_pieces))*p.no_of_pieces
            order_total[p.cart_id]['cart'] += sub_total

    for i in order_total.values():
        if i['order'] != i['cart']:
            print(i)