from django.core.management.base import BaseCommand
from django.db import transaction

from retailer_to_sp.models import OrderedProduct, Trip, franchise_inventory_update


class Command(BaseCommand):
    """
        Add franchise order inventory to franchise shops
    """
    def handle(self, *args, **options):
        franchise_return_verified = OrderedProduct.objects.filter(order__buyer_shop__shop_type__shop_type='f',
                                                                  trip__trip_status=Trip.RETURN_VERIFIED,
                                                                  trip__completed_at__gt='2020-12-29')

        try:
            with transaction.atomic():
                for shipment in franchise_return_verified:
                    if (shipment.order.buyer_shop and shipment.order.buyer_shop.shop_type.shop_type == 'f' and
                            shipment.rt_order_product_order_product_mapping.last()):
                        warehouse = shipment.order.buyer_shop
                        franchise_inventory_update(shipment, warehouse)

        except Exception as e:
            print(e)




