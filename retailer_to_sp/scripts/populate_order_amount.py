from django.db.models.signals import pre_save, post_save

from retailer_to_sp.models import Order


def run():
    recievers = post_save.receivers
    post_save.receivers = []
    start_time = '2020-08-29 01:01:06.067349'
    orders = Order.objects.filter(order_amount=0, created_at__gte=start_time)
    print("Total Order Count {}".format(orders.count()))
    for o in orders:
        total_final_amount = 0
        for cart_product_mapping in o.ordered_cart.rt_cart_list.all():

            if cart_product_mapping.cart.offers:
                array = list(filter(lambda d: d['coupon_type'] in 'catalog', o.ordered_cart.offers))
                for i in array:
                    if cart_product_mapping.cart_product.id == i['item_id']:
                        total_final_amount += (i.get('discounted_product_subtotal', 0))
            else:
                product_price = cart_product_mapping.cart_product_price
                if product_price:
                    total_final_amount += float(product_price.get_per_piece_price(cart_product_mapping.qty)) * cart_product_mapping.no_of_pieces
        if o.total_mrp is None or o.total_mrp == 0:
            total_mrp = o.total_mrp_amount
            if total_mrp:
                o.total_mrp = total_mrp
        if total_final_amount is not None:
            o.order_amount = total_final_amount
        o.save()
        print("Order ID {}, Order No {}, Total MRP {}, Final Amount {}".format( o.pk, o.order_no, o.total_mrp, o.order_amount ))

    post_save.receivers = recievers
    print('Done')