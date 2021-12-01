import logging
from decimal import Decimal

from django.db import transaction

from accounts.models import User
from pos.common_functions import PosInventoryCls
from pos.models import PosCartProductMapping, RetailerProduct, PosCart, PosGRNOrderProductMapping, PosGRNOrder
from retailer_to_sp.models import Cart, Order

# Logger
from wms.models import PosInventoryState, PosInventoryChange

info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')
cron_logger = logging.getLogger('cron_log')


def run(*args):
    # Change all no of packs to no of pieces for old PO and GRN
    with transaction.atomic():
        print("started",)
        ordered_cart = Cart.objects.filter(cart_type='BULK', order_id__isnull=False,
                                           buyer_shop__shop_type__shop_type='f',
                                           buyer_shop__status=True, buyer_shop__approval_status=2,
                                           buyer_shop__pos_enabled=1).order_by('-id')
        for cart in ordered_cart:
            try:
                order = Order.objects.filter(ordered_cart=cart).last()
                if order:
                    cart_products = cart.rt_cart_list.all()
                    pos_cart_pro_map = PosCart.objects.filter(gf_order_no=order.order_no).last()
                    for product in cart_products:
                        retailer_product = RetailerProduct.objects.filter(
                            linked_product=product.cart_product, shop=cart.buyer_shop, is_deleted=False,
                            product_ref__isnull=True).last()
                        if pos_cart_pro_map and retailer_product:
                            print("mapping changed", pos_cart_pro_map)
                            mapping = PosCartProductMapping.objects.filter(cart=pos_cart_pro_map,
                                                                           product=retailer_product).last()
                            if mapping:
                                mapping.pack_size = 1
                                mapping.qty = product.no_of_pieces
                                mapping.save()
                                print("mapping changed", mapping.is_grn_done)
                            if mapping and mapping.is_grn_done:
                                print(" mapping.is_grn_done true", product.cart_product)
                                grn_order = PosGRNOrder.objects.filter(order=pos_cart_pro_map.pos_po_order).last()
                                po_grn_order_map = PosGRNOrderProductMapping.objects.filter(grn_order=grn_order).last()
                                qty_change = round(Decimal(product.no_of_pieces), 3) - po_grn_order_map.received_qty
                                po_grn_order_map.received_qty = product.no_of_pieces
                                po_grn_order_map.save()

                                if qty_change != 0:
                                    print("started", product.cart_product)
                                    PosInventoryCls.grn_inventory(product.cart_product, PosInventoryState.AVAILABLE,
                                                                  PosInventoryState.AVAILABLE, qty_change, User.objects.get(id=9),
                                                                  grn_order.grn_id, PosInventoryChange.GRN_UPDATE,
                                                                  mapping.pack_size)
                                    print("done", product.cart_product)

            except Exception as e:
                error_logger.error(e)
                info_logger.error("Something went wrong:", str(e))

        info_logger.info("Script Complete to Change no of packs to no of pieces for old PO and GRN")
