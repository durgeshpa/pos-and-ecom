import logging

from retailer_to_sp.models import Cart, Order

logger = logging.getLogger(__name__)
info_logger = logging.getLogger('file-info')


def run():
    print('deactivate_ordered_cart_for_ecom_and_pos | STARTED')
    pos_ecom_carts = Cart.objects.filter(cart_type__in=['ECOM', 'BASIC'], cart_status='active',
                                         rt_order_cart_mapping__isnull=False)
    print(pos_ecom_carts.count())
    pos_ecom_carts.update(cart_status='ordered')
    print("Task completed")
