from django.db import transaction

from pos.models import PosCartProductMapping, RetailerProduct
from retailer_to_sp.models import Cart


def run(*args):
    # Change all no of packs to no of pieces for old PO and GRN
    with transaction.atomic():
        order_cart = Cart.objects.filter(cart_type=Cart.BULK, order_id__isnull=False)
        for cart_pro_map in order_cart:
            products = cart_pro_map.rt_cart_list.all()
            for product in products:
                retailer_product = RetailerProduct.objects.filter(
                    linked_product=product.cart_product, shop=order_cart.buyer_shop).last()
                mapping = PosCartProductMapping.objects.filter(cart=order_cart, product=retailer_product).last()
                if mapping:
                    mapping.pack_size = 1
                    mapping.qty = product.no_of_pieces
                    mapping.save()
