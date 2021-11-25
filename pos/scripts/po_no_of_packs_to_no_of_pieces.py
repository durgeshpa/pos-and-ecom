import logging
from django.db import transaction

from pos.models import PosCartProductMapping, RetailerProduct, PosCart
from retailer_to_sp.models import Cart, Order

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run(*args):
    # Change all no of packs to no of pieces for old PO and GRN
    with transaction.atomic():
        info_logger.info("Script Start to Change no of packs to no of pieces for old PO and GRN")
        order_cart = Cart.objects.filter(cart_type='BULK', order_id__isnull=False,
                                         buyer_shop__shop_type__shop_type='f',
                                         buyer_shop__status=True, buyer_shop__approval_status=2,
                                         buyer_shop__pos_enabled=1).order_by('-id')
        for cart_pro_map in order_cart:
            try:
                order = Order.objects.get(ordered_cart=cart_pro_map)
                products = cart_pro_map.rt_cart_list.all()
                pos_cart_pro_map = PosCart.objects.filter(gf_order_no=order.order_no)
                for product in products:
                    retailer_product = RetailerProduct.objects.filter(
                        linked_product=product.cart_product, shop=cart_pro_map.buyer_shop).last()
                    if pos_cart_pro_map:
                        mapping = PosCartProductMapping.objects.filter(cart=pos_cart_pro_map.last(),
                                                                       product=retailer_product).last()
                        if mapping:
                            mapping.pack_size = 1
                            mapping.qty = product.no_of_pieces
                            mapping.save()
                            
            except Exception as e:
                error_logger.error(e)
                info_logger.error("Something went wrong:", str(e))

        info_logger.info("Script Complete to Change no of packs to no of pieces for old PO and GRN")
