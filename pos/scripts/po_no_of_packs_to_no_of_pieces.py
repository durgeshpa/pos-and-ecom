import logging
from django.db import transaction

from pos.models import PosCartProductMapping, RetailerProduct, PosCart, PosGRNOrderProductMapping, PosGRNOrder
from retailer_to_sp.models import Cart, Order

# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run(*args):
    # Change all no of packs to no of pieces for old PO and GRN
    with transaction.atomic():
        ordered_cart = Cart.objects.filter(cart_type='BULK', order_id__isnull=False,
                                           buyer_shop__shop_type__shop_type='f',
                                           buyer_shop__status=True, buyer_shop__approval_status=2,
                                           buyer_shop__pos_enabled=1).order_by('-id')
        for cart_pro_map in ordered_cart:
            try:
                products = cart_pro_map.rt_cart_list.all()
                order = Order.objects.filter(ordered_cart=cart_pro_map).last()
                if order:
                    pos_cart_pro_map = PosCart.objects.filter(gf_order_no=order.order_no).last()
                    for product in products:
                        retailer_product = RetailerProduct.objects.filter(
                            linked_product=product.cart_product, shop=cart_pro_map.buyer_shop, is_deleted=False,
                            product_ref__isnull=True).last()
                        if pos_cart_pro_map and retailer_product:
                            mapping = PosCartProductMapping.objects.filter(cart=pos_cart_pro_map,
                                                                           product=retailer_product).last()
                            if mapping:
                                mapping.pack_size = 1
                                mapping.qty = product.no_of_pieces
                                mapping.save()
                            if mapping and mapping.is_grn_done:
                                grn_order = PosGRNOrder.objects.filter(order=pos_cart_pro_map.pos_po_order).last()
                                po_grn_order_map = PosGRNOrderProductMapping.objects.filter(grn_order=grn_order).last()
                                po_grn_order_map.received_qty = product.no_of_pieces
                                po_grn_order_map.save()

            except Exception as e:
                error_logger.error(e)
                info_logger.error("Something went wrong:", str(e))

        info_logger.info("Script Complete to Change no of packs to no of pieces for old PO and GRN")
